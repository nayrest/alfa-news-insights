"""Персональный отбор и ранжирование новостей под компанию (без LLM).

score = сумма весов совпавших интересов компании × затухание по свежести.
Каждое совпадение сохраняет причину — это и есть объяснение «почему важно».
"""

from datetime import datetime, timezone


def match_news(news_tags: dict, news_text: str, interests: list[dict]) -> list[dict]:
    keys = {f"topic:{t}" for t in news_tags.get("topics", [])}
    keys |= {f"sector:{s}" for s in news_tags.get("sectors", [])}
    keys |= {f"country:{c}" for c in news_tags.get("countries", [])}
    text_lower = news_text.lower()

    matched: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for it in interests:
        key = it["key"]
        if key.startswith("region:"):
            region = key.split(":", 1)[1].lower()
            # «Свердловская область» -> ищем основу «свердловск»
            stem = region.split()[0][:-2] if len(region.split()[0]) > 5 else region
            hit = bool(stem) and stem in text_lower
        else:
            hit = key in keys
        if hit and (key, it["reason"]) not in seen:
            seen.add((key, it["reason"]))
            matched.append(it)
    return matched


def recency_factor(published_at: datetime | None, now: datetime | None = None, half_life_h: float = 48) -> float:
    if published_at is None:
        return 0.7
    now = now or datetime.now(timezone.utc)
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    age_h = max((now - published_at).total_seconds() / 3600, 0)
    return 0.5 ** (age_h / half_life_h)


def score_news(news_tags: dict, news_text: str, published_at: datetime | None, interests: list[dict]) -> dict:
    matched = match_news(news_tags, news_text, interests)
    # Один и тот же ключ (например key_rate из кредитов и из депозитов) считаем по максимальному весу
    best: dict[str, float] = {}
    for m in matched:
        best[m["key"]] = max(best.get(m["key"], 0), m["weight"])
    base = sum(best.values())
    # Бонус за пересечение нескольких факторов (критерий 02: интерпретация «с учётом нескольких факторов»)
    multi = 1 + 0.15 * max(len(best) - 1, 0)
    score = base * multi * recency_factor(published_at)
    return {
        "score": round(score, 3),
        "matched": matched,
        "is_relevant": base >= 2.5 and not (len(best) == 1 and next(iter(best)) in ("topic:inflation", "topic:gdp_macro")),
    }


def rank(news_list: list, interests: list[dict], limit: int = 20) -> list[tuple]:
    """news_list — объекты с .tags, .title, .summary, .published_at. Возвращает [(news, score_info)]."""
    scored = []
    for n in news_list:
        info = score_news(n.tags or {}, f"{n.title}. {n.summary}", n.published_at, interests)
        if info["is_relevant"]:
            scored.append((n, info))
    scored.sort(key=lambda x: x[1]["score"], reverse=True)
    return scored[:limit]
