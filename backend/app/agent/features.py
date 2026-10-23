"""Признаки клиента в виде ключей, на которые агент обязан ссылаться (трассируемость, критерий 12)."""

from app.companies.profile import country_ru

PRODUCT_RU = {
    "rko": "расчётно-кассовое обслуживание",
    "loans": "кредитные продукты",
    "leasing": "лизинг",
    "deposits": "депозиты",
    "guarantees": "банковские гарантии",
    "salary_project": "зарплатный проект",
    "factoring": "факторинг",
}


def feature_keys(p: dict) -> dict[str, str]:
    """{ключ: описание}. Пример: {'has_loans': 'Есть кредитные продукты', 'fts_country:КИТАЙ': ...}."""
    f: dict[str, str] = {}
    for prod, on in p["products"].items():
        if on:
            f[f"has_{prod}"] = f"Есть {PRODUCT_RU.get(prod, prod)}"
        else:
            f[f"no_{prod}"] = f"Нет {PRODUCT_RU.get(prod, prod)} в банке"
    f[f"sector:{p['sector']}"] = f"Отрасль: {p['sector_ru']} (ОКВЭД {p['okved_code']})"
    if p.get("region"):
        f[f"region:{p['region']}"] = f"Регион регистрации: {p['region']}"
    if p.get("revenue"):
        f["revenue"] = f"Выручка {p['revenue']:,.0f} ₽".replace(",", " ")
    if p["market"].get("share_in_okved_dataset") is not None:
        f["market_share"] = (
            f"Доля среди компаний с тем же ОКВЭД в данных: {p['market']['share_in_okved_dataset']:.1%}"
        )
    ft = p["foreign_trade"]
    if ft["has_fts"]:
        f["fts"] = "Ведёт внешнеэкономическую деятельность"
        for c in (ft.get("countries") or [])[:6]:
            f[f"fts_country:{c}"] = f"Страна ВЭД: {country_ru(c)}"
    for side, ru in (("suppliers", "поставщик"), ("buyers", "покупатель")):
        for cp in p["counterparties"][side][:3]:
            f[f"{side[:-1]}:{cp['id']}"] = f"Ключевой {ru} {cp['id']}: {cp['share']:.0%} платежей, отрасль {cp['sector']}"
    if p["group"]["group_size"] > 1:
        f["group"] = f"Группа компаний из {p['group']['group_size']} юрлиц"
    if p.get("workers"):
        f["workers"] = f"Численность работников: {p['workers']}"
    return f


def bank_products_missing(p: dict) -> list[str]:
    return [PRODUCT_RU[k] for k, on in p["products"].items() if not on and k in PRODUCT_RU]
