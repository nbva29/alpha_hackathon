import httpx
import json
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app


def login(client, email="anna@demo.local"):
    result = client.post(
        "/api/auth/login", json={"email": email, "password": "demo123"}
    )
    assert result.status_code == 200
    return {"X-CSRF-Token": result.json()["csrfToken"]}


def test_retrieval_prefers_relevant_overdraft_products():
    from app.services.assistant import retrieve_products

    with TestClient(app), SessionLocal() as db:
        products = retrieve_products(
            db, "Какие документы нужны для овердрафта?", limit=3
        )
    assert products
    assert all(item["category"] == "overdraft" for item in products)
    assert all(item["id"] and item["version"] for item in products)


def test_generic_catalog_question_retrieves_all_active_products():
    from app.services.assistant import retrieve_products

    with TestClient(app), SessionLocal() as db:
        products = retrieve_products(db, "Какие есть кредитные продукты?")
    assert len(products) == 6
    assert all("document" in item and "rate" in item for item in products)


def test_unclassified_question_filters_catalog_by_amount():
    from app.services.assistant import retrieve_products

    with TestClient(app), SessionLocal() as db:
        products = retrieve_products(db, "Что подойдет на 10 миллионов?")
    assert [item["id"] for item in products] == ["growth-plus"]


def test_retrieval_filters_products_by_explicit_amount_and_term():
    from app.services.assistant import retrieve_products

    with TestClient(app), SessionLocal() as db:
        products = retrieve_products(
            db, "Какой кредит подходит для оборудования на 1,2 млн рублей на 24 месяца?"
        )
    assert [item["id"] for item in products] == ["growth-start"]


def test_requested_amount_prefers_loan_sum_over_revenue_and_expenses():
    from app.services.assistant import requested_amount_and_term

    assert requested_amount_and_term(
        "Оборот 700 тыс, затраты 500 тыс, нужен кредит на оборудование на 1 млн"
    )[0] == 1000000
    assert requested_amount_and_term(
        "Нужен кредит на 1 млн, оборот 700 тыс и затраты 500 тыс"
    )[0] == 1000000


def test_comparison_retrieves_both_named_products_across_categories():
    from app.services.assistant import retrieve_products

    with TestClient(app), SessionLocal() as db:
        products = retrieve_products(
            db, "Чем отличается Бизнес-рост Плюс от Оборотного Про?"
        )
    assert {item["id"] for item in products} == {"growth-plus", "turnover-pro"}


def test_assistant_calls_local_model_with_retrieved_catalog(monkeypatch):
    import app.integrations.llm_client as llm_client

    monkeypatch.setattr(
        llm_client.settings, "ai_base_url", "http://localhost:1234/v1", raising=False
    )
    monkeypatch.setattr(
        llm_client.settings, "ai_model", "qwen3:4b-instruct", raising=False
    )
    requests = []

    def fake_post(url, json, timeout):
        requests.append((url, json, timeout))
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": "Для овердрафта нужна выписка по счёту."}}
                ]
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(llm_client.httpx, "post", fake_post)
    with TestClient(app) as client:
        headers = login(client)
        result = client.post(
            "/api/assistant",
            headers=headers,
            json={"message": "Какой документ нужен для овердрафта?"},
        )
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["mode"] == "local-llm"
    assert body["answer"] == "Для овердрафта нужна выписка по счёту."
    assert body["sources"]
    assert all(item["category"] == "overdraft" for item in body["sources"])
    assert requests[0][0] == "http://localhost:1234/v1/chat/completions"
    assert requests[0][1]["model"] == "qwen3:4b-instruct"
    assert "statement" in requests[0][1]["messages"][1]["content"]
    assert "выписка по счёту" in requests[0][1]["messages"][1]["content"].lower()


