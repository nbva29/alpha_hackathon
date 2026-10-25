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
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    current_session,
    employee,
    entrepreneur,
    new_session,
    verify_password,
)
from app.db.session import get_db
from app.integrations.bank_client import review
from app.integrations.llm_client import complete
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
    BankDecisionIn,
    CompanyIn,
    LoginIn,
)
from app.services.catalog import product_dict
from app.services.credit_flow import (
    age_months,
    application_dict,
    audit,
    monthly_payment,
    transition,
)
from app.services.assistant import advisor_answer_is_grounded, advisor_context, advisor_fallback, comparison_answer_is_grounded, humanize_status_codes, product_alternatives, product_fit_reasons, retrieve_products, requested_amount_and_term, verified_comparison

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
            "Скоринг завершён; ожидается решение сотрудника банка",
        )

        # Сотрудник видит рекомендацию симулятора и принимает демо-решение отдельно.

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


@router.get("/bank/applications")
def bank_applications(user: User = Depends(employee), db: Session = Depends(get_db)):
    applications = (
        db.query(LoanApplication)
        .filter(LoanApplication.status != "DRAFT")
        .order_by(LoanApplication.updated_at.desc())
        .all()
    )
    owners = {owner.id: owner for owner in db.query(User).all()}
    return [
        {
            "ownerId": application.owner_id,
            "borrowerName": owners[application.owner_id].name,
            "application": application_dict(db, application),
        }
        for application in applications
    ]


@router.get("/bank/applications/{application_id}/documents/{document_id}")
def bank_document(
    application_id: str,
    document_id: str,
    user: User = Depends(employee),
    db: Session = Depends(get_db),
):
    document = (
        db.query(ApplicationDocument)
        .filter_by(id=document_id, application_id=application_id)
        .first()
    )
    if not document or not Path(document.storage_path).is_file():
        raise HTTPException(404, "Документ не найден")
    return FileResponse(
        document.storage_path,
        media_type=document.mime,
        filename=document.name,
        content_disposition_type="attachment",
    )


