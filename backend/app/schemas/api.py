from typing import Literal

from pydantic import BaseModel, Field, field_validator


class LoginIn(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=200)


class CompanyIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    inn: str
    legal_form: str
    registered_at: str
    industry: str
    revenue: float = Field(ge=0)
    expenses: float = Field(ge=0)
    obligations: float = Field(ge=0)
    overdue: bool = False

    @field_validator("inn")
    @classmethod
    def valid_inn(cls, value):
        if not (value.isdigit() and len(value) in (10, 12)):
            raise ValueError("ИНН должен содержать 10 или 12 цифр")
        return value


class NeedIn(BaseModel):
    purpose: str = Field(min_length=2, max_length=1000)
    category: Literal["development", "turnover", "overdraft"]
    amount: int = Field(gt=0)
    term: int = Field(gt=0)


class ApplicationCreate(BaseModel):
    product_id: str
    need: NeedIn


class ApplicationPatch(BaseModel):
    company: dict | None = None
    need: dict | None = None


class AssistantIn(BaseModel):
    message: str = Field(min_length=1, max_length=3000)
    application_id: str | None = None
    page_context: "AssistantPageContext | None" = None
    history: list["AssistantHistoryMessage"] = Field(default_factory=list, max_length=8)


class AssistantHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(min_length=1, max_length=3000)


class AssistantPageContext(BaseModel):
    page: str = Field(default="home", max_length=40)
    selected_product_ids: list[str] = Field(default_factory=list, max_length=3)
    need: NeedIn | None = None


class DecisionAccept(BaseModel):
    accepted: bool = True


class BankDecisionIn(BaseModel):
    action: Literal["approve", "reject", "request_info"]
    comment: str = Field(default="", max_length=1000)