def test_assistant_falls_back_when_model_is_unavailable(monkeypatch):
    import app.integrations.llm_client as llm_client

    monkeypatch.setattr(
        llm_client.settings, "ai_base_url", "http://localhost:1234/v1", raising=False
    )

    def unavailable(url, json, timeout):
        raise httpx.ConnectError("not running")

    monkeypatch.setattr(llm_client.httpx, "post", unavailable)
    with TestClient(app) as client:
        headers = login(client)
        result = client.post(
            "/api/assistant",
            headers=headers,
            json={"message": "Документы для овердрафта"},
        )
    assert result.status_code == 200
    assert result.json()["mode"] == "deterministic-fallback"
    assert "выписк" in result.json()["answer"].lower()


def test_assistant_rejects_foreign_application_before_model_call(monkeypatch):
    import app.integrations.llm_client as llm_client

    monkeypatch.setattr(
        llm_client.settings, "ai_base_url", "http://localhost:1234/v1", raising=False
    )
    called = False

    def fake_post(url, json, timeout):
        nonlocal called
        called = True
        raise AssertionError("model should not see foreign application")

    monkeypatch.setattr(llm_client.httpx, "post", fake_post)
    with TestClient(app) as client:
        anna_headers = login(client)
        products = client.get("/api/credit-products").json()
        product = next(item for item in products if item["id"] == "growth-start")
        created = client.post(
            "/api/applications",
            headers=anna_headers,
            json={
                "product_id": product["id"],
                "need": {
                    "purpose": "Оборудование",
                    "category": "development",
                    "amount": 1200000,
                    "term": 24,
                },
            },
        )
        assert created.status_code == 201
        maxim_headers = login(client, "maxim@demo.local")
        result = client.post(
            "/api/assistant",
            headers=maxim_headers,
            json={"message": "Какой статус?", "application_id": created.json()["id"]},
        )
    assert result.status_code == 404
    assert not called


def test_assistant_rejects_rate_not_present_in_retrieved_catalog(monkeypatch):
    import app.integrations.llm_client as llm_client

    monkeypatch.setattr(
        llm_client.settings, "ai_base_url", "http://localhost:1234/v1", raising=False
    )

    def fake_post(url, json, timeout):
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Одобрено под 99% годовых."}}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(llm_client.httpx, "post", fake_post)
    with TestClient(app) as client:
        headers = login(client)
        result = client.post(
            "/api/assistant", headers=headers, json={"message": "Ставка овердрафта?"}
        )
    assert result.status_code == 200
    assert result.json()["mode"] == "deterministic-fallback"
    assert "99%" not in result.json()["answer"]


def test_assistant_rejects_product_outside_filtered_sources(monkeypatch):
    import app.integrations.llm_client as llm_client

    monkeypatch.setattr(
        llm_client.settings, "ai_base_url", "http://localhost:1234/v1", raising=False
    )

    def fake_post(url, json, timeout):
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Подходит Бизнес-рост Плюс."}}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(llm_client.httpx, "post", fake_post)
    with TestClient(app) as client:
        headers = login(client)
        result = client.post(
            "/api/assistant",
            headers=headers,
            json={
                "message": "Какой кредит подходит для оборудования на 1,2 млн на 24 месяца?"
            },
        )
    assert result.status_code == 200
    assert result.json()["mode"] == "deterministic-fallback"
    assert all(item["id"] != "growth-plus" for item in result.json()["sources"])


def test_assistant_never_calls_nonlocal_inference_url(monkeypatch):
    import app.integrations.llm_client as llm_client

    monkeypatch.setattr(
        llm_client.settings, "ai_base_url", "https://external.example/v1", raising=False
    )

    def fake_post(url, json, timeout):
        raise AssertionError("external model must not receive private data")

    monkeypatch.setattr(llm_client.httpx, "post", fake_post)
    with TestClient(app) as client:
        headers = login(client)
        result = client.post(
            "/api/assistant", headers=headers, json={"message": "Условия овердрафта"}
        )
    assert result.status_code == 200
    assert result.json()["mode"] == "deterministic-fallback"


