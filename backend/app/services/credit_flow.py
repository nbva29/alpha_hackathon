from datetime import datetime, timezone

from fastapi import HTTPException

from app.models.entities import (
    AuditEvent,
    CreditProduct,
    StatusHistory,
)
from app.services.catalog import product_dict

ALLOWED = {
    "DRAFT": ["SUBMITTED"],
    "NEEDS_INFO": ["SUBMITTED"],
    "SUBMITTED": ["CHECKING"],
    "CHECKING": ["NEEDS_INFO", "SCORING"],
    "SCORING": ["DECISION_PENDING"],
    "DECISION_PENDING": ["NEEDS_INFO", "APPROVED", "REJECTED"],
    "APPROVED": ["OFFER_ACCEPTED"],
    "OFFER_ACCEPTED": ["SIGNED_DEMO"],
    "SIGNED_DEMO": ["DISBURSED_DEMO"],
}


def transition(db, application, to, description):
    if to not in ALLOWED.get(application.status, []):
        raise HTTPException(
            status_code=409,
            detail=f"Переход {application.status} → {to} недоступен",
        )
    application.status = to
    application.updated_at = datetime.now(timezone.utc)
    db.add(
        StatusHistory(
            application_id=application.id,
            status=to,
            description=description,
        )
    )


def age_months(date_str):
    try:
        registered = datetime.strptime(date_str, "%Y-%m-%d").date()
        today = datetime.now().date()
        return max(
            0,
            (today.year - registered.year) * 12
            + today.month
            - registered.month
            - (today.day < registered.day),
        )
    except Exception:
        return 0


def monthly_payment(amount, rate, months):
    monthly_rate = rate / 1200
    if months <= 0:
        return 0
    if monthly_rate == 0:
        return amount / months
    return (
        amount
        * monthly_rate
        * (1 + monthly_rate) ** months
        / ((1 + monthly_rate) ** months - 1)
    )


def application_dict(db, application):
    product = db.get(CreditProduct, application.product_id)
    documents = [
        {
            "id": document.id,
            "name": document.name,
            "mime": document.mime,
            "size": document.size,
            "kind": document.kind,
            "addedAt": document.created_at.isoformat(),
        }
        for document in application.documents
    ]
    checks = [
        {
            "date": check.created_at.isoformat(),
            "fns": check.fns,
            "bki": check.bki,
            "financial": check.financial,
            "score": check.score,
            "reasons": check.score_reasons,
        }
        for check in application.checks
    ]
    decision = None
    if application.decision:
        decision = {
            "approved": application.decision.approved,
            "reasons": application.decision.reasons,
            "rate": application.decision.rate,
            "payment": application.decision.monthly_payment,
            "decidedAt": application.decision.decided_at.isoformat(),
            "note": application.decision.note,
            "outcome": application.decision.outcome,
        }
    return {
        "id": application.id,
        "status": application.status,
        "productId": application.product_id,
        "productVersion": application.product_version,
        "product": product_dict(product) if product else None,
        "need": {
            "purpose": application.purpose,
            "category": application.category,
            "amount": application.amount,
            "term": application.term,
        },
        "company": application.company_snapshot,
        "documents": documents,
        "checks": checks,
        "decision": decision,
        "createdAt": application.created_at.isoformat(),
        "updatedAt": application.updated_at.isoformat(),
        "history": [
            {
                "status": item.status,
                "date": item.created_at.isoformat(),
                "description": item.description,
            }
            for item in application.history
        ],
    }


def audit(db, user_id, action, application_id=None, details=None):
    db.add(
        AuditEvent(
            user_id=user_id,
            action=action,
            application_id=application_id,
            details=details or {},
        )
    )
