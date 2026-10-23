"""Профиль компании из данных кейса — без LLM, детерминированно и трассируемо.

Главный результат — список interests: какие темы/отрасли/страны важны компании,
с весом и человеческой причиной. По ним ранжируются новости, и эти же причины
показываются пользователю в блоке «Почему это важно для вас».
"""

import math
import re

import pandas as pd

# 2 первые цифры ОКВЭД -> отрасль (ключи совпадают с app/news/classify.py::SECTORS)
_OKVED_RANGES: list[tuple[int, int, str]] = [
    (1, 3, "agriculture"),
    (5, 5, "mining_metals"),
    (6, 6, "oil_gas"),
    (7, 8, "mining_metals"),
    (9, 9, "oil_gas"),
    (10, 12, "food"),
    (13, 18, "manufacturing"),
    (19, 19, "oil_gas"),
    (20, 22, "chemicals"),
    (23, 23, "manufacturing"),
    (24, 25, "mining_metals"),
    (26, 28, "manufacturing"),
    (29, 29, "auto"),
    (30, 33, "manufacturing"),
    (35, 39, "energy"),
    (41, 43, "construction"),
    (45, 45, "auto"),
    (46, 47, "retail_trade"),
    (49, 53, "transport_logistics"),
    (55, 56, "retail_trade"),
    (58, 63, "it_telecom"),
    (64, 66, "finance"),
    (68, 68, "real_estate"),
]

SECTOR_NAMES_RU = {
    "agriculture": "сельское хозяйство",
    "oil_gas": "нефть и газ",
    "mining_metals": "добыча и металлургия",
    "food": "пищевая промышленность",
    "chemicals": "химия",
    "manufacturing": "обрабатывающая промышленность",
    "auto": "автомобильная отрасль",
    "energy": "энергетика",
    "construction": "строительство",
    "retail_trade": "торговля",
    "transport_logistics": "транспорт и логистика",
    "it_telecom": "ИТ и связь",
    "finance": "финансы",
    "real_estate": "недвижимость",
    "other": "прочее",
}

_COMMODITY_SECTORS = {"agriculture", "oil_gas", "mining_metals", "chemicals"}
_CONSUMER_SECTORS = {"retail_trade", "food", "auto"}

_TRUE = {"1", "1.0", "y", "yes", "true", "да", "д", "есть", "+"}


_PRODUCT_RU = {
    "rko": "расчётный счёт",
    "loans": "кредиты",
    "leasing": "лизинг",
    "deposits": "депозиты",
    "guarantees": "банковские гарантии",
    "salary_project": "зарплатный проект",
    "factoring": "факторинг",
}

# Оптовая торговля сырьём по ОКВЭД -> отрасль, от цен которой зависит бизнес
_WHOLESALE_RAW = {
    "46.2": ("agriculture", "Оптовая торговля сельхозсырьём: важны урожай, цены на зерно и экспортные правила"),
    "46.3": ("food", "Оптовая торговля продуктами: важны цены на продовольствие"),
    "46.71": ("oil_gas", "Оптовая торговля топливом: важны цены на нефть и нефтепродукты"),
    "46.72": ("mining_metals", "Оптовая торговля металлами и рудами: важны цены на металлы"),
    "46.75": ("chemicals", "Оптовая торговля химией: важны цены на химическое сырьё"),
}


def flag(value) -> bool:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return False
    return str(value).strip().lower() in _TRUE


def to_float(value) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    try:
        return float(re.sub(r"[\s ]", "", str(value)).replace(",", "."))
    except ValueError:
        return None


def text(value) -> str | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    s = str(value).strip()
    return s or None


def split_countries(value) -> list[str]:
    """'КИТАЙ,ИНДИЯ' -> ['КИТАЙ', 'ИНДИЯ'] (в данных кейса страны ВЭД перечислены через запятую)."""
    s = text(value)
    if not s:
        return []
    seen: list[str] = []
    for part in re.split(r"[,;]", s):
        c = part.strip().upper()
        if c and c not in seen:
            seen.append(c)
    return seen