def test_assistant_uses_expert_configured_https_model_and_api_key(monkeypatch):
    import app.integrations.llm_client as llm_client

    monkeypatch.setattr(llm_client.settings, "ai_base_url", "https://models.example/v1")
    monkeypatch.setattr(llm_client.settings, "ai_model", "expert-open-weight-model")
    monkeypatch.setattr(llm_client.settings, "ai_api_key", "test-secret")
    monkeypatch.setattr(llm_client.settings, "ai_allow_remote", True)
    calls = []

    def fake_post(url, json, headers, timeout):
        calls.append((url, json, headers))
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Ответ по справочнику."}}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(llm_client.httpx, "post", fake_post)
    answer = llm_client.complete("Вопрос", [], None)
    assert answer == "Ответ по справочнику."
    assert calls[0][0] == "https://models.example/v1/chat/completions"
    assert calls[0][1]["model"] == "expert-open-weight-model"
    assert calls[0][2] == {"Authorization": "Bearer test-secret"}


def test_assistant_falls_back_on_truncated_model_response(monkeypatch):
    import app.integrations.llm_client as llm_client

    monkeypatch.setattr(
        llm_client.settings, "ai_base_url", "http://localhost:1234/v1", raising=False
    )

    def fake_post(url, json, timeout):
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"finish_reason": "length", "message": {"content": "Вам нужен"}}
                ]
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(llm_client.httpx, "post", fake_post)
    with TestClient(app) as client:
        headers = login(client)
        result = client.post(
            "/api/assistant",
            headers=headers,
            json={"message": "Документ для овердрафта"},
        )
    assert result.status_code == 200
    assert result.json()["mode"] == "deterministic-fallback"


def test_assistant_sends_page_and_owned_workspace_context_to_model(monkeypatch):
    import app.integrations.llm_client as llm_client

    monkeypatch.setattr(llm_client.settings, "ai_base_url", "http://localhost:1234/v1")
    captured = []

    def fake_post(url, json, timeout):
        captured.append(json["messages"][1]["content"])
        return httpx.Response(200, json={"choices": [{"message": {"content": "Сравню условия."}}]}, request=httpx.Request("POST", url))

    monkeypatch.setattr(llm_client.httpx, "post", fake_post)
    with TestClient(app) as client:
        headers = login(client)
        created = client.post("/api/applications", headers=headers, json={
            "product_id": "growth-start",
            "need": {"purpose": "Оборудование", "category": "development", "amount": 1200000, "term": 24},
        })
        assert created.status_code == 201
        result = client.post("/api/assistant", headers=headers, json={
            "message": "Сравни варианты и документы",
            "application_id": created.json()["id"],
            "page_context": {"page": "application", "selected_product_ids": ["growth-start", "growth-plus"], "need": {"purpose": "Оборудование", "category": "development", "amount": 1200000, "term": 24}},
        })
    assert result.status_code == 200
    context = json.loads(captured[0])
    assert context["page_context"]["page"] == "application"
    assert [p["id"] for p in context["page_context"]["selected_products"]] == ["growth-start", "growth-plus"]
    assert context["company"]["inn"]
    assert context["application"]["documents"] == []
    assert context["application"]["need"]["amount"] == 1200000
    assert any(item["id"] == created.json()["id"] for item in context["applications"])


def test_assistant_does_not_offer_products_outside_need_as_alternatives():
    with TestClient(app) as client:
        headers = login(client)
        response = client.post("/api/assistant", headers=headers, json={
            "message": "Какой кредит для оборудования на 1,2 млн на 24 месяца?",
            "page_context": {"page": "catalog", "selected_product_ids": ["growth-start", "growth-plus"]},
        })
    assert response.status_code == 200
    assert response.json()["alternatives"] == []


