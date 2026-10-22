"""JSON-схема инсайта — общий формат обмена между агентом, API и интерфейсом.

Разделяет: подтверждённые факты (facts), позицию Альфа-Банка (bank_view) и выводы модели (ai_inference)
— это требование критерия 03 и раздела «Пространство решений».
"""

from pydantic import BaseModel, Field


class Fact(BaseModel):
    id: str = Field(description="F1, F2, ...")
    text: str
    source: str = Field(description="Идентификатор источника: N1 (новость), N2.. (связанные новости)")
    confirmed: bool = True


class BankView(BaseModel):
    id: str = Field(description="B1, B2, ...")
    text: str
    source: str = Field(description="Идентификатор фрагмента аналитики Альфа-Банка: A1, A2, ...")


class Inference(BaseModel):
    id: str = Field(description="I1, I2, ...")
    text: str
    based_on: list[str] = Field(description="Ссылки на F*, B* и признаки клиента")


class Item(BaseModel):
    text: str
    based_on: list[str] = Field(default_factory=list)


class InsightPayload(BaseModel):
    headline: str = Field(description="Одна фраза: что это значит для компании")
    what_happened: str
    why_important: str
    facts: list[Fact]
    bank_view: list[BankView] = Field(default_factory=list)
    ai_inference: list[Inference]
    client_features_used: list[str]
    risks: list[Item] = Field(default_factory=list)
    opportunities: list[Item] = Field(default_factory=list)
    actions: list[Item] = Field(default_factory=list)
    questions_to_check: list[str] = Field(default_factory=list)
    bank_product_hint: str | None = None
    relevance: float = Field(ge=0, le=1, description="Насколько событие важно для компании")
    horizon: str = Field(default="", description="Когда может сказаться: сразу / квартал / год")


class InsightRequest(BaseModel):
    news_id: int
    role: str = "ceo"
    force: bool = False  # пересчитать, даже если инсайт уже есть


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)


ROLES = {
    "owner": "Собственник: стратегия, стоимость бизнеса, крупные риски",
    "ceo": "Генеральный директор: операционные и стратегические последствия",
    "cfo": "Финансовый директор: долг, ставки, ликвидность, финансирование",
    "treasury": "Казначейство: валюта, ликвидность, размещение средств, хеджирование",
    "accountant": "Главный бухгалтер: налоги, отчётность, регуляторные изменения",
}
