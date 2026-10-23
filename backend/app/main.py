import logging
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.agent.ask import answer
from app.agent.runner import safe_run_agent
from app.analytics import get_index, reload_index
from app.companies.loader import load_companies
from app.config import get_settings
from app.db import SessionLocal, get_session, init_db
from app.llm.client import LLMError, tokens_used_today
from app.models import Company, Insight, News
from app.news.ingest import run_ingest
from app.ranking import rank, score_news
from app.schemas import ROLES, AskRequest, InsightRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("pypdf").setLevel(logging.ERROR)  # шумит предупреждениями о битых ссылках в PDF
log = logging.getLogger("app")


def _init_db_with_retry(attempts: int = 15, delay: float = 2.0) -> None:
    """База и сеть Docker при первом старте могут быть не готовы — ждём, а не падаем."""
    for i in range(1, attempts + 1):
        try:
            init_db()
            return
        except OperationalError as exc:
            if i == attempts:
                raise
            log.warning("База недоступна (попытка %s/%s): %s", i, attempts, str(exc).splitlines()[0])
            time.sleep(delay)


def _ingest_loop(interval_min: int) -> None:
    while True:
        try:
            with SessionLocal() as session:
                log.info("Сбор новостей: %s", run_ingest(session))
        except Exception:  # noqa: BLE001
            log.exception("Ошибка фонового сбора новостей")
        time.sleep(interval_min * 60)


@asynccontextmanager
async def lifespan(_: FastAPI):
    _init_db_with_retry()
    with SessionLocal() as session:
        if not session.scalar(select(func.count()).select_from(Company)):
            log.info("Загрузка компаний: %s", load_companies(session))
    get_index()
    interval = get_settings().news_ingest_interval_min
    if interval > 0:
        threading.Thread(target=_ingest_loop, args=(interval,), daemon=True).start()
    yield


