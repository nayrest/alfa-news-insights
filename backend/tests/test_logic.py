"""Тесты логики без БД и без LLM: python -m pytest tests -q"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from app.analytics import AnalyticsIndex, Chunk, split_chunks
from app.companies.profile import build_profiles, okved_to_sector
from app.news.classify import classify
from app.news.rss import group_duplicates, parse_feed
from app.ranking import score_news

_HERE = Path(__file__).resolve()
# локально: <repo>/data; в контейнере: /app/data
DATA = next(p for p in (_HERE.parents[2] / "data", _HERE.parents[1] / "data") if (p / "sample_companies.csv").exists())

RSS = """<?xml version="1.0"?><rss><channel>
<item><title>Банк России сохранил ключевую ставку 14%</title><link>https://ex.ru/1</link>
<description><![CDATA[<p>Совет директоров &laquo;сохранил&raquo; ставку</p>]]></description>
<pubDate>Fri, 11 Sep 2026 13:30:00 +0300</pubDate></item>
<item><title>ЦБ сохранил ключевую ставку 14%</title><link>https://ex2.ru/1</link></item>
<item><title></title><link>https://ex.ru/empty</link></item>
</channel></rss>"""

ATOM = """<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Юань подорожал</title>
<link href="https://ex.ru/a"/><updated>2026-10-20T10:00:00Z</updated><summary>Курс юаня вырос</summary></entry></feed>"""


def _profiles():
    companies = pd.read_csv(DATA / "sample_companies.csv", dtype=str)
    payments = pd.read_csv(DATA / "sample_payments.csv", dtype=str)
    return build_profiles(companies, payments)


def test_parse_rss_and_atom():
    items = parse_feed(RSS, "test")
    assert len(items) == 2  # пустой заголовок пропущен
    assert items[0].summary == "Совет директоров «сохранил» ставку"
    assert items[0].published_at.tzinfo is not None
    atom = parse_feed(ATOM, "atom")
    assert atom[0].url == "https://ex.ru/a" and atom[0].summary == "Курс юаня вырос"
    assert parse_feed("<not xml", "x") == []


def test_dedup_groups_same_event():
    groups = group_duplicates(parse_feed(RSS, "test"))
    assert len(groups) == 1 and len(groups[0][1]) == 1


def test_classify():
    t = classify("Банк России сохранил ключевую ставку", "")
    assert "key_rate" in t["topics"]
    t = classify("Китай ввёл пошлины на импорт стали", "")
    assert "КИТАЙ" in t["countries"] and "trade_policy" in t["topics"] and "mining_metals" in t["sectors"]
    assert classify("Вышла новая газета", "")["sectors"] == []  # «газ» не путается с «газетой»


def test_okved_sector():
    assert okved_to_sector("46.69") == "retail_trade"
    assert okved_to_sector("24.10") == "mining_metals"
    assert okved_to_sector(None) == "other"


def test_profile_has_counterparties_and_market_share():
    p = _profiles()["DEMO_U_001"]
    assert p["is_large"] and p["products"]["loans"] and p["foreign_trade"]["country"] == "КИТАЙ"
    assert p["counterparties"]["suppliers"][0]["id"] == "DEMO_U_004"
    assert 0 < p["market"]["share_in_okved_dataset"] <= 1
    keys = {i["key"] for i in p["interests"]}
    assert {"topic:key_rate", "topic:fx", "country:КИТАЙ", "sector:transport_logistics"} <= keys


def test_ranking_is_personal():
    profiles = _profiles()
    now = datetime.now(timezone.utc)
    title = "Курс юаня превысил 12 рублей"
    tags = classify(title)
    importer = score_news(tags, title, now, profiles["DEMO_U_001"]["interests"])  # ВЭД с Китаем
    it_company = score_news(tags, title, now, profiles["DEMO_U_005"]["interests"])  # без ВЭД
    assert importer["is_relevant"] and importer["score"] > it_company["score"]
    old = score_news(tags, title, now - timedelta(days=10), profiles["DEMO_U_001"]["interests"])
    assert old["score"] < importer["score"]


def test_analytics_search():
    idx = AnalyticsIndex(
        [
            Chunk("A1", "Ключевая ставка ЦБ РФ", "Банк России сохранил ставку 14%, риторика стала жёстче"),
            Chunk("A2", "Обзор рынка золота", "Цены на золото обновили максимум"),
        ]
    )
    assert idx.search("ключевая ставка")[0]["id"] == "A1"
    assert idx.search("золото")[0]["id"] == "A2"
    assert len(split_chunks("абзац один\n\n" + "длинный текст. " * 200, max_chars=300)) > 3


def test_split_countries_and_interests():
    from app.companies.profile import split_countries

    assert split_countries("ОАЭ,Алжир, индия") == ["ОАЭ", "АЛЖИР", "ИНДИЯ"]
    assert split_countries(None) == []
    companies = pd.read_csv(DATA / "sample_companies.csv", dtype=str)
    companies.loc[companies.SYNTHETIC_U == "DEMO_U_001", "FTS_COUNTRY_NAME"] = "КИТАЙ,ИНДИЯ"
    p = build_profiles(companies)["DEMO_U_001"]
    keys = {i["key"] for i in p["interests"]}
    assert {"country:КИТАЙ", "country:ИНДИЯ"} <= keys
    title = "Индия снизила пошлины на импорт"
    assert score_news(classify(title), title, None, p["interests"])["is_relevant"]
