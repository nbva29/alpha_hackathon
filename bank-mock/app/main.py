import os
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="Alfa Demo Bank Mock",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
)

INTERNAL_KEY = os.getenv("BANK_INTERNAL_KEY", "local-bank-mock-key-change-me")


class Review(BaseModel):
    application_id: str
    attempt: int = 1
    product: dict[str, Any]
    need: dict[str, Any]
    company: dict[str, Any]
    document_kinds: list[str]


def payment(amount, rate, months):
    monthly_rate = rate / 1200
    if months <= 0:
        return 0
    if not monthly_rate:
        return amount / months
    return (
        amount
        * monthly_rate
        * (1 + monthly_rate) ** months
        / ((1 + monthly_rate) ** months - 1)
    )


@app.get("/health")
def health():
    return {"status": "ok", "service": "bank-mock"}


@app.post("/internal/review")
def review(body: Review, x_bank_internal_key: str | None = Header(default=None)):
    if x_bank_internal_key != INTERNAL_KEY:
        raise HTTPException(403, "internal only")

    company = body.company
    need = body.need
    product = body.product
    reasons = []

    required_document = product.get("required_document", product.get("document"))
    if (
        required_document not in body.document_kinds
        and product.get("document") not in body.document_kinds
    ):
        return {
            "outcome": "NEEDS_INFO",
            "fns": "Демо-проверка: синтетические данные",
            "bki": "Проверка выполнена на тестовых данных",
            "financial": "Недостаточно документов для оценки",
            "score": None,
            "reasons": ["Приложите обязательный документ: " + str(required_document)],
            "rate": product.get("rate", 0),
            "payment": 0,
            "decided_at": datetime.now(timezone.utc).isoformat(),
            "rule_version": "rules-1.0",
        }

    monthly = payment(float(need["amount"]), float(product["rate"]), int(need["term"]))
    disposable = (
        float(company.get("revenue", 0))
        - float(company.get("expenses", 0))
        - float(company.get("obligations", 0))
    )

    score = 100
    if company.get("overdue"):
        score -= 55
        reasons.append("По синтетическим данным есть просроченная задолженность")
    if disposable < monthly * 1.25:
        score -= 35
        reasons.append(
            "Свободного денежного потока недостаточно для покрытия платежа "
            "с запасом 1,25×"
        )
    if float(company.get("revenue", 0)) < float(
        product.get("min_revenue", product.get("minRevenue", 0))
    ):
        score -= 15
        reasons.append("Выручка ниже минимального требования продукта")

    if score < 50:
        outcome = "REJECTED"
        note = "Отказ по результатам демонстрационной скоринговой модели"
    else:
        outcome = "APPROVED"
        note = "Условно одобрено автоматическим Rule Engine (демо)"
        reasons = []

    return {
        "outcome": outcome,
        "fns": "Демо-проверка пройдена; данные не запрашивались у ФНС",
        "bki": (
            "Просрочка обнаружена"
            if company.get("overdue")
            else "По синтетическим данным просрочек нет"
        ),
        "financial": "Финансовые показатели рассчитаны по анкете",
        "score": max(0, score),
        "reasons": reasons,
        "rate": float(product["rate"]),
        "payment": round(monthly, 2),
        "decided_at": datetime.now(timezone.utc).isoformat(),
        "note": note,
        "rule_version": "rules-1.0",
    }
