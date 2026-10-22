from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Company(Base):
    """Компания из df_Uid_data_hack.csv. raw — исходная строка, profile — посчитанный профиль."""

    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # SYNTHETIC_U
    okved_code: Mapped[str | None] = mapped_column(String(16))
    okved_name: Mapped[str | None] = mapped_column(Text)
    region: Mapped[str | None] = mapped_column(String(255))
    revenue: Mapped[float | None] = mapped_column(Float)
    group_id: Mapped[str | None] = mapped_column(String(64))
    raw: Mapped[dict] = mapped_column(JSON, default=dict)
    profile: Mapped[dict] = mapped_column(JSON, default=dict)


class News(Base):
    __tablename__ = "news"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dedup_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(255))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    # Классификация: темы, страны, отрасли (см. app/news/classify.py)
    tags: Mapped[dict] = mapped_column(JSON, default=dict)
    # Другие источники, написавшие о том же событии
    duplicates: Mapped[list] = mapped_column(JSON, default=list)


class Insight(Base):
    """Персональная интерпретация события для компании (результат агента)."""

    __tablename__ = "insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    news_id: Mapped[int] = mapped_column(ForeignKey("news.id"), index=True)
    role: Mapped[str] = mapped_column(String(32), default="ceo")
    payload: Mapped[dict] = mapped_column(JSON)  # JSON по схеме app/schemas.py::InsightPayload
    trace: Mapped[list] = mapped_column(JSON, default=list)  # шаги агента
    status: Mapped[str] = mapped_column(String(16), default="ok")  # ok | partial | error
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LLMCall(Base):
    """Журнал и кэш обращений к LLM: экономия лимита + аудит (требование безопасности)."""

    __tablename__ = "llm_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cache_key: Mapped[str] = mapped_column(String(64), index=True)
    model: Mapped[str] = mapped_column(String(64))
    purpose: Mapped[str] = mapped_column(String(64))
    request: Mapped[list] = mapped_column(JSON)
    response: Mapped[str] = mapped_column(Text)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ToolCall(Base):
    """Журнал вызовов инструментов агентом (требование безопасности из кейса)."""

    __tablename__ = "tool_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    insight_run: Mapped[str] = mapped_column(String(64), index=True)
    tool: Mapped[str] = mapped_column(String(64))
    args: Mapped[dict] = mapped_column(JSON)
    result_preview: Mapped[str] = mapped_column(Text, default="")
    allowed: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
