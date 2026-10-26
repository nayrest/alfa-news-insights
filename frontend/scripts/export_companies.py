"""Выгружает профили выбранных компаний из df_Uid_data_hack.csv в JSON для фронтенда.

Запуск из корня репозитория:
    python frontend/scripts/export_companies.py data/df_Uid_data_hack.csv frontend/src/mocks/companies.json
"""
import json
import sys

import pandas as pd

# Клиенты для демо: разные отрасли, с кредитами и без, с ВЭД и без.
# Условные названия задаются во фронтенде (src/config/companies.ts), здесь только данные из CSV.
SELECTED = ["U_34911", "U_9250", "U_200890", "U_102920", "U_4909"]

PRODUCTS = {
    "CL_PRODUCT_RKO_MARK": "РКО",
    "CL_PRODUCT_LOA_MARK": "Кредиты",
    "CL_PRODUCT_GAR_MARK": "Банковские гарантии",
    "CL_PRODUCT_LEA_MARK": "Лизинг",
    "CL_PRODUCT_DEP_MARK": "Депозиты",
    "CL_PRODUCT_ZPP_MARK": "Зарплатный проект",
    "FACTORING_MARK": "Факторинг",
}
CL_TYPES = {"CLIENT": "Действующий клиент", "CLOSE_CLIENT": "Закрывающийся клиент", "PROSPECT": "Потенциальный клиент"}


def none_if_nan(value):
    return None if pd.isna(value) else value


def country_label(raw):
    # «ОАЭ», «США» оставляем аббревиатурой, остальное — с заглавной буквы.
    raw = raw.strip()
    return raw if len(raw) <= 3 else raw.title()


def main(csv_path, out_path):
    df = pd.read_csv(csv_path, sep=";", low_memory=False)
    groups = df.groupby("GROUP_ID")
    result = []
    for uid in SELECTED:
        row = df[df.SYNTHETIC_U == uid].iloc[0]
        group = groups.get_group(row.GROUP_ID)
        countries = none_if_nan(row.FTS_COUNTRY_NAME)
        result.append({
            "id": uid,
            "okved_code": str(row.MAINOKVED_CODE),
            "okved_name": row.MAINOKVED_NAME,
            "revenue": float(row.REVENUE_COMPANY),
            "client_type": row.CL_TYPE,
            "client_type_label": CL_TYPES.get(row.CL_TYPE, row.CL_TYPE),
            "products": [label for col, label in PRODUCTS.items() if row[col] == 1],
            "has_loans": bool(row.CL_PRODUCT_LOA_MARK == 1),
            "fts_flag": bool(row.FTS_FLAG == 1),
            "fts_countries": [country_label(c) for c in countries.split(",")] if countries else [],
            "negative_mark": bool(row.NEGATIVEMARK == 1),
            "eco_stage": none_if_nan(row.ECO_MARK_LABEL),
            "age": row.COMPANY_AGE_YEARS_GRADATION,
            "workers": row.AMOUNT_WORKERS_FNS_GRADATION,
            "ownership": row.OKFS_NAME.capitalize(),
            "city": row.CITY,
            "region": row.REGION,
            "group": {
                "id": row.GROUP_ID,
                "size": int(group.SYNTHETIC_U.nunique()),
                "revenue": float(group.REVENUE_COMPANY.sum()),
                "top_okved": group.MAINOKVED_CODE.astype(str).value_counts().head(3).index.tolist(),
            },
        })
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Сохранено {len(result)} компаний в {out_path}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