def test_assistant_offers_only_eligible_alternatives_with_pros_and_cons():
    with TestClient(app) as client:
        headers = login(client)
        response = client.post("/api/assistant", headers=headers, json={
            "message": "Что думаешь про кредит Бизнес-рост для оборудования на 4 млн на 24 месяца?",
            "page_context": {"page": "catalog", "need": {
                "purpose": "Оборудование", "category": "development", "amount": 4000000, "term": 24,
            }},
        })
    assert response.status_code == 200
    alternatives = response.json()["alternatives"]
    assert [item["product"]["id"] for item in alternatives] == ["growth-plus"]
    assert alternatives[0]["fits"] is True
    assert alternatives[0]["pros"] and alternatives[0]["cons"]


def test_short_comparison_question_uses_selected_products_without_model_hallucinations(monkeypatch):
    import app.integrations.llm_client as llm_client

    monkeypatch.setattr(llm_client.settings, "ai_base_url", "http://localhost:1234/v1")
    captured = []

    def fake_post(url, json, timeout):
        captured.append(__import__("json").loads(json["messages"][1]["content"]))
        return httpx.Response(200, json={"choices": [{"message": {"content": "Бизнес-рост подходит."}}]}, request=httpx.Request("POST", url))

    monkeypatch.setattr(llm_client.httpx, "post", fake_post)
    with TestClient(app) as client:
        headers = login(client)
        response = client.post("/api/assistant", headers=headers, json={
            "message": "Что лучше?",
            "page_context": {"page": "catalog", "selected_product_ids": ["growth-start", "growth-plus"],
                             "need": {"purpose": "Оборудование", "category": "development", "amount": 1200000, "term": 24}},
        })
    assert response.status_code == 200
    assert len(captured) == 1
    assert [item["id"] for item in captured[0]["comparison_facts"]] == ["growth-start", "growth-plus"]
    assert [item["id"] for item in response.json()["sources"]] == ["growth-start", "growth-plus"]
    assert response.json()["mode"] == "verified-comparison"
    assert "сумма вне диапазона" in response.json()["answer"]
    assert response.json()["alternatives"] == []


def test_assistant_rejects_model_recommendation_of_ineligible_selected_product(monkeypatch):
    import app.integrations.llm_client as llm_client

    monkeypatch.setattr(llm_client.settings, "ai_base_url", "http://localhost:1234/v1")

    def fake_post(url, json, timeout):
        return httpx.Response(200, json={"choices": [{"message": {"content": "Рекомендую Бизнес-рост Плюс."}}]}, request=httpx.Request("POST", url))

    monkeypatch.setattr(llm_client.httpx, "post", fake_post)
    with TestClient(app) as client:
        headers = login(client)
        response = client.post("/api/assistant", headers=headers, json={
            "message": "Что лучше?",
            "page_context": {"page": "catalog", "selected_product_ids": ["growth-start", "growth-plus"],
                             "need": {"purpose": "Оборудование", "category": "development", "amount": 1200000, "term": 24}},
        })
    assert response.status_code == 200
    assert response.json()["mode"] == "verified-comparison"
    assert "Рекомендую Бизнес-рост Плюс" not in response.json()["answer"]


def test_short_comparison_of_two_eligible_products_includes_rates_limits_and_tradeoff(monkeypatch):
    import app.integrations.llm_client as llm_client

    monkeypatch.setattr(llm_client.settings, "ai_base_url", "http://localhost:1234/v1")

    def fake_post(url, json, timeout):
        return httpx.Response(200, json={"choices": [{"message": {"content": "Бизнес-рост лучше. Максимум 500 тыс, а Бизнес-рост Плюс требует возраст 24 года."}}]}, request=httpx.Request("POST", url))

    monkeypatch.setattr(llm_client.httpx, "post", fake_post)
    with TestClient(app) as client:
        headers = login(client)
        response = client.post("/api/assistant", headers=headers, json={
            "message": "Чем отличаются?",
            "page_context": {"page": "catalog", "selected_product_ids": ["growth-start", "growth-plus"],
                             "need": {"purpose": "Оборудование", "category": "development", "amount": 4000000, "term": 24}},
        })
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "verified-comparison"
    assert "16,9%" in body["answer"] and "15,9%" in body["answer"]
    assert "5 000 000" in body["answer"] and "15 000 000" in body["answer"]
    assert "поручительство" in body["answer"].lower()
    assert "500 тыс" not in body["answer"] and "24 года" not in body["answer"]