def country_ru(c: str) -> str:
    """'ЮЖНАЯ КОРЕЯ' -> 'Южная Корея', аббревиатуры (ОАЭ, США) не трогаем."""
    return c if len(c) <= 3 else c.title()


def okved_to_sector(code: str | None) -> str:
    if not code:
        return "other"
    m = re.match(r"\s*(\d{1,2})", str(code))
    if not m:
        return "other"
    two = int(m.group(1))
    for lo, hi, sector in _OKVED_RANGES:
        if lo <= two <= hi:
            return sector
    return "other"


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    return df


def counterparty_index(payments: pd.DataFrame | None, sectors: dict[str, str], top: int = 5) -> dict[str, dict]:
    """Для каждой компании: ключевые поставщики (кому платит) и покупатели (кто платит) с долями.

    Считается один раз по всей таблице платежей (она может быть большой).
    """
    index: dict[str, dict] = {}
    if payments is None or payments.empty:
        return index

    pay = payments[["PAYER", "BENEFICIARY", "PAY_AMT"]].copy()
    pay["PAYER"] = pay["PAYER"].astype(str)
    pay["BENEFICIARY"] = pay["BENEFICIARY"].astype(str)
    pay = pay[pay["PAYER"] != pay["BENEFICIARY"]]  # переводы самой себе — не контрагенты
    pairs = pay.groupby(["PAYER", "BENEFICIARY"], as_index=False)["PAY_AMT"].sum()

    for side, own_col, other_col in (("suppliers", "PAYER", "BENEFICIARY"), ("buyers", "BENEFICIARY", "PAYER")):
        totals = pairs.groupby(own_col)["PAY_AMT"].sum()
        top_rows = pairs.sort_values("PAY_AMT", ascending=False).groupby(own_col).head(top)
        for own_id, grp in top_rows.groupby(own_col):
            total = float(totals.get(own_id, 0)) or 1.0
            index.setdefault(own_id, {"suppliers": [], "buyers": []})[side] = [
                {
                    "id": str(r[other_col]),
                    "share": round(float(r["PAY_AMT"]) / total, 3),
                    "sector": sectors.get(str(r[other_col]), "unknown"),
                }
                for _, r in grp.iterrows()
            ]
    return index


def build_interests(p: dict) -> list[dict]:
    """Что важно этой компании: [{key, weight, reason}]. Ключи вида 'topic:fx', 'sector:food', 'country:КИТАЙ'."""
    out: list[dict] = []

    def add(key: str, weight: float, reason: str) -> None:
        out.append({"key": key, "weight": weight, "reason": reason})

    prod = p["products"]
    if prod["loans"] or prod["leasing"]:
        what = " и ".join(x for x, ok in (("кредиты", prod["loans"]), ("лизинг", prod["leasing"])) if ok)
        add("topic:key_rate", 3, f"У компании есть {what}: ставка влияет на стоимость долга")
        add("topic:debt_market", 2, f"У компании есть {what}: важны условия долгового рынка")
    if prod["deposits"]:
        add("topic:key_rate", 2, "У компании есть депозиты: ставка влияет на доходность размещения")
    if prod["factoring"] or prod["guarantees"]:
        add("topic:debt_market", 1, "Факторинг/гарантии: важны условия финансирования оборотного капитала")

    if p["foreign_trade"]["has_fts"]:
        countries = p["foreign_trade"].get("countries") or []
        suffix = f" ({', '.join(country_ru(c) for c in countries[:3])})" if countries else ""
        add("topic:fx", 3, f"Компания ведёт ВЭД{suffix}: курс валют влияет на расчёты")
        add("topic:trade_policy", 2, f"Компания ведёт ВЭД{suffix}: важны пошлины и правила импорта/экспорта")
        add("topic:sanctions", 2, "Компания ведёт ВЭД: санкционные изменения могут затронуть расчёты и поставки")
        add("topic:logistics", 1, "Компания ведёт ВЭД: важна логистика")
        for c in countries[:6]:
            add(f"country:{c}", 4, f"Страна ВЭД компании — {country_ru(c)}")

    sector = p["sector"]
    if sector != "other":
        add(f"sector:{sector}", 3, f"Основная отрасль компании — {SECTOR_NAMES_RU.get(sector, sector)}")
        if sector in _COMMODITY_SECTORS:
            add("topic:commodities", 3, "Выручка компании зависит от цен на сырьё")
        if sector in _CONSUMER_SECTORS:
            add("topic:consumer_demand", 2, "Бизнес компании зависит от потребительского спроса")
    okved = str(p.get("okved_code") or "")
    for prefix, (raw_sector, reason) in _WHOLESALE_RAW.items():
        if okved.startswith(prefix):
            add(f"sector:{raw_sector}", 3, reason)
            add("topic:commodities", 2, reason)
            break

    if prod["salary_project"] or p.get("workers"):
        add("topic:labor", 1.5, "Расходы на персонал: важны зарплаты и рынок труда")

    for cp_type, ru in (("suppliers", "поставщик"), ("buyers", "покупатель")):
        for cp in p["counterparties"][cp_type][:3]:
            if cp["sector"] not in ("unknown", "other") and cp["share"] >= 0.1:
                add(
                    f"sector:{cp['sector']}",
                    2,
                    f"Крупный {ru} ({int(cp['share'] * 100)}% платежей) — из отрасли "
                    f"«{SECTOR_NAMES_RU.get(cp['sector'], cp['sector'])}»",
                )

    if p.get("region"):
        add(f"region:{p['region']}", 2, f"Компания зарегистрирована в регионе: {p['region']}")

    add("topic:inflation", 1, "Инфляция влияет на издержки и спрос любой компании")
    add("topic:gdp_macro", 0.5, "Общая макроэкономическая ситуация")
    return out


