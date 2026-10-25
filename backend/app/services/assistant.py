import re

from sqlalchemy.orm import Session

from app.models.entities import CreditProduct
from app.services.catalog import product_dict
from app.services.credit_flow import age_months, monthly_payment

CATEGORY_TERMS = {
    "development": ("развит", "оборудован", "инвестиц", "расширен"),
    "turnover": ("оборот", "закуп", "сезон", "товар"),
    "overdraft": ("овердраф", "кассов", "разрыв", "резерв"),
}


def requested_amount_and_term(question: str) -> tuple[int | None, int | None]:
    query = question.casefold().replace("\u00a0", " ")
    amount = None
    money_pattern = r"(\d+(?:[.,]\d+)?)\s*(млн|миллион\w*|тыс\.?|тысяч\w*|руб\w*|₽)"
    money = re.search(r"(?:кредит|займ)\b.{0,80}?\bна\s*" + money_pattern, query)
    if not money:
        money = re.search(money_pattern, query)
    if money:
        number = float(money.group(1).replace(",", "."))
        unit = money.group(2)
        multiplier = (
            1_000_000
            if unit.startswith(("млн", "миллион"))
            else 1_000 if unit.startswith(("тыс", "тысяч")) else 1
        )
        amount = round(number * multiplier)
    else:
        plain = re.search(r"\b\d{6,9}\b", query)
        if plain:
            amount = int(plain.group())
    duration = re.search(r"\b(\d+)\s*(месяц\w*|мес\.?|год\w*|лет)\b", query)
    term = None
    if duration:
        count = int(duration.group(1))
        term = count * 12 if duration.group(2).startswith(("год", "лет")) else count
    return amount, term


def retrieve_products(db: Session, question: str, limit: int = 3) -> list[dict]:
    products = []
    for product in (
        db.query(CreditProduct)
        .filter_by(active=True)
        .order_by(CreditProduct.name)
        .all()
    ):
        item = product_dict(product)
        item["documentLabel"] = (
            "выписка по счёту"
            if item["document"] == "statement"
            else "финансовая отчётность"
        )
        products.append(item)
    query = question.casefold()
    query_words = re.findall(r"[a-zа-яё0-9]+", query)
    named = []
    for product in products:
        name_words = re.findall(r"[a-zа-яё0-9]+", product["name"].casefold())
        if all(
            any(
                (
                    query_word == name_word
                    if len(name_word) < 5
                    else query_word.startswith(name_word[:5])
                )
                for query_word in query_words
            )
            for name_word in name_words
        ):
            named.append((product, set(name_words)))
    if named:
        return [
            product
            for product, name_words in named
            if not any(name_words < other_words for _, other_words in named)
        ][:limit]

    amount, term = requested_amount_and_term(question)

    categories = [
        category
        for category, terms in CATEGORY_TERMS.items()
        if any(term in query for term in terms)
    ]
    if categories:
        products = [
            product for product in products if product["category"] in categories
        ]
    want_all = any(
        term in query for term in ("каталог", "продукт", "предложен", "вариант")
    )

    if amount is not None:
        products = [
            product
            for product in products
            if product["min"] <= amount <= product["max"]
        ]
    if term is not None:
        products = [
            product
            for product in products
            if product["minTerm"] <= term <= product["maxTerm"]
        ]
    if want_all and not categories:
        return products

    words = {word for word in query_words if len(word) >= 4}

    def score(product: dict) -> int:
        text = " ".join(
            str(product[field]).casefold()
            for field in ("name", "purpose", "category", "extras", "limit")
        )
        return sum(1 for word in words if word in text)

    if not categories and not any(score(product) for product in products):
        return products
    products.sort(key=lambda product: (-score(product), product["name"]))
    return products[:limit]


def fallback_answer(products: list[dict], application: dict | None) -> str:
    if application:
        return (
            f"Статус заявки: {application['status']}. "
            "Причины и условия решения смотрите в карточке заявки."
        )
    if not products:
        return "По указанной сумме и сроку подходящих предложений в демонстрационном каталоге нет."
    lines = []
    for product in products:
        document_label = product.get("documentLabel") or (
            "выписка по счёту" if product["document"] == "statement" else "финансовая отчётность"
        )
        lines.append(
            f"{product['name']}: ставка {product['rate']}%, нужен документ — {document_label}."
        )
    return "По данным демонстрационного каталога: " + " ".join(lines)


def product_fit_reasons(product: dict, need: dict, company: dict) -> list[str]:
    reasons = []
    if product["category"] != need["category"]:
        reasons.append("другая цель финансирования")
    if not product["min"] <= need["amount"] <= product["max"]:
        reasons.append("сумма вне диапазона")
    if not product["minTerm"] <= need["term"] <= product["maxTerm"]:
        reasons.append("срок вне диапазона")
    if age_months(company["registeredAt"]) < product["minAge"]:
        reasons.append("недостаточный срок работы бизнеса")
    if company["revenue"] < product["minRevenue"]:
        reasons.append("выручка ниже требования")
    return reasons


