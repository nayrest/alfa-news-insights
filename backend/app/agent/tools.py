"""Инструменты агента. Только чтение, белый список, каждый вызов журналируется.

Это и есть «ограничения на потенциально небезопасные действия» из кейса:
агент не может ничего изменить или вызвать что-то вне этого списка.
"""

import json
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.analytics import get_index
from app.models import Company, News, ToolCall


class ToolContext:
    def __init__(self, session: Session, run_id: str, company: Company):
        self.session = session
        self.run_id = run_id
        self.company = company  # агент видит данные только «своей» компании


def _get_profile(ctx: ToolContext) -> dict:
    return ctx.company.profile


def _get_counterparties(ctx: ToolContext) -> dict:
    return ctx.company.profile.get("counterparties", {})


def _search_alfa_analytics(ctx: ToolContext, query: str, k: int = 3) -> list[dict]:
    return get_index().search(query, k=min(int(k), 5))


def _search_related_news(ctx: ToolContext, query: str, days: int = 14, k: int = 3) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=min(int(days), 30))
    words = [w for w in query.split() if len(w) > 3][:5]
    if not words:
        return []
    cond = or_(*[News.title.ilike(f"%{w[:7]}%") for w in words])
    rows = ctx.session.scalars(
        select(News).where(News.fetched_at >= since, cond).order_by(News.published_at.desc().nullslast()).limit(int(k))
    )
    return [{"news_id": n.id, "title": n.title, "summary": n.summary[:400], "url": n.url, "source": n.source} for n in rows]


TOOLS: dict[str, tuple[Callable, str]] = {
    "get_profile": (_get_profile, "Профиль клиента: отрасль, продукты, ВЭД, регион, доля рынка"),
    "get_counterparties": (_get_counterparties, "Ключевые поставщики и покупатели по платежам"),
    "search_alfa_analytics": (_search_alfa_analytics, "Поиск по аналитике Альфа-Банка. Аргумент: query"),
    "search_related_news": (_search_related_news, "Поиск связанных новостей за последние дни. Аргумент: query"),
}


def call_tool(ctx: ToolContext, name: str, **args):
    allowed = name in TOOLS
    result = TOOLS[name][0](ctx, **args) if allowed else {"error": f"Инструмент '{name}' не разрешён"}
    ctx.session.add(
        ToolCall(
            insight_run=ctx.run_id,
            tool=name,
            args=args,
            result_preview=json.dumps(result, ensure_ascii=False, default=str)[:1000],
            allowed=allowed,
        )
    )
    return result


def tools_description() -> str:
    return "\n".join(f"- {name}: {desc}" for name, (_, desc) in TOOLS.items())