def build_profiles(
    companies: pd.DataFrame,
    payments: pd.DataFrame | None = None,
    persons: pd.DataFrame | None = None,
    large_revenue: float = 15_000_000_000,
) -> dict[str, dict]:
    companies = normalize_columns(companies)
    payments = normalize_columns(payments) if payments is not None else None
    persons = normalize_columns(persons) if persons is not None else None

    if payments is not None and not payments.empty:
        payments = payments.copy()
        payments["PAY_AMT"] = payments["PAY_AMT"].map(to_float).fillna(0.0)

    companies = companies.copy()
    companies["_ID"] = companies["SYNTHETIC_U"].astype(str)
    companies["_REV"] = companies.get("REVENUE_COMPANY", pd.Series(dtype=object)).map(to_float)
    companies["_OKVED"] = companies.get("MAINOKVED_CODE", pd.Series(dtype=object)).map(text)
    companies["_SECTOR"] = companies["_OKVED"].map(okved_to_sector)
    sectors = dict(zip(companies["_ID"], companies["_SECTOR"]))

    # Оценка доли рынка: выручка компании / сумма выручки компаний с тем же ОКВЭД в наборе данных.
    okved_totals = companies.groupby("_OKVED")["_REV"].sum(min_count=1).to_dict()
    okved_counts = companies.groupby("_OKVED")["_ID"].count().to_dict()
    companies["_RANK"] = companies.groupby("_OKVED")["_REV"].rank(ascending=False, method="min")

    group_sizes = companies.groupby("GROUP_ID")["_ID"].count().to_dict() if "GROUP_ID" in companies else {}
    cp_index = counterparty_index(payments, sectors)

    linked: dict[str, set[str]] = {}
    if persons is not None and not persons.empty:
        by_person = persons.groupby(persons["SYNTHETIC_F"].astype(str))["SYNTHETIC_U"].apply(
            lambda s: set(s.astype(str))
        )
        for comps in by_person:
            for c in comps:
                linked.setdefault(c, set()).update(comps - {c})

    profiles: dict[str, dict] = {}
    for _, row in companies.iterrows():
        cid = row["_ID"]
        rev = None if pd.isna(row["_REV"]) else float(row["_REV"])
        okved = row["_OKVED"]
        total = okved_totals.get(okved)
        total = None if total is None or pd.isna(total) else float(total)
        group_id = text(row.get("GROUP_ID"))
        p = {
            "id": cid,
            "okved_code": okved,
            "okved_name": text(row.get("MAINOKVED_NAME")),
            "sector": row["_SECTOR"],
            "sector_ru": SECTOR_NAMES_RU.get(row["_SECTOR"], row["_SECTOR"]),
            "region": text(row.get("REGION")),
            "city": text(row.get("CITY")),
            "revenue": rev,
            "is_large": bool(rev and rev >= large_revenue),
            "market": {
                "share_in_okved_dataset": round(rev / total, 4) if rev and total else None,
                "rank_in_okved_dataset": int(row["_RANK"]) if not pd.isna(row["_RANK"]) else None,
                "companies_in_okved_dataset": int(okved_counts.get(okved, 0)),
                "note": "Оценка по компаниям из набора данных кейса, а не по всему рынку",
            },
            "products": {
                "rko": flag(row.get("CL_PRODUCT_RKO_MARK")),
                "loans": flag(row.get("CL_PRODUCT_LOA_MARK")),
                "leasing": flag(row.get("CL_PRODUCT_LEA_MARK")),
                "deposits": flag(row.get("CL_PRODUCT_DEP_MARK")),
                "guarantees": flag(row.get("CL_PRODUCT_GAR_MARK")),
                "salary_project": flag(row.get("CL_PRODUCT_ZPP_MARK")),
                "factoring": flag(row.get("FACTORING_MARK")),
            },
            "foreign_trade": {
                "has_fts": flag(row.get("FTS_FLAG")),
                "country": text(row.get("FTS_COUNTRY_NAME")),  # как в данных, для совместимости
                "countries": split_countries(row.get("FTS_COUNTRY_NAME")),
            },
            "group": {
                "group_id": group_id,
                "group_size": int(group_sizes.get(row.get("GROUP_ID"), 1)) if group_id else 1,
            },
            "linked_companies_via_persons": sorted(linked.get(cid, set()))[:20],
            "workers": text(row.get("AMOUNT_WORKERS_FNS_GRADATION")) or text(row.get("AMOUNT_WORKERS_SPARK_GRADATION")),
            "client_type": text(row.get("CL_TYPE")),
            "company_age": text(row.get("COMPANY_AGE_YEARS_GRADATION")),
            "eco_stage": text(row.get("ECO_MARK_LABEL")),
            "negative_mark": flag(row.get("NEGATIVEMARK")),
            "ownership": text(row.get("OKFS_NAME")),
            "org_type": text(row.get("ORG_TYPE")),
            "counterparties": cp_index.get(cid, {"suppliers": [], "buyers": []}),
        }
        p["interests"] = build_interests(p)
        profiles[cid] = p
    return profiles


