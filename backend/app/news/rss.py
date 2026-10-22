"""Загрузка и разбор RSS/Atom. Разбор — только стандартная библиотека, чтобы его было легко тестировать."""

import hashlib
import html
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


@dataclass
class RawNews:
    title: str
    summary: str
    url: str
    source: str
    published_at: datetime | None
    tags: dict = field(default_factory=dict)

    @property
    def dedup_key(self) -> str:
        return hashlib.sha256(normalize_title(self.title).encode()).hexdigest()


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_NON_WORD_RE = re.compile(r"[^\w\s]", re.UNICODE)


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    text = html.unescape(_TAG_RE.sub(" ", text))
    return _WS_RE.sub(" ", text).strip()


def normalize_title(title: str) -> str:
    title = _NON_WORD_RE.sub(" ", title.lower().replace("ё", "е"))
    return _WS_RE.sub(" ", title).strip()


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    try:
        dt = parsedate_to_datetime(value)  # RFC 822 (RSS)
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))  # ISO 8601 (Atom)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _local(tag: str) -> str:
    """'{namespace}item' -> 'item'."""
    return tag.rsplit("}", 1)[-1]


def _child_text(el: ET.Element, *names: str) -> str | None:
    for child in el:
        if _local(child.tag) in names and (child.text or "").strip():
            return child.text
    return None


def parse_feed(xml_text: str, source: str, max_summary_chars: int = 1500) -> list[RawNews]:
    """Разбирает RSS 2.0 или Atom. Битые элементы пропускаются, а не роняют весь фид."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    items = [el for el in root.iter() if _local(el.tag) in ("item", "entry")]
    result: list[RawNews] = []
    for item in items:
        title = clean_text(_child_text(item, "title"))
        if not title:
            continue

        url = _child_text(item, "link") or ""
        if not url:  # Atom: <link href="..."/>
            for child in item:
                if _local(child.tag) == "link" and child.get("href"):
                    url = child.get("href", "")
                    break

        summary = clean_text(
            _child_text(item, "full-text", "encoded", "description", "summary", "content")
        )[:max_summary_chars]
        published = _parse_date(_child_text(item, "pubDate", "published", "updated", "date"))
        result.append(RawNews(title=title, summary=summary, url=url.strip(), source=source, published_at=published))
    return result


def fetch_feed(url: str, source: str, timeout: float = 15.0) -> list[RawNews]:
    import httpx  # импорт здесь, чтобы parse_feed можно было тестировать без httpx

    resp = httpx.get(
        url,
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 (alfa-news-insights hackathon prototype)"},
    )
    resp.raise_for_status()
    return parse_feed(resp.text, source)


_SYNONYMS = {"банк россии": "цб", "центробанк": "цб", "центральный банк": "цб", "минфин россии": "минфин"}
_SHORT_STOP = {"в", "на", "и", "с", "по", "за", "к", "от", "до", "о", "об", "из", "не", "для"}


def _title_terms(title: str) -> set[str]:
    t = normalize_title(title)
    for k, v in _SYNONYMS.items():
        t = t.replace(k, v)
    return {w[:5] for w in t.split() if w not in _SHORT_STOP}


def jaccard(a: str, b: str) -> float:
    sa, sb = _title_terms(a), _title_terms(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def group_duplicates(items: list[RawNews], threshold: float = 0.6) -> list[tuple[RawNews, list[RawNews]]]:
    """Склеивает одно событие из разных источников: (главная новость, [дубли]).

    Простая эвристика по пересечению слов заголовка — для прототипа достаточно,
    позже можно заменить на эмбеддинги.
    """
    groups: list[tuple[RawNews, list[RawNews]]] = []
    for item in items:
        for main, dups in groups:
            if item.dedup_key == main.dedup_key or jaccard(item.title, main.title) >= threshold:
                dups.append(item)
                break
        else:
            groups.append((item, []))
    return groups
