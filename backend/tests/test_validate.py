from app.agent.validate import check_payload

GOOD = {
    "headline": "Кредиты не подешевеют в ближайшие месяцы",
    "what_happened": "ЦБ сохранил ставку 14%",
    "why_important": "У компании кредиты",
    "facts": [{"id": "F1", "text": "Ставка сохранена на 14%", "source": "N1"}],
    "bank_view": [{"id": "B1", "text": "Банк ждёт паузу", "source": "A1"}],
    "ai_inference": [{"id": "I1", "text": "Долговая нагрузка не снизится", "based_on": ["F1", "B1", "has_loans"]}],
    "client_features_used": ["has_loans"],
    "risks": [{"text": "Дорогой рефинанс", "based_on": ["I1"]}],
    "relevance": 0.8,
}


def test_good_payload_passes():
    payload, issues = check_payload(GOOD, {"N1"}, {"A1"}, {"has_loans"})
    assert payload is not None and issues == []


def test_hallucinated_sources_are_caught():
    bad = {**GOOD, "facts": [{"id": "F1", "text": "x", "source": "N9"}], "client_features_used": ["made_up"]}
    _, issues = check_payload(bad, {"N1"}, {"A1"}, {"has_loans"})
    assert any("N9" in i for i in issues) and any("made_up" in i for i in issues)


def test_schema_violation():
    payload, issues = check_payload({"headline": "x"}, {"N1"}, set(), set())
    assert payload is None and issues


def test_inline_refs_are_stripped():
    from app.agent.runner import strip_inline_refs

    d = strip_inline_refs(
        {
            "headline": "Кредиты (loans) не подешевеют [B1].",
            "ai_inference": [{"id": "I1", "text": "Риск для ВЭД (ОАЭ, Индия) [B1, fts].", "based_on": ["B1"]}],
        }
    )
    assert d["headline"] == "Кредиты не подешевеют."
    assert d["ai_inference"][0]["text"] == "Риск для ВЭД (ОАЭ, Индия)."