def profile_summary(p: dict) -> str:
    """Короткое текстовое описание профиля для промпта LLM (экономит токены)."""
    prod = [_PRODUCT_RU.get(k, k) for k, v in p["products"].items() if v]
    lines = [
        f"Компания {p['id']}: отрасль — {p['sector_ru']} (ОКВЭД {p['okved_code']} {p['okved_name'] or ''}).",
        f"Регион: {p['region'] or 'н/д'}. Выручка: {p['revenue'] or 'н/д'} ₽, крупный бизнес: {'да' if p['is_large'] else 'нет'}.",
        f"Продукты в банке: {', '.join(prod) or 'нет данных'}.",
        "ВЭД: "
        + (
            "да, страны " + (", ".join(country_ru(c) for c in p["foreign_trade"].get("countries") or []) or "н/д")
            if p["foreign_trade"]["has_fts"]
            else "нет"
        )
        + ".",
    ]
    share = p["market"]["share_in_okved_dataset"]
    if share is not None:
        lines.append(
            f"Доля среди компаний с тем же ОКВЭД в данных: {share:.1%} "
            f"(место {p['market']['rank_in_okved_dataset']} из {p['market']['companies_in_okved_dataset']})."
        )
    for cp_type, ru in (("suppliers", "Поставщики"), ("buyers", "Покупатели")):
        cps = p["counterparties"][cp_type]
        if cps:
            lines.append(ru + ": " + "; ".join(f"{c['id']} ({c['share']:.0%}, {c['sector']})" for c in cps[:3]))
    if p["group"]["group_size"] > 1:
        lines.append(f"Входит в группу компаний из {p['group']['group_size']} юрлиц.")
    return "\n".join(lines)
