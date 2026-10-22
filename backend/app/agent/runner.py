"""Агент интерпретации: план -> инструменты -> черновик -> самопроверка -> (повтор) -> результат.

Каждый шаг пишется в trace, чтобы в интерфейсе можно было показать «Как получен вывод» (критерий 12).
"""

import json
import time
import uuid

from sqlalchemy.orm import Session

from app.agent import prompts
from app.agent.features import bank_products_missing, feature_keys
from app.agent.tools import ToolContext, call_tool, tools_description
from app.agent.validate import check_payload
from app.companies.profile import profile_summary
from app.config import get_settings
from app.llm.client import LLMError, chat_json
from app.models import Company, Insight, News
from app.ranking import score_news
from app.schemas import ROLES

MAX_REVISIONS = 2


class Trace:
    def __init__(self):
        self.steps: list[dict] = []
        self._t0 = time.monotonic()

    def add(self, step: str, **data) -> None:
        self.steps.append({"step": step, "t": round(time.monotonic() - self._t0, 2), **data})


def _fmt_analytics(chunks: list[dict]) -> str:
    if not chunks:
        return "(релевантная аналитика не найдена)"
    return "\n\n".join(f'[{c["id"]}] «{c["doc"]}»: {c["text"]}' for c in chunks)


def _fmt_related(items: list[dict]) -> str:
    if not items:
        return "(нет)"
    return "\n".join(f'[N{i + 2}] {n["title"]} ({n["source"]}) — {n["summary"][:300]}' for i, n in enumerate(items))