def verified_comparison(products: list[dict], need: dict, company: dict) -> str:
    if len(products) != 2:
        return fallback_answer(products, None)

    def money(value: int) -> str:
        return f"{value:,}".replace(",", " ")

    lines = [f"Сравнение для {money(need['amount'])} ₽ на {need['term']} мес.:"]
    eligible = []
    for product in products:
        reasons = product_fit_reasons(product, need, company)
        details = (
            f"{product['name']}: ставка {str(product['rate']).replace('.', ',')}%, "
            f"сумма {money(product['min'])}–{money(product['max'])} ₽, "
            f"срок {product['minTerm']}–{product['maxTerm']} мес.; {product['extras'].lower()}."
        )
        if reasons:
            details += " Сейчас не подходит: " + ", ".join(reasons) + "."
        else:
            details += " Подходит по указанным параметрам."
            eligible.append(product)
        lines.append(details)
    if len(eligible) == 2:
        cheaper = min(eligible, key=lambda item: item["rate"])
        larger = max(eligible, key=lambda item: item["max"])
        if cheaper["id"] == larger["id"]:
            lines.append(
                f"Если важны меньшая ставка и запас по сумме, выгоднее {cheaper['name']}: "
                f"{str(cheaper['rate']).replace('.', ',')}% и лимит до {money(cheaper['max'])} ₽. "
                "Проверьте его дополнительные условия; другой вариант может быть удобнее по обеспечению или графику."
            )
        else:
            lines.append(
                f"Если важна ставка, выгоднее {cheaper['name']}; "
                f"если нужна сумма больше, выбирайте {larger['name']} с лимитом до {money(larger['max'])} ₽."
            )
    elif eligible:
        lines.append(f"Из выбранных вариантов сейчас подходит {eligible[0]['name']}.")
    else:
        lines.append("Из выбранных вариантов сейчас ни один не подходит по указанным параметрам.")
    return "\n".join(lines)


DOCUMENT_NAMES = {
    "financial": "финансовая отчётность",
    "statement": "выписка по счёту",
}

STATUS_LABELS = {
    "DRAFT": "черновик",
    "SUBMITTED": "заявка отправлена",
    "CHECKING": "идёт проверка",
    "NEEDS_INFO": "нужно дополнить заявку",
    "SCORING": "идёт оценка заявки",
    "DECISION_PENDING": "ожидается решение банка",
    "APPROVED": "заявка одобрена",
    "REJECTED": "в заявке отказано",
    "OFFER_ACCEPTED": "предложение принято",
    "SIGNED_DEMO": "демонстрационный договор подписан",
    "DISBURSED_DEMO": "демонстрационная выдача завершена",
}


def humanize_status_codes(answer: str) -> str:
    for code, label in STATUS_LABELS.items():
        answer = re.sub(rf"\b{code}\b", label, answer)
    return answer

NEXT_ACTIONS = {
    "DRAFT": "Проверьте данные, приложите обязательный документ и отправьте заявку.",
    "NEEDS_INFO": "Посмотрите запрос сотрудника, дополните сведения и отправьте заявку повторно.",
    "DECISION_PENDING": "Ожидайте решения сотрудника банка; автоматические проверки завершены.",
    "APPROVED": "Проверьте условия предложения и при согласии примите их.",
    "REJECTED": "Посмотрите указанные причины отказа; можно подобрать другой продукт или исправить данные для новой заявки.",
    "OFFER_ACCEPTED": "Можно подписать демонстрационный договор.",
    "SIGNED_DEMO": "Демонстрационное подписание завершено.",
    "DISBURSED_DEMO": "Демонстрационная выдача завершена; реальные деньги не перечислялись.",
}


def advisor_context(company: dict | None, need: dict | None, product: dict | None,
                    application: dict | None) -> dict:
    facts: dict = {
        "need": need,
        "product": product,
        "application_status": application["status"] if application else None,
        "missing_documents": [],
        "missing_document_effect": None,
        "eligibility_reasons": [],
        "risk_factors": [],
        "observed_check_reasons": [],
        "decision_reasons": [],
        "next_action": NEXT_ACTIONS.get(application["status"]) if application else None,
    }
    if application and product:
        uploaded = {item["kind"] for item in application["documents"]}
        required = product["document"]
        if required not in uploaded:
            facts["missing_documents"].append(DOCUMENT_NAMES.get(required, required))
            facts["missing_document_effect"] = (
                "При отправке без обязательного документа демопроверка запрашивает дополнение "
                "заявки, а не отказывает. Документ можно приложить в черновике "
                "или после запроса на дополнение."
            )
        if application["checks"]:
            facts["observed_check_reasons"] = application["checks"][-1].get("reasons") or []
        if application["decision"]:
            facts["decision_reasons"] = application["decision"].get("reasons") or []
    if not company:
        return facts
    if company.get("overdue"):
        facts["risk_factors"].append("В данных компании указана просроченная задолженность.")
    if product and need and all(key in need for key in ("category", "amount", "term")):
        facts["eligibility_reasons"] = product_fit_reasons(product, need, company)
        if company["revenue"] < product["minRevenue"]:
            facts["risk_factors"].append("Выручка ниже минимального требования продукта.")
        disposable = company["revenue"] - company["expenses"] - company["obligations"]
        payment = monthly_payment(need["amount"], product["rate"], need["term"])
        facts["monthly_disposable_cash_flow"] = round(disposable, 2)
        facts["estimated_monthly_payment"] = round(payment, 2)
        if disposable < payment * 1.25:
            facts["risk_factors"].append(
                "Свободного денежного потока недостаточно для платежа с запасом 1,25× по демонстрационным правилам."
            )
    return facts


