"""Список открытых источников новостей.

Новый источник = одна строка здесь (критерий 07 «масштабирование на новые источники»).
Если какой-то фид недоступен, парсер пропустит его и продолжит с остальными.
"""

RSS_SOURCES: list[dict] = [
    {"name": "Интерфакс", "url": "https://www.interfax.ru/rss.asp"},
    {"name": "РБК", "url": "https://rssexport.rbc.ru/rbcnews/news/30/full.rss"},
    {"name": "ТАСС", "url": "https://tass.ru/rss/v2.xml"},
    {"name": "Коммерсантъ", "url": "https://www.kommersant.ru/RSS/main.xml"},
    {"name": "Ведомости", "url": "https://www.vedomosti.ru/rss/news"},
    {"name": "Банк России", "url": "https://www.cbr.ru/rss/eventrss"},
]