def run_agent(session: Session, company: Company, news: News, role: str = "ceo") -> Insight:
    s = get_settings()
    run_id = uuid.uuid4().hex[:16]
    trace = Trace()
    ctx = ToolContext(session, run_id, company)
    profile = company.profile
    summary_text = profile_summary(profile)
    features = feature_keys(profile)
    role_desc = ROLES.get(role, ROLES["ceo"])

    # Шаг 0. Отбор правилами — дешёвый, объясняет, какие признаки совпали
    rule = score_news(news.tags or {}, f"{news.title}. {news.summary}", news.published_at, profile["interests"])
    trace.add("rule_match", score=rule["score"], matched=[m["reason"] for m in rule["matched"]])

    news_fields = {
        "title": news.title,
        "summary": news.summary[:1500],
        "source": news.source,
        "published": news.published_at.isoformat() if news.published_at else "дата неизвестна",
        "url": news.url,
    }

    # Шаг 1. Планирование
    plan = chat_json(
        session,
        [
            {"role": "system", "content": prompts.SYSTEM},
            {
                "role": "user",
                "content": prompts.PLAN.format(
                    **news_fields,
                    profile=summary_text,
                    reasons="; ".join(m["reason"] for m in rule["matched"]) or "нет",
                    tools=tools_description(),
                ),
            },
        ],
        model=s.llm_model_fast,
        purpose="plan",
        max_tokens=600,
    )
    if not isinstance(plan, dict):
        plan = {}
    trace.add("plan", output=plan)

    # Шаг 2. Инструменты по плану
    queries = [q for q in plan.get("analytics_queries", []) if isinstance(q, str) and q.strip()][:3] or [news.title]
    analytics: dict[str, dict] = {}
    for q in queries:
        for chunk in call_tool(ctx, "search_alfa_analytics", query=q, k=2):
            analytics.setdefault(chunk["id"], chunk)
    trace.add("tool:search_alfa_analytics", queries=queries, found=[f'{c["id"]} «{c["doc"]}»' for c in analytics.values()])

    related: list[dict] = []
    if plan.get("need_related_news") and plan.get("related_news_query"):
        related = [r for r in call_tool(ctx, "search_related_news", query=plan["related_news_query"]) if r["news_id"] != news.id]
        trace.add("tool:search_related_news", query=plan["related_news_query"], found=[r["title"] for r in related])

    if any(f.startswith(("supplier:", "buyer:")) for f in features):
        cps = call_tool(ctx, "get_counterparties")
        trace.add("tool:get_counterparties", output=cps)

    # Шаги 3–4. Черновик + самопроверка, до MAX_REVISIONS доработок
    source_ids = {"N1", *[f"N{i + 2}" for i in range(len(related))]}
    feedback = ""
    payload = None
    issues: list[str] = []
    for revision in range(MAX_REVISIONS + 1):
        draft = chat_json(
            session,
            [
                {"role": "system", "content": prompts.SYSTEM},
                {
                    "role": "user",
                    "content": prompts.DRAFT.format(
                        **news_fields,
                        related=_fmt_related(related),
                        analytics=_fmt_analytics(list(analytics.values())),
                        profile=summary_text,
                        features=json.dumps(features, ensure_ascii=False, indent=0),
                        role=role_desc,
                        missing_products=", ".join(bank_products_missing(profile)) or "нет",
                        plan=json.dumps(plan.get("steps", []), ensure_ascii=False),
                        feedback=feedback,
                    ),
                },
            ],
            model=s.llm_model_smart,
            purpose=f"draft:{revision}",
            max_tokens=1800,
        )
        payload, issues = check_payload(draft, source_ids, set(analytics), set(features))
        trace.add("self_check:rules", revision=revision, issues=issues)

        if payload is not None and not issues:
            critic = chat_json(
                session,
                [
                    {"role": "system", "content": prompts.SYSTEM},
                    {
                        "role": "user",
                        "content": prompts.CRITIC.format(
                            title=news.title,
                            summary=news.summary[:1000],
                            analytics=_fmt_analytics(list(analytics.values())),
                            profile=summary_text,
                            insight=payload.model_dump_json(),
                        ),
                    },
                ],
                model=s.llm_model_fast,
                purpose=f"critic:{revision}",
                max_tokens=500,
            )
            if not isinstance(critic, dict):
                critic = {"ok": True}
            trace.add("self_check:critic", revision=revision, output=critic)
            if critic.get("ok", True):
                break
            issues = [str(i) for i in critic.get("issues", [])][:5]
            # Адаптация: если критику не хватило данных — дозапрашиваем аналитику
            for q in [q for q in critic.get("extra_analytics_queries", []) if isinstance(q, str)][:2]:
                for chunk in call_tool(ctx, "search_alfa_analytics", query=q, k=2):
                    analytics.setdefault(chunk["id"], chunk)
            trace.add("adapt", extra_analytics=list(analytics))

        if revision < MAX_REVISIONS:
            feedback = "Замечания к прошлой версии, исправь их:\n- " + "\n- ".join(issues)

    status = "ok" if payload is not None and not issues else ("partial" if payload is not None else "error")
    insight = Insight(
        company_id=company.id,
        news_id=news.id,
        role=role,
        payload={
            **(payload.model_dump() if payload else {}),
            "sources": {
                "N1": {"title": news.title, "url": news.url, "source": news.source},
                **{f"N{i + 2}": {"title": r["title"], "url": r["url"], "source": r["source"]} for i, r in enumerate(related)},
                **{cid: {"doc": c["doc"], "text": c["text"]} for cid, c in analytics.items()},
            },
            "features": features,
            "unresolved_issues": issues,
        },
        trace=trace.steps,
        status=status,
    )
    session.add(insight)
    session.commit()
    return insight


def safe_run_agent(session: Session, company: Company, news: News, role: str = "ceo") -> Insight:
    """Как run_agent, но ошибки LLM не роняют API: сохраняем инсайт со статусом error и причиной."""
    try:
        return run_agent(session, company, news, role)
    except LLMError as exc:
        session.rollback()
        insight = Insight(
            company_id=company.id,
            news_id=news.id,
            role=role,
            payload={"error": str(exc)},
            trace=[{"step": "error", "message": str(exc)}],
            status="error",
        )
        session.add(insight)
        session.commit()
        return insight
