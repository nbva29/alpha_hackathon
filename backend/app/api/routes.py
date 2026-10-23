import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    current_session,
    entrepreneur,
    new_session,
    verify_password,
)
from app.db.session import get_db
from app.integrations.bank_client import review
from app.models.entities import (
    ApplicationDocument,
    BankCheckResult,
    Company,
    CreditDecision,
    CreditProduct,
    LoanApplication,
    StatusHistory,
    User,
)
from app.schemas.api import (
    ApplicationCreate,
    ApplicationPatch,
    AssistantIn,
    CompanyIn,
    LoginIn,
)
from app.services.catalog import product_dict
from app.services.credit_flow import age_months, application_dict, audit, transition

router = APIRouter(prefix="/api")


def company_dict(company):
    if not company:
        return None
    return {
        "name": company.name,
        "inn": company.inn,
        "legalForm": company.legal_form,
        "registeredAt": company.registered_at,
        "industry": company.industry,
        "revenue": company.revenue,
        "expenses": company.expenses,
        "obligations": company.obligations,
        "overdue": company.overdue,
    }


def owned_app(db, user_id, application_id):
    application = (
        db.query(LoanApplication).filter_by(id=application_id, owner_id=user_id).first()
    )
    if not application:
        raise HTTPException(404, "Заявка не найдена")
    return application


@router.post("/auth/login")
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .filter(
            User.email == body.email.strip().lower(),
            User.is_active.is_(True),
        )
        .first()
    )
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Неверная почта или пароль демо-аккаунта")

    raw_token, csrf_token, record = new_session(db, user)
    response.set_cookie(
        "alfa_session",
        raw_token,
        max_age=settings.session_hours * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )
    audit(db, user.id, "auth.login")
    db.commit()

    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        },
        "csrfToken": csrf_token,
        "expiresAt": record.expires_at.isoformat(),
    }


@router.get("/auth/me")
def me(request: Request, user: User = Depends(current_session)):
    record = getattr(request.state, "session_record", None)
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "csrfToken": record.csrf_token if record else None,
        "expiresAt": record.expires_at.isoformat() if record else None,
    }


@router.post("/auth/logout")
def logout(
    request: Request,
    response: Response,
    user: User = Depends(current_session),
    db: Session = Depends(get_db),
):
    record = request.state.session_record
    record.revoked_at = datetime.now(timezone.utc)
    audit(db, user.id, "auth.logout")
    db.commit()
    response.delete_cookie("alfa_session", path="/")
    return {"ok": True}


@router.get("/profile")
def profile(user: User = Depends(entrepreneur), db: Session = Depends(get_db)):
    company = db.query(Company).filter_by(owner_id=user.id).first()
    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        },
        "company": company_dict(company),
    }


@router.get("/companies/me")
def get_company(user: User = Depends(entrepreneur), db: Session = Depends(get_db)):
    return company_dict(db.query(Company).filter_by(owner_id=user.id).first())


@router.put("/companies/me")
def put_company(
    body: CompanyIn,
    user: User = Depends(entrepreneur),
    db: Session = Depends(get_db),
):
    company = db.query(Company).filter_by(owner_id=user.id).first()
    values = {
        "name": body.name.strip(),
        "inn": body.inn,
        "legal_form": body.legal_form,
        "registered_at": body.registered_at,
        "industry": body.industry,
        "revenue": body.revenue,
        "expenses": body.expenses,
        "obligations": body.obligations,
        "overdue": body.overdue,
    }
    if company:
        for key, value in values.items():
            setattr(company, key, value)
    else:
        company = Company(owner_id=user.id, **values)
        db.add(company)

    audit(db, user.id, "company.updated", details={"inn": body.inn})
    db.commit()
    db.refresh(company)
    return company_dict(company)


@router.get("/credit-products")
def list_products(
    category: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(entrepreneur),
):
    query = db.query(CreditProduct).filter_by(active=True)
    if category:
        query = query.filter_by(category=category)
    return [
        product_dict(product) for product in query.order_by(CreditProduct.name).all()
    ]


@router.get("/credit-products/{product_id}")
def get_product(
    product_id: str,
    user: User = Depends(entrepreneur),
    db: Session = Depends(get_db),
):
    product = db.get(CreditProduct, product_id)
    if not product or not product.active:
        raise HTTPException(404, "Кредитное предложение не найдено")
    return product_dict(product)