def test_comparison_never_displays_model_collateral_contradiction(monkeypatch):
    import app.integrations.llm_client as llm_client

    monkeypatch.setattr(llm_client.settings, "ai_base_url", "http://localhost:1234/v1")

    def fake_post(url, json, timeout):
        return httpx.Response(200, json={"choices": [{"message": {"content":
            "Бизнес-рост: 16,9%, до 5 млн ₽, без залога, но требует залога. "
            "Бизнес-рост Плюс: 15,9%, до 15 млн ₽, поручительство."}}]}, request=httpx.Request("POST", url))

    monkeypatch.setattr(llm_client.httpx, "post", fake_post)
    with TestClient(app) as client:
        headers = login(client)
        response = client.post("/api/assistant", headers=headers, json={
            "message": "Чем отличаются?",
            "page_context": {"page": "catalog", "selected_product_ids": ["growth-start", "growth-plus"],
                             "need": {"purpose": "Оборудование", "category": "development", "amount": 4000000, "term": 24}},
        })
    assert response.status_code == 200
    assert response.json()["mode"] == "verified-comparison"
    assert "требует залога" not in response.json()["answer"].lower()


def test_consultant_gives_model_missing_document_and_uses_saved_application_need(monkeypatch):
    import app.integrations.llm_client as llm_client

    monkeypatch.setattr(llm_client.settings, "ai_base_url", "http://localhost:1234/v1")
    captured = []

    def fake_post(url, json, timeout):
        captured.append(__import__("json").loads(json["messages"][1]["content"]))
        return httpx.Response(200, json={"choices": [{"message": {"content": "Не хватает финансовой отчётности."}}]}, request=httpx.Request("POST", url))

    monkeypatch.setattr(llm_client.httpx, "post", fake_post)
    with TestClient(app) as client:
        headers = login(client)
        created = client.post("/api/applications", headers=headers, json={
            "product_id": "growth-start",
            "need": {"purpose": "Оборудование", "category": "development", "amount": 1200000, "term": 24},
        })
        app_id = created.json()["id"]
        response = client.post("/api/assistant", headers=headers, json={
            "message": "Чего не хватает?", "application_id": app_id,
            "page_context": {"page": "application", "need": {
                "purpose": "Другой черновик", "category": "turnover", "amount": 8000000, "term": 36,
            }},
            "history": [{"role": "user", "text": "Помоги с заявкой"}],
        })
    assert response.status_code == 200
    facts = captured[0]["advisor_context"]
    assert facts["need"]["amount"] == 1200000
    assert facts["missing_documents"] == ["финансовая отчётность"]
    assert "запрос" in facts["missing_document_effect"].lower()
    assert "NEEDS_INFO" not in facts["missing_document_effect"]
    assert facts["next_action"]
    assert captured[0]["conversation"] == [{"role": "user", "text": "Помоги с заявкой"}]
    assert [item["id"] for item in captured[0]["products"]] == ["growth-start"]
    assert [item["id"] for item in response.json()["sources"]] == ["growth-start"]


def test_consultant_gives_model_risk_factors_from_company_data(monkeypatch):
    import app.integrations.llm_client as llm_client

    monkeypatch.setattr(llm_client.settings, "ai_base_url", "http://localhost:1234/v1")
    captured = []

    def fake_post(url, json, timeout):
        captured.append(__import__("json").loads(json["messages"][1]["content"]))
        return httpx.Response(200, json={"choices": [{"message": {"content": "Есть риск из-за просрочки и недостаточной выручки."}}]}, request=httpx.Request("POST", url))

    monkeypatch.setattr(llm_client.httpx, "post", fake_post)
    with TestClient(app) as client:
        headers = login(client, "maxim@demo.local")
        response = client.post("/api/assistant", headers=headers, json={
            "message": "Почему могут отказать?",
            "page_context": {"page": "catalog", "selected_product_ids": ["growth-start"],
                             "need": {"purpose": "Оборудование", "category": "development", "amount": 1200000, "term": 24}},
        })
    assert response.status_code == 200
    risks = " ".join(captured[0]["advisor_context"]["risk_factors"]).lower()
    assert "просроч" in risks
    assert "выручк" in risks


