from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_demo_login_and_csrf():
    with TestClient(app) as client:
        response = client.post(
            "/api/auth/login",
            json={"email": "anna@demo.local", "password": "demo123"},
        )
        assert response.status_code == 200
        assert response.json()["user"]["role"] == "entrepreneur"

        token = response.json()["csrfToken"]
        me = client.get("/api/auth/me")
        assert me.status_code == 200
        assert me.json()["csrfToken"] == token

        assert client.post("/api/auth/logout").status_code == 403
        assert (
            client.post("/api/auth/logout", headers={"X-CSRF-Token": token}).status_code
            == 200
        )


def test_complete_credit_flow(monkeypatch):
    import app.api.routes as routes

    monkeypatch.setattr(
        routes,
        "review",
        lambda payload: {
            "outcome": "APPROVED",
            "fns": "synthetic",
            "bki": "clear",
            "financial": "ok",
            "score": 90,
            "reasons": [],
            "rate": 16.9,
            "payment": 59000,
            "note": "test approved",
            "rule_version": "test",
        },
    )

    with TestClient(app) as client:
        login = client.post(
            "/api/auth/login",
            json={"email": "anna@demo.local", "password": "demo123"},
        ).json()
        headers = {"X-CSRF-Token": login["csrfToken"]}

        products = client.get("/api/credit-products").json()
        product = next(item for item in products if item["id"] == "growth-start")

        created = client.post(
            "/api/applications",
            headers=headers,
            json={
                "product_id": product["id"],
                "need": {
                    "purpose": "Оборудование",
                    "category": "development",
                    "amount": 1_200_000,
                    "term": 24,
                },
            },
        )
        assert created.status_code == 201, created.text
        app_id = created.json()["id"]

        upload = client.post(
            f"/api/applications/{app_id}/documents",
            headers=headers,
            data={"kind": "financial"},
            files={"file": ("financial.pdf", b"%PDF-1.4 demo", "application/pdf")},
        )
        assert upload.status_code == 201, upload.text

        submitted = client.post(f"/api/applications/{app_id}/submit", headers=headers)
        assert submitted.status_code == 200, submitted.text
        assert submitted.json()["status"] == "DECISION_PENDING"
        assert (
            client.post(
                f"/api/bank/applications/{app_id}/decision",
                headers=headers,
                json={"action": "approve"},
            ).status_code
            == 403
        )

        employee_login = client.post(
            "/api/auth/login",
            json={"email": "bank@demo.local", "password": "demo123"},
        )
        assert employee_login.status_code == 200
        employee_headers = {"X-CSRF-Token": employee_login.json()["csrfToken"]}
        queue = client.get("/api/bank/applications")
        assert queue.status_code == 200
        assert any(item["application"]["id"] == app_id for item in queue.json())
        document_id = upload.json()["id"]
        downloaded = client.get(
            f"/api/bank/applications/{app_id}/documents/{document_id}"
        )
        assert downloaded.status_code == 200
        assert downloaded.content == b"%PDF-1.4 demo"
        decided = client.post(
            f"/api/bank/applications/{app_id}/decision",
            headers=employee_headers,
            json={"action": "approve", "comment": "Проверки пройдены"},
        )
        assert decided.status_code == 200, decided.text
        assert decided.json()["status"] == "APPROVED"

        client.post(
            "/api/auth/login", json={"email": "anna@demo.local", "password": "demo123"}
        )
        headers = {"X-CSRF-Token": client.get("/api/auth/me").json()["csrfToken"]}

        accepted = client.post(
            f"/api/applications/{app_id}/accept-offer", headers=headers
        )
        assert accepted.status_code == 200
        assert accepted.json()["status"] == "OFFER_ACCEPTED"

        signed = client.post(f"/api/applications/{app_id}/sign-demo", headers=headers)
        assert signed.status_code == 200
        assert signed.json()["status"] == "DISBURSED_DEMO"
        assert len(signed.json()["history"]) >= 7

        second = client.post(
            "/api/applications",
            headers=headers,
            json={
                "product_id": product["id"],
                "need": {
                    "purpose": "Оборудование",
                    "category": "development",
                    "amount": 1_200_000,
                    "term": 24,
                },
            },
        ).json()
        second_id = second["id"]
        client.post(
            f"/api/applications/{second_id}/documents",
            headers=headers,
            data={"kind": "financial"},
            files={"file": ("financial.pdf", b"%PDF-1.4 demo", "application/pdf")},
        )
        assert (
            client.post(
                f"/api/applications/{second_id}/submit", headers=headers
            ).json()["status"]
            == "DECISION_PENDING"
        )
        employee_login = client.post(
            "/api/auth/login",
            json={"email": "bank@demo.local", "password": "demo123"},
        ).json()
        employee_headers = {"X-CSRF-Token": employee_login["csrfToken"]}
        missing_reason = client.post(
            f"/api/bank/applications/{second_id}/decision",
            headers=employee_headers,
            json={"action": "request_info"},
        )
        assert missing_reason.status_code == 422
        request_info = client.post(
            f"/api/bank/applications/{second_id}/decision",
            headers=employee_headers,
            json={
                "action": "request_info",
                "comment": "Уточните финансовые показатели",
            },
        )
        assert request_info.status_code == 200
        assert request_info.json()["status"] == "NEEDS_INFO"


def test_employee_role_is_required_for_bank_queue_and_client_data():
    with TestClient(app) as client:
        employee = client.post(
            "/api/auth/login",
            json={"email": "bank@demo.local", "password": "demo123"},
        )
        assert employee.status_code == 200
        assert employee.json()["user"]["role"] == "employee"
        assert client.get("/api/bank/applications").status_code == 200
        assert client.get("/api/applications").status_code == 403

        client.post(
            "/api/auth/login", json={"email": "anna@demo.local", "password": "demo123"}
        )
        assert client.get("/api/bank/applications").status_code == 403
