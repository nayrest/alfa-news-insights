"""Загрузка данных кейса в БД. Если реальных CSV нет — берутся синтетические примеры из data/."""

import logging
import math
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.companies.profile import build_profiles, normalize_columns
from app.config import get_settings
from app.models import Company

log = logging.getLogger(__name__)


def read_csv(path: str) -> pd.DataFrame | None:
    p = Path(path)
    if not p.is_file():
        return None
    # sep=None — pandas сам определит разделитель (, или ;)
    for enc in ("utf-8", "utf-8-sig", "cp1251"):
        try:
            return pd.read_csv(p, sep=None, engine="python", encoding=enc, dtype=str)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Не удалось прочитать {path}: неизвестная кодировка")


def _clean(row: dict) -> dict:
    return {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in row.items()}


def load_companies(session: Session) -> dict:
    s = get_settings()
    companies = read_csv(s.companies_csv)
    source = s.companies_csv
    if companies is None:
        companies = read_csv(s.sample_companies_csv)
        source = s.sample_companies_csv
    if companies is None:
        return {"loaded": 0, "error": "Нет ни реальных, ни синтетических данных о компаниях"}

    payments = read_csv(s.payments_csv)
    if payments is None:
        payments = read_csv(str(Path(s.sample_companies_csv).with_name("sample_payments.csv")))
    persons = read_csv(s.persons_csv)

    # Защита от путаницы имён файлов в кейсе: файл платежей узнаём по колонкам
    if persons is not None and {"PAYER", "BENEFICIARY"} <= set(c.upper() for c in persons.columns):
        payments, persons = persons, None

    companies = normalize_columns(companies)
    profiles = build_profiles(companies, payments, persons, s.large_business_revenue)
    raw_rows = {str(r["SYNTHETIC_U"]): _clean(r) for r in companies.to_dict(orient="records")}

    existing_ids = set(session.scalars(select(Company.id)))
    for cid, p in profiles.items():
        # add — быстро для первой загрузки, merge — для обновления уже загруженных
        (session.merge if cid in existing_ids else session.add)(
            Company(
                id=cid,
                okved_code=p["okved_code"],
                okved_name=p["okved_name"],
                region=p["region"],
                revenue=p["revenue"],
                group_id=p["group"]["group_id"],
                raw=raw_rows.get(cid, {}),
                profile=p,
            )
        )
    session.commit()
    log.info("Загружено компаний: %s из %s", len(profiles), source)
    return {
        "loaded": len(profiles),
        "source": source,
        "with_payments": payments is not None,
        "with_persons": persons is not None,
    }