def test_short_comparison_is_answered_by_model_with_verified_product_facts(monkeypatch):
    import app.integrations.llm_client as llm_client

    monkeypatch.setattr(llm_client.settings, "ai_base_url", "http://localhost:1234/v1")
    captured = []

    def fake_post(url, json, timeout):
        captured.append(__import__("json").loads(json["messages"][1]["content"]))
        return httpx.Response(200, json={"choices": [{"message": {"content":
            "Оба подходят. Бизнес-рост: 16,9%, до 5 млн ₽, без залога. Бизнес-рост Плюс: 15,9%, до 15 млн ₽, поручительство. "
            "Если важны ставка и запас по сумме, выбирайте Бизнес-рост Плюс; если важнее отсутствие залога, рассмотрите Бизнес-рост."}}]}, request=httpx.Request("POST", url))

    monkeypatch.setattr(llm_client.httpx, "post", fake_post)
    with TestClient(app) as client:
        headers = login(client)
        response = client.post("/api/assistant", headers=headers, json={
            "message": "Чем отличаются?",
            "page_context": {"page": "catalog", "selected_product_ids": ["growth-start", "growth-plus"],
                             "need": {"purpose": "Оборудование", "category": "development", "amount": 4000000, "term": 24}},
        })
    assert response.status_code == 200
    assert response.json()["mode"] == "local-llm"
    assert [item["fits"] for item in captured[0]["comparison_facts"]] == [True, True]
    assert captured[0]["advisor_context"]["need"]["amount"] == 4000000
    assert "Оба" in captured[0]["verified_comparison"] or "Подходит" in captured[0]["verified_comparison"]
    assert captured[0]["applications"] == []


def test_comparison_accepts_grounded_model_tradeoff_without_repeating_smaller_limit(monkeypatch):
    import app.integrations.llm_client as llm_client

    monkeypatch.setattr(llm_client.settings, "ai_base_url", "http://localhost:1234/v1")

    def fake_post(url, json, timeout):
        return httpx.Response(200, json={"choices": [{"message": {"content":
            "Оба подходят для 4 млн ₽ на 24 месяца. Бизнес-рост Плюс: ставка 15,9% против 16,9% у Бизнес-рост, "
            "лимит до 15 млн ₽, но нужно поручительство. Бизнес-рост доступен без залога."}}]}, request=httpx.Request("POST", url))

    monkeypatch.setattr(llm_client.httpx, "post", fake_post)
    with TestClient(app) as client:
        headers = login(client)
        response = client.post("/api/assistant", headers=headers, json={
            "message": "Что лучше?",
            "page_context": {"page": "catalog", "selected_product_ids": ["growth-start", "growth-plus"],
                             "need": {"purpose": "Оборудование", "category": "development", "amount": 4000000, "term": 24}},
        })
    assert response.json()["mode"] == "local-llm"


def test_comparison_rejects_model_claim_that_eligible_product_does_not_fit(monkeypatch):
    import app.integrations.llm_client as llm_client

    monkeypatch.setattr(llm_client.settings, "ai_base_url", "http://localhost:1234/v1")

    def fake_post(url, json, timeout):
        return httpx.Response(200, json={"choices": [{"message": {"content":
            "Бизнес-рост: 16,9%, до 5 млн ₽, не подходит. "
            "Бизнес-рост Плюс: 15,9%, до 15 млн ₽, подходит."}}]}, request=httpx.Request("POST", url))

    monkeypatch.setattr(llm_client.httpx, "post", fake_post)
    with TestClient(app) as client:
        headers = login(client)
        response = client.post("/api/assistant", headers=headers, json={
            "message": "Что лучше?",
            "page_context": {"page": "catalog", "selected_product_ids": ["growth-start", "growth-plus"],
                             "need": {"purpose": "Оборудование", "category": "development", "amount": 4000000, "term": 24}},
        })
    assert response.json()["mode"] == "verified-comparison"


