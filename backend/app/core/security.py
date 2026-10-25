import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.entities import SessionRecord, User


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode(),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
        dklen=32,
    )
    return (
        "scrypt$"
        + base64.urlsafe_b64encode(salt).decode()
        + "$"
        + base64.urlsafe_b64encode(digest).decode()
    )


def verify_password(password: str, hashed: str) -> bool:
    try:
        scheme, salt_b64, digest_b64 = hashed.split("$", 2)
        if scheme != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        expected = base64.urlsafe_b64decode(digest_b64.encode())
        actual = hashlib.scrypt(
            password.encode(),
            salt=salt,
            n=2**14,
            r=8,
            p=1,
            dklen=len(expected),
        )
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_session(db: Session, user: User):
    raw = secrets.token_urlsafe(48)
    csrf = secrets.token_urlsafe(32)
    record = SessionRecord(
        user_id=user.id,
        token_hash=token_hash(raw),
        csrf_hash=token_hash(csrf),
        csrf_token=csrf,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.session_hours),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return raw, csrf, record


def current_session(request: Request, db: Session = Depends(get_db)):
    raw = request.cookies.get("alfa_session")
    if not raw:
        raise HTTPException(status_code=401, detail="Требуется авторизация")

    record = (
        db.query(SessionRecord)
        .filter(
            SessionRecord.token_hash == token_hash(raw),
            SessionRecord.revoked_at.is_(None),
        )
        .first()
    )
    if not record:
        raise HTTPException(status_code=401, detail="Сессия недействительна")

    now = datetime.now(timezone.utc)
    expires = record.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires <= now:
        record.revoked_at = now
        db.commit()
        raise HTTPException(status_code=401, detail="Сессия истекла")

    if request.method not in ("GET", "HEAD", "OPTIONS"):
        supplied = request.headers.get("x-csrf-token", "")
        if not supplied or not secrets.compare_digest(
            token_hash(supplied), record.csrf_hash
        ):
            raise HTTPException(status_code=403, detail="CSRF-проверка не пройдена")

        origin = request.headers.get("origin")
        allowed = [
            value.strip()
            for value in settings.allowed_origins.split(",")
            if value.strip()
        ]
        if origin and origin not in allowed:
            raise HTTPException(status_code=403, detail="Недопустимый Origin")

    user = db.get(User, record.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Пользователь недоступен")

    request.state.session_record = record
    return user


def entrepreneur(user: User = Depends(current_session)):
    if user.role != "entrepreneur":
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    return user


def employee(user: User = Depends(current_session)):
    if user.role != "employee":
        raise HTTPException(status_code=403, detail="Доступно только сотруднику банка")
    return user
