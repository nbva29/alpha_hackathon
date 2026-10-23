from app.services.credit_flow import age_months, monthly_payment


def test_monthly_payment_positive():
    assert monthly_payment(1_200_000, 16.9, 24) > 0


def test_zero_rate_payment():
    assert monthly_payment(1200, 0, 12) == 100


def test_invalid_registration_date_is_safe():
    assert age_months("not-a-date") == 0