@router.post("/credit-products/recommendations")
def recommendations(
    body: dict,
    user: User = Depends(entrepreneur),
    db: Session = Depends(get_db),
):
    need = body.get("need", body)
    company = db.query(Company).filter_by(owner_id=user.id).first()
    results = []

    for product in db.query(CreditProduct).filter_by(active=True).all():
        reasons = []
        if need.get("category") and need["category"] != product.category:
            reasons.append("другая цель финансирования")
        if not product.min_amount <= int(need.get("amount", 0)) <= product.max_amount:
            reasons.append("сумма вне диапазона")
        if not product.min_term <= int(need.get("term", 0)) <= product.max_term:
            reasons.append("срок вне диапазона")
        if company and age_months(company.registered_at) < product.min_age_months:
            reasons.append("недостаточный срок работы бизнеса")
        if company and company.revenue < product.min_revenue:
            reasons.append("выручка ниже требования")

        results.append(
            {
                "product": product_dict(product),
                "fits": not reasons,
                "reasons": reasons,
            }
        )

    return sorted(results, key=lambda item: (not item["fits"], item["product"]["rate"]))


@router.get("/applications")
def list_applications(
    user: User = Depends(entrepreneur),
    db: Session = Depends(get_db),
):
    applications = (
        db.query(LoanApplication)
        .filter_by(owner_id=user.id)
        .order_by(LoanApplication.created_at.desc())
        .all()
    )
    return [application_dict(db, application) for application in applications]


@router.post("/applications", status_code=201)
def create_application(
    body: ApplicationCreate,
    user: User = Depends(entrepreneur),
    db: Session = Depends(get_db),
):
    company = db.query(Company).filter_by(owner_id=user.id).first()
    if not company:
        raise HTTPException(400, "Сначала заполните профиль компании")

    product = db.get(CreditProduct, body.product_id)
    if not product or not product.active:
        raise HTTPException(404, "Кредитное предложение не найдено")

    need = body.need
    if need.category != product.category:
        raise HTTPException(400, "Категория заявки не соответствует предложению")

    application = LoanApplication(
        owner_id=user.id,
        product_id=product.id,
        product_version=product.version,
        purpose=need.purpose,
        category=need.category,
        amount=need.amount,
        term=need.term,
        company_snapshot=company_dict(company),
        status="DRAFT",
    )
    db.add(application)
    db.flush()
    db.add(
        StatusHistory(
            application_id=application.id,
            status="DRAFT",
            description="Черновик создан",
        )
    )
    audit(
        db,
        user.id,
        "application.created",
        application.id,
        {"product_id": product.id},
    )
    db.commit()
    db.refresh(application)
    return application_dict(db, application)


@router.get("/applications/{application_id}")
def get_application(
    application_id: str,
    user: User = Depends(entrepreneur),
    db: Session = Depends(get_db),
):
    return application_dict(db, owned_app(db, user.id, application_id))


@router.patch("/applications/{application_id}")
def patch_application(
    application_id: str,
    body: ApplicationPatch,
    user: User = Depends(entrepreneur),
    db: Session = Depends(get_db),
):
    application = owned_app(db, user.id, application_id)
    if application.status not in ("DRAFT", "NEEDS_INFO"):
        raise HTTPException(409, "Редактирование заявки недоступно")

    if body.need:
        field_map = {
            "purpose": "purpose",
            "category": "category",
            "amount": "amount",
            "term": "term",
        }
        for key, value in body.need.items():
            if key in field_map:
                setattr(application, field_map[key], value)

    if body.company:
        snapshot = dict(application.company_snapshot)
        snapshot.update(body.company)
        application.company_snapshot = snapshot

    application.updated_at = datetime.now(timezone.utc)
    audit(db, user.id, "application.updated", application.id)
    db.commit()
    return application_dict(db, application)


@router.get("/applications/{application_id}/history")
def application_history(
    application_id: str,
    user: User = Depends(entrepreneur),
    db: Session = Depends(get_db),
):
    application = owned_app(db, user.id, application_id)
    return [
        {
            "status": item.status,
            "date": item.created_at.isoformat(),
            "description": item.description,
        }
        for item in application.history
    ]


@router.get("/applications/{application_id}/documents")
def list_documents(
    application_id: str,
    user: User = Depends(entrepreneur),
    db: Session = Depends(get_db),
):
    application = owned_app(db, user.id, application_id)
    return [
        {
            "id": document.id,
            "kind": document.kind,
            "name": document.name,
            "mime": document.mime,
            "size": document.size,
            "addedAt": document.created_at.isoformat(),
        }
        for document in application.documents
    ]


