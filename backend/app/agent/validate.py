"""Детерминированная самопроверка инсайта: структура и связь каждого вывода с источниками.

Работает без LLM. Ошибки отсюда идут агенту как замечания на доработку.
"""

from pydantic import ValidationError

from app.schemas import InsightPayload


def check_payload(data: dict, source_ids: set[str], analytics_ids: set[str], feature_ids: set[str]) -> tuple[InsightPayload | None, list[str]]:
    issues: list[str] = []
    try:
        payload = InsightPayload.model_validate(data)
    except ValidationError as exc:
        return None, [f"Нарушена JSON-схема: {e['loc']} — {e['msg']}" for e in exc.errors()[:8]]

    if not payload.facts:
        issues.append("Нет ни одного факта из новости (facts пуст)")
    fact_ids = {f.id for f in payload.facts}
    bank_ids = {b.id for b in payload.bank_view}

    for f in payload.facts:
        if f.source not in source_ids:
            issues.append(f"Факт {f.id} ссылается на неизвестный источник '{f.source}'. Допустимо: {sorted(source_ids)}")
    for b in payload.bank_view:
        if b.source not in analytics_ids:
            issues.append(
                f"Позиция банка {b.id} ссылается на '{b.source}', которого нет в найденной аналитике {sorted(analytics_ids)}"
            )

    known_refs = fact_ids | bank_ids | feature_ids
    for inf in payload.ai_inference:
        if not inf.based_on:
            issues.append(f"Вывод {inf.id} ни на что не опирается (based_on пуст)")
        bad = [r for r in inf.based_on if r not in known_refs]
        if bad:
            issues.append(f"Вывод {inf.id} ссылается на несуществующее: {bad}")

    used_bad = [f for f in payload.client_features_used if f not in feature_ids]
    if used_bad:
        issues.append(f"client_features_used содержит неизвестные признаки: {used_bad}")
    if not payload.client_features_used:
        issues.append("Не указано, какие признаки клиента повлияли на вывод (client_features_used пуст)")
    if not (payload.risks or payload.opportunities):
        issues.append("Нет ни рисков, ни возможностей")
    if analytics_ids and not payload.bank_view:
        issues.append("Найдена аналитика Альфа-Банка, но она не использована в bank_view")

    return payload, issues
