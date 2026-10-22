"""Уточняющие вопросы по готовому инсайту (критерий 10)."""

import json

from sqlalchemy.orm import Session

from app.agent import prompts
from app.companies.profile import profile_summary
from app.config import get_settings
from app.llm.client import chat_json
from app.models import Company, Insight, News


def answer(session: Session, ins: Insight, company: Company, news: News, question: str) -> dict:
    payload = {k: v for k, v in ins.payload.items() if k not in ("sources", "features")}
    analytics = {k: v for k, v in ins.payload.get("sources", {}).items() if k.startswith("A")}
    result = chat_json(
        session,
        [
            {"role": "system", "content": prompts.SYSTEM},
            {
                "role": "user",
                "content": prompts.ASK.format(
                    insight=json.dumps(payload, ensure_ascii=False),
                    news=f"{news.title}. {news.summary[:1000]} ({news.url})",
                    analytics="\n".join(f"[{k}] «{v['doc']}»: {v['text']}" for k, v in analytics.items()) or "(нет)",
                    profile=profile_summary(company.profile),
                    question=question,
                ),
            },
        ],
        model=get_settings().llm_model_smart,
        purpose="ask",
        max_tokens=800,
    )
    return {"question": question, **result, "sources": ins.payload.get("sources", {})}
