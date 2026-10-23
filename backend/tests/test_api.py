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
        assert submitted.json()["status"] == "APPROVED"

        accepted = client.post(
            f"/api/applications/{app_id}/accept-offer", headers=headers
        )
        assert accepted.status_code == 200
        assert accepted.json()["status"] == "OFFER_ACCEPTED"

        signed = client.post(f"/api/applications/{app_id}/sign-demo", headers=headers)
        assert signed.status_code == 200
        assert signed.json()["status"] == "DISBURSED_DEMO"
        assert len(signed.json()["history"]) >= 7
