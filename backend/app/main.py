from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.models import entities  # noqa: F401 - register all ORM tables
from app.models.entities import Company, User
from app.services.catalog import seed_products

DEMO_USERS = [
    (
        "Анна Смирнова",
        "anna@demo.local",
        {
            "name": "ООО «Северный свет»",
            "inn": "7708123456",
            "legal_form": "ООО",
            "registered_at": "2021-04-15",
            "industry": "Торговля",
            "revenue": 1_250_000,
            "expenses": 500_000,
            "obligations": 100_000,
            "overdue": False,
        },
    ),
    (
        "Максим Петров",
        "maxim@demo.local",
        {
            "name": "ИП Петров Максим Сергеевич",
            "inn": "780123456789",
            "legal_form": "ИП",
            "registered_at": "2025-11-12",
            "industry": "Услуги",
            "revenue": 270_000,
            "expenses": 210_000,
            "obligations": 110_000,
            "overdue": True,
        },
    ),
]


def seed_demo_data() -> None:
    db = SessionLocal()
    try:
        seed_products(db)
        for name, email, company in DEMO_USERS:
            user = db.query(User).filter_by(email=email).first()
            if not user:
                user = User(
                    name=name,
                    email=email,
                    password_hash=hash_password(settings.demo_seed_password),
                    role="entrepreneur",
                    is_active=True,
                )
                db.add(user)
                db.flush()
            if not db.query(Company).filter_by(owner_id=user.id).first():
                db.add(Company(owner_id=user.id, **company))
        if not db.query(User).filter_by(email="bank@demo.local").first():
            db.add(
                User(
                    name="Мария Орлова",
                    email="bank@demo.local",
                    password_hash=hash_password(settings.demo_seed_password),
                    role="employee",
                    is_active=True,
                )
            )
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_demo_data()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "Backend для демонстрационного кредитного кабинета предпринимателя. "
        "Все проверки и выдача синтетические."
    ),
    lifespan=lifespan,
)

origins = [
    origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)
app.include_router(router)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "service": "backend"}