@router.post("/applications/{application_id}/documents", status_code=201)
def upload_document(
    application_id: str,
    kind: str = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(entrepreneur),
    db: Session = Depends(get_db),
):
    application = owned_app(db, user.id, application_id)
    if application.status not in ("DRAFT", "NEEDS_INFO"):
        raise HTTPException(409, "Документы этой заявки уже отправлены")
    if kind not in ("financial", "statement"):
        raise HTTPException(422, "Неизвестный тип документа")
    if file.content_type not in ("application/pdf", "image/png", "image/jpeg"):
        raise HTTPException(415, "Допустимы PDF, PNG и JPG")

    data = file.file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(413, "Максимальный размер файла — 1 МБ")
    if not data:
        raise HTTPException(400, "Файл пуст")

    upload_root = Path(settings.upload_dir).resolve()
    upload_root.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "file").suffix.lower()
    storage_path = upload_root / f"{uuid.uuid4().hex}{suffix}"
    storage_path.write_bytes(data)

    old_documents = (
        db.query(ApplicationDocument)
        .filter_by(application_id=application.id, kind=kind)
        .all()
    )
    for document in old_documents:
        try:
            Path(document.storage_path).unlink(missing_ok=True)
        except OSError:
            pass
        db.delete(document)

    document = ApplicationDocument(
        application_id=application.id,
        kind=kind,
        name=Path(file.filename or "document").name[:255],
        mime=file.content_type,
        size=len(data),
        storage_path=str(storage_path),
        sha256=hashlib.sha256(data).hexdigest(),
    )
    db.add(document)
    audit(
        db,
        user.id,
        "document.uploaded",
        application.id,
        {"kind": kind, "size": len(data)},
    )
    db.commit()
    db.refresh(document)

    return {
        "id": document.id,
        "kind": document.kind,
        "name": document.name,
        "mime": document.mime,
        "size": document.size,
        "addedAt": document.created_at.isoformat(),
    }


@router.delete("/applications/{application_id}/documents/{document_id}")
def delete_document(
    application_id: str,
    document_id: str,
    user: User = Depends(entrepreneur),
    db: Session = Depends(get_db),
):
    application = owned_app(db, user.id, application_id)
    if application.status not in ("DRAFT", "NEEDS_INFO"):
        raise HTTPException(409, "Документы этой заявки уже отправлены")

    document = (
        db.query(ApplicationDocument)
        .filter_by(id=document_id, application_id=application.id)
        .first()
    )
    if not document:
        raise HTTPException(404, "Документ не найден")

    Path(document.storage_path).unlink(missing_ok=True)
    db.delete(document)
    audit(db, user.id, "document.deleted", application.id)
    db.commit()
    return {"ok": True}


@router.post("/applications/{application_id}/submit")
def submit(
    application_id: str,
    user: User = Depends(entrepreneur),
    db: Session = Depends(get_db),
):
    application = owned_app(db, user.id, application_id)
    if application.status not in ("DRAFT", "NEEDS_INFO", "CHECKING"):
        raise HTTPException(409, "Заявка уже отправлена или завершена")

    product = db.get(CreditProduct, application.product_id)
    snapshot = application.company_snapshot
    if not snapshot.get("name") or not snapshot.get("inn"):
        raise HTTPException(400, "Проверьте данные компании")
    if not application.purpose or application.amount <= 0 or application.term <= 0:
        raise HTTPException(400, "Проверьте цель, сумму и срок")
    if (
        not product.min_amount <= application.amount <= product.max_amount
        or not product.min_term <= application.term <= product.max_term
    ):
        raise HTTPException(400, "Сумма или срок вне диапазона продукта")
    if age_months(snapshot.get("registeredAt", "")) < product.min_age_months:
        raise HTTPException(
            400,
            "Срок работы бизнеса ниже минимального требования продукта",
        )
    if float(snapshot.get("revenue", 0)) < product.min_revenue:
        raise HTTPException(
            400,
            "Выручка компании ниже минимального требования продукта",
        )

    document_kinds = [document.kind for document in application.documents]
    if application.status != "CHECKING":
        transition(
            db, application, "SUBMITTED", "Заявка отправлена в локальный демо-банк"
        )
        transition(
            db,
            application,
            "CHECKING",
            "Выполняются синтетические проверки",
        )
        application.submitted_at = datetime.now(timezone.utc)

    audit(db, user.id, "application.submitted", application.id)
    db.commit()

    attempt = len(application.checks) + 1
    payload = {
        "application_id": application.id,
        "attempt": attempt,
        "product": product_dict(product),
        "need": {
            "purpose": application.purpose,
            "category": application.category,
            "amount": application.amount,
            "term": application.term,
        },
        "company": snapshot,
        "document_kinds": document_kinds,
    }
    # Mock получает явные имена полей; реальные ФНС и БКИ не вызываются.
    result = review(payload)

    check = BankCheckResult(
        application_id=application.id,
        attempt=attempt,
        fns=result["fns"],
        bki=result["bki"],
        financial=result["financial"],
        score=result.get("score"),
        score_reasons=result.get("reasons", []),
    )
    db.add(check)

    if result["outcome"] == "NEEDS_INFO":
        transition(
            db,
            application,
            "NEEDS_INFO",
            "Требуются дополнительные документы или сведения",
        )
    else:
        transition(
            db,
            application,
            "SCORING",
            "Демонстрационная скоринговая оценка завершена",
        )
        transition(
            db,
            application,
            "DECISION_PENDING",
            "Правила решения применены локальным Rule Engine",
        )

        outcome = result["outcome"]
        approved = outcome == "APPROVED"
        db.add(
            CreditDecision(
                application_id=application.id,
                outcome=outcome,
                approved=approved,
                reasons=result.get("reasons", []),
                rate=result["rate"],
                monthly_payment=result["payment"],
                note=result.get("note", "Решение сформировано демо-правилами"),
                rule_version=result.get("rule_version", "rules-1.0"),
            )
        )
        transition(
            db,
            application,
            outcome,
            "Демо-решение: " + ("предварительно одобрено" if approved else "отказ"),
        )

    audit(
        db,
        user.id,
        "application.reviewed",
        application.id,
        {"outcome": result["outcome"], "attempt": attempt},
    )
    db.commit()
    db.refresh(application)
    return application_dict(db, application)


