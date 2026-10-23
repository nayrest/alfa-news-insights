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


def _columns(path: Path) -> set[str]:
    try:
        with path.open(encoding="utf-8-sig", errors="ignore") as f:
            header = f.readline()
    except OSError:
        return set()
    sep = ";" if header.count(";") > header.count(",") else ","
    return {c.strip().strip('"').upper() for c in header.split(sep)}


def _resolve(configured: str, data_dir: str, required: set[str]) -> str | None:
    """Путь из настроек, если файл есть и подходит по колонкам; иначе ищем подходящий CSV в папке данных."""
    p = Path(configured)
    if p.is_file() and required <= _columns(p):
        return str(p)
    base = Path(data_dir)
    if base.is_dir():
        for candidate in sorted(base.glob("*.csv")):
            if not candidate.name.startswith("sample_") and required <= _columns(candidate):
                log.info("Файл %s не найден, использую %s (подходит по колонкам)", configured, candidate.name)
                return str(candidate)
    return None


def _clean(row: dict) -> dict:
    return {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in row.items()}


def load_companies(session: Session) -> dict:
    s = get_settings()
    companies_path = _resolve(s.companies_csv, s.data_dir, {"SYNTHETIC_U", "MAINOKVED_CODE"})
    using_sample = companies_path is None
    companies_path = companies_path or s.sample_companies_csv
    companies = read_csv(companies_path)
    if companies is None:
        return {"loaded": 0, "error": "Нет ни реальных, ни синтетических данных о компаниях"}

    if using_sample:
        payments_path = str(Path(s.sample_companies_csv).with_name("sample_payments.csv"))
        persons_path = None
    else:
        # Синтетику к реальным компаниям не подмешиваем: ищем настоящие файлы по колонкам,
        # имена в кейсе путаются (на слайде у физлиц и платежей одно имя).
        payments_path = _resolve(s.payments_csv, s.data_dir, {"PAYER", "BENEFICIARY"})
        persons_path = _resolve(s.persons_csv, s.data_dir, {"SYNTHETIC_F", "SYNTHETIC_U"})
    payments = read_csv(payments_path) if payments_path else None
    persons = read_csv(persons_path) if persons_path else None
    source = companies_path

    companies = normalize_columns(companies)
    profiles = build_profiles(companies, payments, persons, s.large_business_revenue)
    raw_rows = {str(r["SYNTHETIC_U"]): _clean(r) for r in companies.to_dict(orient="records")}

    existing_ids = set(session.scalars(select(Company.id)))
    rows = [
        {
            "id": cid,
            "okved_code": p["okved_code"],
            "okved_name": p["okved_name"],
            "region": p["region"],
            "revenue": p["revenue"],
            "group_id": p["group"]["group_id"],
            "raw": raw_rows.get(cid, {}),
            "profile": p,
        }
        for cid, p in profiles.items()
    ]
    # Пакетная вставка/обновление: 85 тыс. строк по одной через merge заняли бы минуты
    new_rows = [r for r in rows if r["id"] not in existing_ids]
    old_rows = [r for r in rows if r["id"] in existing_ids]
    for i in range(0, len(new_rows), 5000):
        session.bulk_insert_mappings(Company, new_rows[i : i + 5000])
    for i in range(0, len(old_rows), 5000):
        session.bulk_update_mappings(Company, old_rows[i : i + 5000])
    session.commit()
    log.info("Загружено компаний: %s из %s", len(profiles), source)
    return {
        "loaded": len(profiles),
        "source": source,
        "payments": payments_path,
        "persons": persons_path,
    }