def test_consultant_rejects_model_claim_of_refusal_for_missing_document(monkeypatch):
    import app.integrations.llm_client as llm_client

    monkeypatch.setattr(llm_client.settings, "ai_base_url", "http://localhost:1234/v1")

    def fake_post(url, json, timeout):
        return httpx.Response(200, json={"choices": [{"message": {"content":
            "Заявка может быть отклонена из-за отсутствия финансовой отчётности. "
            "Без неё будет NEEDS_INFO, но отклонение связано исключительно с документом."}}]}, request=httpx.Request("POST", url))

    monkeypatch.setattr(llm_client.httpx, "post", fake_post)
    with TestClient(app) as client:
        headers = login(client)
        created = client.post("/api/applications", headers=headers, json={
            "product_id": "growth-start",
            "need": {"purpose": "Оборудование", "category": "development", "amount": 1200000, "term": 24},
        })
        response = client.post("/api/assistant", headers=headers, json={
            "message": "Почему могут отказать?", "application_id": created.json()["id"],
        })
    assert response.json()["mode"] == "deterministic-fallback"
    assert "Не хватает документа" in response.json()["answer"]
    assert "не отказ" in response.json()["answer"]
    assert "DRAFT" not in response.json()["answer"]
    assert "NEEDS_INFO" not in response.json()["answer"]


def test_consultant_hides_internal_status_codes_in_model_answer(monkeypatch):
    import app.integrations.llm_client as llm_client

    monkeypatch.setattr(llm_client.settings, "ai_base_url", "http://localhost:1234/v1")

    def fake_post(url, json, timeout):
        return httpx.Response(200, json={"choices": [{"message": {"content":
            "Приложите финансовую отчётность, иначе проверка вернёт NEEDS_INFO."}}]}, request=httpx.Request("POST", url))

    monkeypatch.setattr(llm_client.httpx, "post", fake_post)
    with TestClient(app) as client:
        headers = login(client)
        created = client.post("/api/applications", headers=headers, json={
            "product_id": "growth-start",
            "need": {"purpose": "Оборудование", "category": "development", "amount": 1200000, "term": 24},
        })
        response = client.post("/api/assistant", headers=headers, json={
            "message": "Чего не хватает?", "application_id": created.json()["id"],
        })
    assert response.json()["mode"] == "local-llm"
    assert "NEEDS_INFO" not in response.json()["answer"]
    assert "дополнить заявку" in response.json()["answer"]


def test_consultant_keeps_correct_model_explanation_that_missing_document_is_not_refusal(monkeypatch):
    import app.integrations.llm_client as llm_client

    monkeypatch.setattr(llm_client.settings, "ai_base_url", "http://localhost:1234/v1")

    def fake_post(url, json, timeout):
        return httpx.Response(200, json={"choices": [{"message": {"content":
            "Нужно приложить финансовую отчётность. Без документа попросят дополнить заявку; это не отказ."}}]}, request=httpx.Request("POST", url))

    monkeypatch.setattr(llm_client.httpx, "post", fake_post)
    with TestClient(app) as client:
        headers = login(client)
        created = client.post("/api/applications", headers=headers, json={
            "product_id": "growth-start",
            "need": {"purpose": "Оборудование", "category": "development", "amount": 1200000, "term": 24},
        })
        response = client.post("/api/assistant", headers=headers, json={
            "message": "Что от меня ещё требуется?", "application_id": created.json()["id"],
            "history": [{"role": "assistant", "text": "Проверяю черновик заявки."}],
        })
    assert response.json()["mode"] == "local-llm"
    assert "не отказ" in response.json()["answer"]