@router.post("/bank/applications/{application_id}/decision")
def bank_decision(
    application_id: str,
    body: BankDecisionIn,
    user: User = Depends(employee),
    db: Session = Depends(get_db),
):
    application = db.get(LoanApplication, application_id)
    if not application:
        raise HTTPException(404, "Заявка не найдена")
    if application.status != "DECISION_PENDING":
        raise HTTPException(409, "Заявка пока не ожидает решения")
    comment = body.comment.strip()
    if body.action in ("reject", "request_info") and not comment:
        raise HTTPException(422, "Укажите причину для клиента")

    check = max(application.checks, key=lambda item: item.attempt, default=None)
    if body.action == "approve" and (not check or (check.score or 0) < 50):
        raise HTTPException(409, "Одобрение не соответствует результату демопроверки")

    if body.action == "request_info":
        transition(db, application, "NEEDS_INFO", comment)
    else:
        approved = body.action == "approve"
        product = db.get(CreditProduct, application.product_id)
        reasons = [] if approved else [comment]
        db.add(
            CreditDecision(
                application_id=application.id,
                outcome="APPROVED" if approved else "REJECTED",
                approved=approved,
                reasons=reasons,
                rate=product.rate,
                monthly_payment=round(
                    monthly_payment(application.amount, product.rate, application.term),
                    2,
                ),
                note=comment or "Одобрено сотрудником банка в демонстрационном режиме",
                rule_version="employee-demo-1.0",
            )
        )
        transition(
            db,
            application,
            "APPROVED" if approved else "REJECTED",
            "Демо-решение сотрудника: " + ("одобрено" if approved else comment),
        )
    audit(
        db,
        user.id,
        "bank.decision",
        application.id,
        {"action": body.action, "comment": comment},
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
    application_data = None
    if body.application_id:
        application = owned_app(db, user.id, body.application_id)
        application_data = application_dict(db, application)

    products = retrieve_products(db, body.message)
    page = body.page_context
    selected_products = []
    if page:
        for product_id in page.selected_product_ids:
            product = db.get(CreditProduct, product_id)
            if product and product.active:
                selected_products.append(product_dict(product))
    requested_amount, requested_term = requested_amount_and_term(body.message)
    need = application_data["need"] if application_data else page.need.model_dump() if page and page.need else None
    if requested_amount or requested_term:
        need = {**(need or {}), **({"amount": requested_amount} if requested_amount else {}),
                **({"term": requested_term} if requested_term else {})}
    product_question = any(term in body.message.casefold() for term in
                           ("кредит", "продукт", "вариант", "аналог", "сравн", "подход", "документ", "ставк", "услови"))
    recommendation_question = any(term in body.message.casefold() for term in
                                  ("подход", "рекоменду", "выбрать", "подобра"))
    if need and recommendation_question and not requested_amount and not requested_term and page and page.page in {"need", "catalog"}:
        products = [item for item in products if item["min"] <= need["amount"] <= item["max"]
                    and item["minTerm"] <= need["term"] <= item["maxTerm"]]
    comparison_context = bool(page and page.page == "catalog" and len(selected_products) >= 2)
    if selected_products and (comparison_context or any(term in body.message.casefold() for term in ("сравн", "выбран", "между"))):
        products = selected_products
    if application_data and application_data["product"]:
        application_product = application_data["product"]
        asks_for_other_products = any(term in body.message.casefold() for term in
                                      ("другие", "альтернатив", "аналог", "сравн", "вариант", "кредитов", "продуктов"))
        products = ([application_product] + [item for item in products if item["id"] != application_product["id"]][:2]
                    if asks_for_other_products else [application_product])
    company = company_dict(db.query(Company).filter_by(owner_id=user.id).first())
    alternatives = product_alternatives(db, products, need, page.selected_product_ids if page else None,
                                        company) if product_question or comparison_context else []
    selected_with_fit = []
    for item in selected_products:
        if need and company and all(key in need for key in ("category", "amount", "term")):
            reasons = product_fit_reasons(item, need, company)
            selected_with_fit.append({**item, "fit_reasons": reasons, "fits": not reasons})
        else:
            selected_with_fit.append(item)
    current_product = (
        application_data["product"] if application_data else
        selected_products[0] if selected_products else
        products[0] if products else None
    )
    advisor_facts = advisor_context(
        application_data["company"] if application_data else company,
        need, current_product, application_data,
    )
    applications = db.query(LoanApplication).filter_by(owner_id=user.id).order_by(LoanApplication.updated_at.desc()).limit(10).all()
    context = {
        "company": company,
        "applications": [{"id": item.id, "status": item.status, "productId": item.product_id,
                          "need": {"purpose": item.purpose, "category": item.category,
                                   "amount": item.amount, "term": item.term},
                          "documents": [{"name": doc.name, "kind": doc.kind, "addedAt": doc.created_at.isoformat()}
                                        for doc in item.documents]} for item in applications],
        "page_context": {"page": page.page if page else "unknown", "selected_products": selected_with_fit,
                         "need": need},
        "alternatives": alternatives,
        "advisor_context": advisor_facts,
        "conversation": [item.model_dump() for item in body.history],
        "comparison_facts": selected_with_fit if comparison_context else [],
    }
    verified_answer = (
        verified_comparison(products, need, company)
        if comparison_context and need and company and all(key in need for key in ("category", "amount", "term"))
        else None
    )
    if comparison_context:
        context["applications"] = []
        context["alternatives"] = []
        context["advisor_context"] = {"need": need}
        context["verified_comparison"] = verified_answer
    names = [
        name for (name,) in db.query(CreditProduct.name).filter_by(active=True).all()
    ]
    answer = complete(body.message, products, application_data, names, context)
    if answer and not advisor_answer_is_grounded(answer, advisor_facts):
        answer = None
    if verified_answer and answer and not comparison_answer_is_grounded(answer, products, need, company):
        answer = None
    fallback_products = (
        [item for item in products if not product_fit_reasons(item, need, company)]
        if comparison_context and need and company and all(key in need for key in ("category", "amount", "term"))
        else products
    )
    return {
        "answer": humanize_status_codes(answer or verified_answer or advisor_fallback(advisor_facts, fallback_products, application_data)),
        "mode": "local-llm" if answer else "verified-comparison" if verified_answer else "deterministic-fallback",
        "sources": [
            {
                "id": product["id"],
                "version": product["version"],
                "name": product["name"],
                "category": product["category"],
            }
            for product in products
        ],
        "application": application_data,
        "alternatives": alternatives,
    }