def advisor_fallback(facts: dict, products: list[dict], application: dict | None) -> str:
    parts = []
    if application:
        parts.append(f"Статус заявки: {STATUS_LABELS.get(application['status'], application['status'])}.")
    if facts["missing_documents"]:
        parts.append("Не хватает документа: " + ", ".join(facts["missing_documents"]) + ".")
        if not facts["decision_reasons"]:
            parts.append("Без него попросят дополнить заявку; это не отказ.")
    if facts["decision_reasons"]:
        parts.append("Причины решения: " + "; ".join(facts["decision_reasons"]) + ".")
    elif facts["observed_check_reasons"]:
        parts.append("По демопроверке отмечено: " + "; ".join(facts["observed_check_reasons"]) + ".")
    elif facts["risk_factors"]:
        parts.append("Возможные факторы риска: " + " ".join(facts["risk_factors"]))
    if facts["next_action"]:
        parts.append(facts["next_action"])
    return " ".join(parts) if parts else fallback_answer(products, application)


def advisor_answer_is_grounded(answer: str, facts: dict) -> bool:
    normalized = answer.casefold()
    if facts["missing_documents"] and not facts["decision_reasons"]:
        for sentence in re.split(r"[.!?]", normalized):
            without_negated_refusal = re.sub(r"\bне\s+(?:отказ\w*|отклон\w*|откаж\w*)", "", sentence)
            if (re.search(r"отклон|отказ|откаж", without_negated_refusal)
                    and re.search(r"отсутств|не хватает|недоста|документ|отчётност|отчетност", sentence)):
                return False
    return True


def comparison_answer_is_grounded(answer: str, products: list[dict],
                                  need: dict | None = None, company: dict | None = None) -> bool:
    normalized = answer.casefold().replace("\u00a0", " ")
    if len(products) != 2 or any(product["name"].casefold() not in normalized for product in products):
        return False
    for product in products:
        rate = str(product["rate"])
        if rate not in normalized and rate.replace(".", ",") not in normalized:
            return False
    highest_limit = max(product["max"] for product in products)
    maximum = f"{highest_limit:,}".replace(",", " ")
    short_maximum = f"{highest_limit / 1_000_000:g}".replace(".", ",")
    if maximum not in normalized and not re.search(rf"(?<!\d){re.escape(short_maximum)}\s*млн\b", normalized):
        return False
    if "требует залога" in normalized and not any(
        "залог" in product["extras"].casefold() and "без залога" not in product["extras"].casefold()
        for product in products
    ):
        return False
    if any(re.search(rf"\b{product['minAge']}\s*(?:год|года|лет)\b", normalized)
           for product in products):
        return False
    if need and company and all(not product_fit_reasons(product, need, company) for product in products):
        if re.search(r"не подходит|не соответствует|подойд[её]т только|подходит только|только\s+(?:продукт\s+)?[^,.]{0,60}\s+подход", normalized):
            return False
    return True


def product_alternatives(db: Session, primary: list[dict], need: dict | None,
                         selected_ids: list[str] | None = None, company: dict | None = None,
                         limit: int = 3) -> list[dict]:
    primary_ids = {item["id"] for item in primary}
    if not primary or not company or not need or not all(key in need for key in ("category", "amount", "term")):
        return []
    reference = primary[0]
    selected_ids = selected_ids or []
    candidates = [product_dict(item) for item in db.query(CreditProduct).filter_by(active=True).all()
                  if item.id not in primary_ids]

    def rank(item):
        return (item["id"] not in selected_ids,
                item["category"] != reference["category"],
                abs(item["rate"] - reference["rate"]), item["name"])

    result = []
    for item in sorted(candidates, key=rank):
        if product_fit_reasons(item, need, company):
            continue
        pros = [f"Ставка {item['rate']}%", f"Лимит до {item['max']:,} ₽".replace(',', ' ')]
        if item["rate"] < reference["rate"]:
            pros.insert(0, "Ставка ниже основного варианта")
        cons = [f"Требуется документ: {'выписка по счёту' if item['document'] == 'statement' else 'финансовая отчётность'}"]
        if "поручительство" in item["extras"].casefold():
            cons.append("Требуется поручительство")
        result.append({"product": item, "fits": True, "pros": pros, "cons": cons})
        if len(result) >= limit:
            break
    return result