app = FastAPI(
    title="Alfa News Insights",
    description="Персонализированная новостная аналитика для руководителей крупного бизнеса (прототип для хакатона).",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ---------- служебное ----------


@app.get("/health")
def health(session: Session = Depends(get_session)):
    s = get_settings()
    return {
        "status": "ok",
        "companies": session.scalar(select(func.count()).select_from(Company)),
        "news": session.scalar(select(func.count()).select_from(News)),
        "insights": session.scalar(select(func.count()).select_from(Insight)),
        "alfa_analytics_docs": get_index().documents,
        "alfa_analytics_chunks": len(get_index().chunks),
        "llm_configured": bool(s.llm_base_url and s.llm_api_key),
        "llm_tokens_today": tokens_used_today(session),
        "llm_daily_token_limit": s.llm_daily_token_limit,
    }


@app.post("/admin/load-companies")
def admin_load_companies(session: Session = Depends(get_session)):
    return load_companies(session)


@app.post("/admin/reload-analytics")
def admin_reload_analytics():
    idx = reload_index()
    return {"documents": idx.documents, "chunks": len(idx.chunks), "files": idx.files}


@app.get("/admin/analytics-status")
def admin_analytics_status():
    """Сколько текста извлечено из каждого файла аналитики — чтобы видеть проблемные PDF."""
    idx = get_index()
    return {"chunks": len(idx.chunks), "files": idx.files}


@app.get("/admin/analytics-search")
def admin_analytics_search(q: str, k: int = Query(3, le=10)):
    """Проверка RAG вручную: что найдётся в аналитике банка по запросу."""
    return get_index().search(q, k=k)


ALLOWED_MODELS = [
    "google/gemma-4-26b-a4b-it",
    "z-ai/glm-5.3-flash",
    "qwen/qwen3.6-35b-a3b",
    "deepseek/deepseek-v4.1-flash",
    "qwen/qwen3-vl-30b-a3b-instruct",
    "moonshotai/kimi-k2.6",
]


@app.post("/admin/llm-ping")
def admin_llm_ping(model: str | None = None, session: Session = Depends(get_session)):
    """Проверка доступа к LLM: короткий запрос к одной модели (или ко всем, если model не указан).

    Показывает задержку, расход токенов и то, отвечает ли модель JSON без «рассуждений» на весь лимит.
    Тратит немного бюджета — не вызывайте в цикле.
    """
    from app.llm.client import LLMError, chat

    results = []
    for m in [model] if model else ALLOWED_MODELS:
        t0 = time.monotonic()
        try:
            out = chat(
                session,
                [{"role": "user", "content": 'Верни JSON {"ok": true, "lang": "ru"} и ничего больше.'}],
                model=m,
                purpose="ping",
                max_tokens=400,
                use_cache=False,
            )
            results.append({"model": m, "ok": True, "seconds": round(time.monotonic() - t0, 1), "answer": out[:200]})
        except LLMError as exc:
            results.append({"model": m, "ok": False, "seconds": round(time.monotonic() - t0, 1), "error": str(exc)[:400]})
    return {"results": results, "tokens_today": tokens_used_today(session)}


@app.get("/admin/llm-usage")
def admin_llm_usage(session: Session = Depends(get_session)):
    """Расход токенов за сутки (с 03:00 МСК) по моделям и целям — следим за лимитом 500 ₽."""
    from datetime import datetime as _dt

    from app.models import LLMCall

    start = _dt.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    rows = session.execute(
        select(
            LLMCall.model,
            LLMCall.purpose,
            func.count(),
            func.sum(LLMCall.prompt_tokens),
            func.sum(LLMCall.completion_tokens),
        )
        .where(LLMCall.created_at >= start)
        .group_by(LLMCall.model, LLMCall.purpose)
    ).all()
    return [
        {"model": m, "purpose": p, "calls": c, "prompt_tokens": int(pt or 0), "completion_tokens": int(ct or 0)}
        for m, p, c, pt, ct in rows
    ]


@app.get("/roles")
def roles():
    return ROLES


# ---------- новости ----------


@app.post("/news/ingest")
def news_ingest(session: Session = Depends(get_session)):
    return run_ingest(session)


@app.post("/admin/reclassify-news")
def admin_reclassify_news(session: Session = Depends(get_session)):
    """Пересчитать темы/отрасли/страны у уже сохранённых новостей (после изменения правил классификации)."""
    from app.news.classify import classify

    rows = list(session.scalars(select(News)))
    for n in rows:
        n.tags = classify(n.title, n.summary)
    session.commit()
    return {"reclassified": len(rows)}


@app.get("/news")
def news_list(limit: int = Query(50, le=500), session: Session = Depends(get_session)):
    rows = session.scalars(select(News).order_by(News.published_at.desc().nullslast()).limit(limit))
    return [_news_out(n) for n in rows]


def _news_out(n: News) -> dict:
    return {
        "id": n.id,
        "title": n.title,
        "summary": n.summary,
        "url": n.url,
        "source": n.source,
        "published_at": n.published_at,
        "tags": n.tags,
        "also_reported_by": n.duplicates,
    }


# ---------- компании ----------


@app.get("/companies")
def companies_list(
    large_only: bool = True,
    limit: int = Query(50, le=1000),
    session: Session = Depends(get_session),
):
    q = select(Company)
    if large_only:
        q = q.where(Company.revenue >= get_settings().large_business_revenue)
    rows = session.scalars(q.order_by(Company.revenue.desc().nullslast()).limit(limit))
    return [
        {
            "id": c.id,
            "sector": c.profile.get("sector_ru"),
            "okved": f"{c.okved_code} {c.okved_name or ''}".strip(),
            "region": c.region,
            "revenue": c.revenue,
        }
        for c in rows
    ]


def _company_or_404(session: Session, company_id: str) -> Company:
    company = session.get(Company, company_id)
    if not company:
        raise HTTPException(404, f"Компания {company_id} не найдена")
    return company


@app.get("/companies/{company_id}")
def company_profile(company_id: str, session: Session = Depends(get_session)):
    return _company_or_404(session, company_id).profile


@app.get("/companies/{company_id}/feed")
def company_feed(
    company_id: str,
    days: int = Query(7, le=30),
    limit: int = Query(20, le=100),
    role: str = "ceo",
    session: Session = Depends(get_session),
):
    """Лента: свежие новости, отобранные и отсортированные под компанию, с причинами отбора."""
    company = _company_or_404(session, company_id)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    candidates = list(session.scalars(select(News).where(News.fetched_at >= since)))
    ranked = rank(candidates, company.profile["interests"], limit=limit)

    news_ids = [n.id for n, _ in ranked]
    existing = {}
    if news_ids:
        for ins in session.scalars(
            select(Insight).where(
                Insight.company_id == company_id, Insight.news_id.in_(news_ids), Insight.role == role
            ).order_by(Insight.id)
        ):
            existing[ins.news_id] = ins  # последний перезапишет предыдущие

    return [
        {
            **_news_out(n),
            "score": info["score"],
            "why_selected": [m["reason"] for m in info["matched"]],
            "insight_id": existing[n.id].id if n.id in existing else None,
            "insight_headline": existing[n.id].payload.get("headline") if n.id in existing else None,
        }
        for n, info in ranked
    ]


# ---------- инсайты (агент) ----------


@app.post("/companies/{company_id}/insights")
def create_insight(company_id: str, req: InsightRequest, session: Session = Depends(get_session)):
    company = _company_or_404(session, company_id)
    news = session.get(News, req.news_id)
    if not news:
        raise HTTPException(404, f"Новость {req.news_id} не найдена")
    if req.role not in ROLES:
        raise HTTPException(422, f"Неизвестная роль. Доступны: {list(ROLES)}")

    if not req.force:
        cached = session.scalar(
            select(Insight)
            .where(
                Insight.company_id == company_id,
                Insight.news_id == news.id,
                Insight.role == req.role,
                Insight.status != "error",
            )
            .order_by(Insight.id.desc())
            .limit(1)
        )
        if cached:
            return _insight_out(cached)
    return _insight_out(safe_run_agent(session, company, news, req.role))


def _insight_out(ins: Insight) -> dict:
    return {
        "id": ins.id,
        "company_id": ins.company_id,
        "news_id": ins.news_id,
        "role": ins.role,
        "status": ins.status,
        "created_at": ins.created_at,
        "insight": ins.payload,
    }


@app.get("/insights/{insight_id}")
def get_insight(insight_id: int, session: Session = Depends(get_session)):
    ins = session.get(Insight, insight_id)
    if not ins:
        raise HTTPException(404, "Инсайт не найден")
    return _insight_out(ins)


@app.get("/insights/{insight_id}/trace")
def get_trace(insight_id: int, session: Session = Depends(get_session)):
    """«Как получен вывод»: шаги агента, вызванные инструменты, найденные источники."""
    ins = session.get(Insight, insight_id)
    if not ins:
        raise HTTPException(404, "Инсайт не найден")
    return {"insight_id": ins.id, "status": ins.status, "trace": ins.trace}


@app.post("/insights/{insight_id}/ask")
def ask_insight(insight_id: int, req: AskRequest, session: Session = Depends(get_session)):
    """Уточняющий вопрос по инсайту (критерий 10)."""
    ins = session.get(Insight, insight_id)
    if not ins or ins.status == "error":
        raise HTTPException(404, "Инсайт не найден или не построен")
    company = session.get(Company, ins.company_id)
    news = session.get(News, ins.news_id)
    try:
        return answer(session, ins, company, news, req.question)
    except LLMError as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get("/companies/{company_id}/explain/{news_id}")
def explain_selection(company_id: str, news_id: int, session: Session = Depends(get_session)):
    """Почему новость попала (или не попала) в ленту компании — без LLM."""
    company = _company_or_404(session, company_id)
    news = session.get(News, news_id)
    if not news:
        raise HTTPException(404, "Новость не найдена")
    return score_news(news.tags or {}, f"{news.title}. {news.summary}", news.published_at, company.profile["interests"])
