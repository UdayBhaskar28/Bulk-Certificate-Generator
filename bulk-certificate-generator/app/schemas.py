import re
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
from app.models import JobStatus, CertificateStatus

EMAIL_REGEX = re.compile(r"^[\w\.-]+@([\w-]+\.)+[\w-]{2,}$")

class RecipientInput(BaseModel):
    name: str = Field(..., description="Recipient full name", min_length=1)
    email: str = Field(..., description="Recipient email address")
    custom_attributes: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Optional recipient metadata (e.g., {'grade': 'A', 'hours': 40})"
    )

    @field_validator("name")
    def clean_name(cls, v: str) -> str:
        cleaned = v.strip() if isinstance(v, str) else ""
        if not cleaned:
            raise ValueError("Recipient name cannot be empty or whitespace.")
        return cleaned

    @field_validator("email")
    def clean_email(cls, v: str) -> str:
        cleaned = v.strip().lower() if isinstance(v, str) else ""
        if not cleaned or not EMAIL_REGEX.match(cleaned):
            raise ValueError(f"Invalid email address: '{v}'")
        return cleaned

class JobCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Course or Event Title")
    issuer_name: str = Field(..., min_length=1, max_length=255, description="Issuing organization or instructor")
    issue_date: Optional[str] = Field(default=None, description="Certificate issuance date (default: today)")
    description: Optional[str] = Field(default=None, description="Optional job/event description")
    recipients: List[Dict[str, Any]] = Field(
        ..., 
        min_length=1, 
        description="List of recipient objects. Valid entries will be generated, invalid entries flagged as failed without aborting the batch."
    )

    @field_validator("title")
    def clean_title(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Job title cannot be empty.")
        return cleaned

    @field_validator("issuer_name")
    def clean_issuer(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Issuer name cannot be empty.")
        return cleaned

class CertificateItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    recipient_name: str
    recipient_email: str
    title: Optional[str] = None
    issuer_name: Optional[str] = None
    custom_attributes: Optional[str] = None
    status: CertificateStatus
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    download_url: Optional[str] = None
    preview_url: Optional[str] = None
    verification_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    generated_at: Optional[datetime] = None

class GenerationJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    issuer_name: str
    issue_date: str
    description: Optional[str] = None
    status: JobStatus
    total_count: int
    processed_count: int
    success_count: int
    failed_count: int
    progress_percentage: float
    error_summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    download_all_url: Optional[str] = None
    certificates: Optional[List[CertificateItemResponse]] = None

class JobSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    issuer_name: str
    issue_date: str
    status: JobStatus
    total_count: int
    processed_count: int
    success_count: int
    failed_count: int
    progress_percentage: float
    created_at: datetime
    completed_at: Optional[datetime] = None

class CertificateVerificationResponse(BaseModel):
    valid: bool
    certificate_id: str
    recipient_name: Optional[str] = None
    recipient_email: Optional[str] = None
    title: Optional[str] = None
    issuer_name: Optional[str] = None
    issue_date: Optional[str] = None
    issued_at: Optional[datetime] = None
    verification_status: str
    download_url: Optional[str] = None
