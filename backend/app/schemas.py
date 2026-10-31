from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str


class FindingAction(BaseModel):
    action: str
    comment: str = Field(min_length=3, max_length=2000)


class SingleEnrolment(BaseModel):
    name: str
    dob: str
    apaar_id: str = ""
    apaar_status: str = ""
    programme: str
    seat_category: str = "regular"
    admission_date: str
    admission_mode: str = "counselling"
    gender: str = "U"
    phone: str = ""
    email: str = ""
    nationality: str = "India"
    qualifying_exam_pct: str = ""


class IssueCredentialRequest(BaseModel):
    enrolment_id: int


class RevokeCredentialRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=240)


class ConsentCreateRequest(BaseModel):
    enrolment_ref: str
    fields: list[str]
    purpose: str


class ConsentDecision(BaseModel):
    approve: bool


class CopilotQuery(BaseModel):
    question: str = Field(min_length=2, max_length=500)