@router.get("/applications/{application_id}/decision")
def decision(
    application_id: str,
    user: User = Depends(entrepreneur),
    db: Session = Depends(get_db),
):
    application = owned_app(db, user.id, application_id)
    if not application.decision:
        return {"status": application.status, "decision": None}
    return {
        "status": application.status,
        "decision": application_dict(db, application)["decision"],
    }


@router.post("/applications/{application_id}/accept-offer")
def accept_offer(
    application_id: str,
    user: User = Depends(entrepreneur),
    db: Session = Depends(get_db),
):
    application = owned_app(db, user.id, application_id)
    if application.status != "APPROVED":
        raise HTTPException(409, "Принять можно только одобренное предложение")

    transition(
        db,
        application,
        "OFFER_ACCEPTED",
        "Условия демо-предложения приняты",
    )
    audit(db, user.id, "offer.accepted", application.id)
    db.commit()
    return application_dict(db, application)


@router.post("/applications/{application_id}/sign-demo")
def sign_demo(
    application_id: str,
    user: User = Depends(entrepreneur),
    db: Session = Depends(get_db),
):
    application = owned_app(db, user.id, application_id)
    if application.status != "OFFER_ACCEPTED":
        raise HTTPException(409, "Сначала примите условия предложения")

    transition(db, application, "SIGNED_DEMO", "Демо-договор подписан")
    transition(
        db,
        application,
        "DISBURSED_DEMO",
        "Демонстрационная выдача выполнена; реальные средства не перечислялись",
    )
    audit(db, user.id, "loan.signed_demo", application.id)
    db.commit()
    return application_dict(db, application)


@router.post("/assistant")
def assistant(
    body: AssistantIn,
    user: User = Depends(entrepreneur),
    db: Session = Depends(get_db),
):
    message = body.message.lower()
    text = (
        "Я помогу разобраться с кредитным предложением. Уточните сумму, срок и цель "
        "финансирования — я сопоставлю их с условиями продуктов."
    )

    if any(token in message for token in ("ставк", "процент", "платеж", "платёж")):
        text = (
            "Ставка и ориентировочный платёж рассчитываются по выбранному продукту "
            "и сроку. Итоговое решение принимает только детерминированный демо "
            "Rule Engine; я не назначаю ставку и не одобряю кредит."
        )
    elif any(
        token in message for token in ("документ", "справк", "выписк", "отчет", "отчёт")
    ):
        text = (
            "Для продуктов «Бизнес-рост» и «Оборотный» приложите финансовую "
            "отчётность (PDF, PNG или JPG до 1 МБ). Для овердрафта нужна выписка "
            "по счёту."
        )
    elif any(token in message for token in ("отказ", "решен", "одобрен")):
        text = (
            "Статус и причины решения доступны в карточке заявки. Проверки и "
            "скоринг демонстрационные и не обращаются к реальным ФНС или бюро "
            "кредитных историй."
        )
    elif any(token in message for token in ("продукт", "предложен", "каталог")):
        text = (
            "В каталоге есть три категории: развитие бизнеса, оборотные средства "
            "и овердрафт. Сравните допустимую сумму, срок, минимальную выручку и "
            "необходимый документ."
        )

    application_data = None
    if body.application_id:
        application = owned_app(db, user.id, body.application_id)
        application_data = {
            "id": application.id,
            "status": application.status,
            "need": {
                "purpose": application.purpose,
                "amount": application.amount,
                "term": application.term,
            },
            "decision": application_dict(db, application)["decision"],
        }

    return {
        "answer": text,
        "mode": "deterministic-fallback",
        "application": application_data,
    }
