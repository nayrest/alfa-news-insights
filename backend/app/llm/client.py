"""Клиент LLM (OpenAI-совместимый API) с кэшем, журналом и защитой дневного лимита.

Кэш: одинаковый запрос к той же модели второй раз не тратит токены.
Журнал: каждый вызов пишется в llm_calls — для аудита и подсчёта расхода.
"""

import hashlib
import json
import logging
import re
import time
from datetime import datetime, timezone

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import LLMCall

log = logging.getLogger(__name__)


class LLMError(RuntimeError):
    pass


class LLMBudgetExceeded(LLMError):
    pass


def _cache_key(model: str, messages: list[dict]) -> str:
    raw = json.dumps({"m": model, "msg": messages}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def tokens_used_today(session: Session) -> int:
    # Бюджет шлюза обновляется в 03:00 МСК = 00:00 UTC — считаем сутки так же
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    total = session.scalar(
        select(func.coalesce(func.sum(LLMCall.prompt_tokens + LLMCall.completion_tokens), 0)).where(
            LLMCall.created_at >= start
        )
    )
    return int(total or 0)


def chat(
    session: Session,
    messages: list[dict],
    *,
    model: str | None = None,
    purpose: str = "generic",
    temperature: float = 0.2,
    max_tokens: int = 1500,
    use_cache: bool = True,
) -> str:
    s = get_settings()
    model = model or s.llm_model_fast
    key = _cache_key(model, messages)

    if use_cache:
        cached = session.scalar(
            select(LLMCall)
            .where(LLMCall.cache_key == key, LLMCall.response != "")
            .order_by(LLMCall.id.desc())
            .limit(1)
        )
        if cached:
            return cached.response

    if not s.llm_base_url or not s.llm_api_key:
        raise LLMError("LLM не настроен: заполните LLM_BASE_URL и LLM_API_KEY в .env")
    if tokens_used_today(session) >= s.llm_daily_token_limit:
        raise LLMBudgetExceeded("Дневной лимит токенов исчерпан (LLM_DAILY_TOKEN_LIMIT)")

    body = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
    data = _post_with_fallback(s, body)

    message = (data.get("choices") or [{}])[0].get("message") or {}
    content = message.get("content") or ""
    usage = data.get("usage") or {}
    session.add(
        LLMCall(
            cache_key=key,
            model=model,
            purpose=purpose,
            request=messages,
            response=content,
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
        )
    )
    session.commit()
    if not content.strip():
        # Частый случай у «думающих» моделей: весь max_tokens ушёл на рассуждения, ответа нет
        hint = " (модель потратила лимит на рассуждения — увеличьте max_tokens или возьмите другую модель)" if message.get(
            "reasoning"
        ) or message.get("reasoning_content") else ""
        raise LLMError(f"Пустой ответ от {model}{hint}")
    return content


def _post_with_fallback(s, body: dict) -> dict:
    """Пробует основной адрес шлюза, при сетевых ошибках/5xx/429 — запасной.

    Ошибки 4xx (неверный ключ, неизвестная модель) не повторяем: повтор не поможет.
    """
    urls = [u for u in (s.llm_base_url, s.llm_base_url_fallback) if u]
    last_exc: Exception | None = None
    for attempt in range(4):
        url = urls[attempt % len(urls)].rstrip("/") + "/chat/completions"
        try:
            resp = httpx.post(
                url,
                headers={"Authorization": f"Bearer {s.llm_api_key}"},
                json=body,
                timeout=s.llm_timeout_sec,
            )
        except httpx.HTTPError as exc:
            last_exc = exc
            log.warning("LLM %s недоступен (попытка %s): %s", url, attempt + 1, exc)
            continue
        if resp.status_code == 429 or resp.status_code >= 500:
            last_exc = LLMError(f"HTTP {resp.status_code} от {url}: {resp.text[:300]}")
            log.warning("%s", last_exc)
            time.sleep(1.5 * (attempt + 1))
            continue
        if resp.status_code >= 400:
            raise LLMError(f"HTTP {resp.status_code} от {url}: {resp.text[:500]}")
        try:
            return resp.json()
        except ValueError as exc:
            last_exc = exc
    raise LLMError(f"LLM недоступен: {last_exc}")


_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


def parse_json(text: str) -> dict:
    """Достаёт JSON из ответа модели (модели любят оборачивать его в ```json ... ```)."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = _JSON_BLOCK.search(text)
        if m:
            return json.loads(m.group(0))
        raise


def chat_json(session: Session, messages: list[dict], **kwargs) -> dict:
    """chat() + разбор JSON. При битом JSON один раз просит модель исправить ответ."""
    raw = chat(session, messages, **kwargs)
    try:
        return parse_json(raw)
    except (json.JSONDecodeError, ValueError):
        fix = messages + [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": "Ответ не является корректным JSON. Верни только исправленный JSON без пояснений."},
        ]
        return parse_json(chat(session, fix, **{**kwargs, "purpose": kwargs.get("purpose", "") + ":fix_json"}))
