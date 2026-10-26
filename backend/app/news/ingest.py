"""Сбор новостей: RSS -> склейка дублей -> классификация -> БД."""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import News
from app.news.classify import classify
from app.news.rss import RawNews, fetch_feed, group_duplicates, jaccard
from app.news.sources import RSS_SOURCES

log = logging.getLogger(__name__)


def collect(sources: list[dict] | None = None) -> tuple[list[RawNews], list[dict]]:
    """Скачивает все фиды. Ошибка одного источника не останавливает остальные."""
    items: list[RawNews] = []
    errors: list[dict] = []
    for src in sources or RSS_SOURCES:
        try:
            items.extend(fetch_feed(src["url"], src["name"]))
        except Exception as exc:  # noqa: BLE001 — источник может быть недоступен, это нормально
            log.warning("RSS %s недоступен: %s", src["name"], exc)
            errors.append({"source": src["name"], "error": str(exc)[:200]})
    return items, errors


def save(session: Session, items: list[RawNews]) -> dict:
    """Сохраняет новые события; дубли (в т.ч. с уже сохранёнными за 3 дня) приклеивает к существующим."""
    since = datetime.now(timezone.utc) - timedelta(days=3)
    recent = list(session.scalars(select(News).where(News.fetched_at >= since)))
    by_key = {n.dedup_key: n for n in recent}

    groups = group_duplicates(items)
    # Точный дубль ищем по всей таблице: ленты вроде ЦБ отдают старые записи,
    # которые уже сохранены раньше окна в 3 дня (иначе — UniqueViolation и пустая лента)
    keys = {main.dedup_key for main, _ in groups} - by_key.keys()
    if keys:
        for n in session.scalars(select(News).where(News.dedup_key.in_(keys))):
            by_key[n.dedup_key] = n

    added = merged = 0
    for main, dups in groups:
        existing = by_key.get(main.dedup_key) or next(
            (n for n in recent if jaccard(n.title, main.title) >= 0.6), None
        )
        dup_refs = [{"source": d.source, "url": d.url, "title": d.title} for d in [main, *dups]]
        if existing:
            known = {d.get("url") for d in existing.duplicates} | {existing.url}
            new_refs = [r for r in dup_refs if r["url"] not in known]
            if new_refs:
                existing.duplicates = [*existing.duplicates, *new_refs]
                merged += 1
            continue

        news = News(
            dedup_key=main.dedup_key,
            title=main.title,
            summary=main.summary,
            url=main.url,
            source=main.source,
            published_at=main.published_at,
            tags=classify(main.title, main.summary),
            duplicates=[r for r in dup_refs[1:]],
        )
        session.add(news)
        recent.append(news)
        by_key[news.dedup_key] = news
        added += 1

    session.commit()
    return {"added": added, "merged_into_existing": merged}


def run_ingest(session: Session) -> dict:
    items, errors = collect()
    stats = save(session, items)
    return {"fetched": len(items), **stats, "source_errors": errors}
