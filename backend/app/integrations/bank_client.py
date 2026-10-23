import httpx
from fastapi import HTTPException

from app.core.config import settings


def review(payload):
    try:
        response = httpx.post(
            settings.bank_mock_url.rstrip("/") + "/internal/review",
            json=payload,
            headers={"X-Bank-Internal-Key": settings.bank_internal_key},
            timeout=8.0,
        )
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Демо-банк временно недоступен; заявка сохранена, "
                "повторите отправку позже"
            ),
        ) from exc
