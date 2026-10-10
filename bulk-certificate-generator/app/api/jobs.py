import csv
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, UploadFile, File, Form, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import GenerationJob, CertificateItem, JobStatus, CertificateStatus
from app.schemas import (
    JobCreateRequest,
    GenerationJobResponse,
    JobSummaryResponse,
    CertificateItemResponse
)
from app.config import settings
from app.services.job_processor import process_bulk_job
from app.services.generator import CertificateGenerator

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def compute_progress_percentage(total: int, processed: int) -> float:
    if total <= 0:
        return 100.0
    return round((processed / total) * 100.0, 1)

def format_job_response(job: GenerationJob, include_certificates: bool = True) -> GenerationJobResponse:
    cert_items = []
    if include_certificates and job.certificates:
        for c in job.certificates:
            cert_items.append(CertificateItemResponse(
                id=c.id,
                job_id=c.job_id,
                recipient_name=c.recipient_name,
                recipient_email=c.recipient_email,
                custom_attributes=c.custom_attributes,
                status=c.status,
                file_name=c.file_name,
                file_size=c.file_size,
                download_url=f"/api/v1/certificates/{c.id}/download" if c.status == CertificateStatus.COMPLETED else None,
                preview_url=f"/api/v1/certificates/{c.id}/preview" if c.status == CertificateStatus.COMPLETED else None,
                verification_url=f"/api/v1/certificates/{c.id}/verify",
                error_message=c.error_message,
                created_at=c.created_at,
                generated_at=c.generated_at
            ))

    return GenerationJobResponse(
        id=job.id,
        title=job.title,
        issuer_name=job.issuer_name,
        issue_date=job.issue_date,
        description=job.description,
        status=job.status,
        total_count=job.total_count,
        processed_count=job.processed_count,
        success_count=job.success_count,
        failed_count=job.failed_count,
        progress_percentage=compute_progress_percentage(job.total_count, job.processed_count),
        error_summary=job.error_summary,
        created_at=job.created_at,
        updated_at=job.updated_at,
        completed_at=job.completed_at,
        download_all_url=f"/api/v1/jobs/{job.id}/download-all" if job.success_count > 0 else None,
        certificates=cert_items if include_certificates else None
    )

@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=GenerationJobResponse)
def create_generation_job(
    payload: JobCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Accepts a certificate generation request with a batch of recipients.
    Enqueues the generation process asynchronously and returns 202 Accepted.
    """
    if not payload.recipients:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
            detail="The recipients list must not be empty."
        )

    issue_date = payload.issue_date or datetime.now(timezone.utc).strftime("%B %d, %Y")

    # Create Job record
    job = GenerationJob(
        title=payload.title,
        issuer_name=payload.issuer_name,
        issue_date=issue_date,
        description=payload.description,
        status=JobStatus.PENDING,
        total_count=len(payload.recipients),
        processed_count=0,
        success_count=0,
        failed_count=0
    )
    db.add(job)
    db.flush()

    # Create CertificateItem records
    for recipient in payload.recipients:
        # Extract fields safely even if dictionary keys vary
        raw_name = recipient.get("name", "") if isinstance(recipient, dict) else ""
        raw_email = recipient.get("email", "") if isinstance(recipient, dict) else ""
        
        # Any additional fields stored as custom attributes
        custom_dict = {}
        if isinstance(recipient, dict):
            for k, v in recipient.items():
                if k not in ("name", "email"):
                    custom_dict[k] = v
        if "custom_attributes" in recipient and isinstance(recipient["custom_attributes"], dict):
            custom_dict.update(recipient["custom_attributes"])

        custom_json = json.dumps(custom_dict) if custom_dict else None

        cert_item = CertificateItem(
            job_id=job.id,
            recipient_name=str(raw_name).strip() if raw_name else "",
            recipient_email=str(raw_email).strip().lower() if raw_email else "",
            custom_attributes=custom_json,
            status=CertificateStatus.PENDING
        )
        db.add(cert_item)

    db.commit()
    db.refresh(job)

    # Trigger processing:
    # On serverless platforms (e.g. Vercel), background worker tasks are frozen once the response finishes.
    # Therefore, process synchronously in serverless mode to ensure certificates are completely generated.
    if settings.IS_SERVERLESS:
        process_bulk_job(job.id)
        db.refresh(job)
    else:
        background_tasks.add_task(process_bulk_job, job.id)

    return format_job_response(job, include_certificates=True)

@router.post("/csv", status_code=status.HTTP_202_ACCEPTED, response_model=GenerationJobResponse)
async def create_job_from_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="CSV file with name, email and optional attribute columns"),
    title: str = Form(..., description="Course or Event Title"),
    issuer_name: str = Form(..., description="Issuing organization or instructor"),
    issue_date: Optional[str] = Form(None, description="Certificate issuance date"),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Optional helper endpoint to upload a recipient CSV file directly.
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a CSV file.")

    content = await file.read()
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        decoded = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(decoded))
    recipients = []
    for row in reader:
        # Normalize key names to lowercase
        normalized = {k.strip().lower(): v.strip() for k, v in row.items() if k}
        name = normalized.get("name") or normalized.get("recipient_name") or normalized.get("full_name") or ""
        email = normalized.get("email") or normalized.get("recipient_email") or ""
        
        # extra attributes
        extras = {k: v for k, v in normalized.items() if k not in ("name", "recipient_name", "full_name", "email", "recipient_email")}
        
        recipients.append({
            "name": name,
            "email": email,
            "custom_attributes": extras
        })

    if not recipients:
        raise HTTPException(status_code=400, detail="CSV file contains no valid rows.")

    request_payload = JobCreateRequest(
        title=title,
        issuer_name=issuer_name,
        issue_date=issue_date,
        description=description,
        recipients=recipients
    )
    return create_generation_job(request_payload, background_tasks, db)

@router.get("", response_model=List[JobSummaryResponse])
def list_jobs(
    status_filter: Optional[JobStatus] = Query(None, alias="status", description="Filter by job status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    List all generation jobs with optional status filter and pagination.
    """
    query = db.query(GenerationJob)
    if status_filter:
        query = query.filter(GenerationJob.status == status_filter)
    
    jobs = query.order_by(GenerationJob.created_at.desc()).offset(offset).limit(limit).all()
    
    return [
        JobSummaryResponse(
            id=j.id,
            title=j.title,
            issuer_name=j.issuer_name,
            issue_date=j.issue_date,
            status=j.status,
            total_count=j.total_count,
            processed_count=j.processed_count,
            success_count=j.success_count,
            failed_count=j.failed_count,
            progress_percentage=compute_progress_percentage(j.total_count, j.processed_count),
            created_at=j.created_at,
            completed_at=j.completed_at
        )
        for j in jobs
    ]

@router.get("/{job_id}", response_model=GenerationJobResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """
    Check the progress and results of a certificate generation job.
    """
    job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    
    return format_job_response(job, include_certificates=True)

@router.get("/{job_id}/items", response_model=List[CertificateItemResponse])
def get_job_items(
    job_id: str,
    status_filter: Optional[CertificateStatus] = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Get recipient certificate items for a job, optionally filtered by status.
    """
    job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    query = db.query(CertificateItem).filter(CertificateItem.job_id == job_id)
    if status_filter:
        query = query.filter(CertificateItem.status == status_filter)

    items = query.order_by(CertificateItem.created_at.asc()).offset(offset).limit(limit).all()

    return [
        CertificateItemResponse(
            id=c.id,
            job_id=c.job_id,
            recipient_name=c.recipient_name,
            recipient_email=c.recipient_email,
            custom_attributes=c.custom_attributes,
            status=c.status,
            file_name=c.file_name,
            file_size=c.file_size,
            download_url=f"/api/v1/certificates/{c.id}/download" if c.status == CertificateStatus.COMPLETED else None,
            preview_url=f"/api/v1/certificates/{c.id}/preview" if c.status == CertificateStatus.COMPLETED else None,
            verification_url=f"/api/v1/certificates/{c.id}/verify",
            error_message=c.error_message,
            created_at=c.created_at,
            generated_at=c.generated_at
        )
        for c in items
    ]

@router.get("/{job_id}/download-all")
def download_all_certificates_zip(job_id: str, db: Session = Depends(get_db)):
    """
    Retrieves and bundles all successfully generated certificates
    for this job into a single downloadable ZIP archive.
    """
    job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    completed_items = db.query(CertificateItem).filter(
        CertificateItem.job_id == job_id,
        CertificateItem.status == CertificateStatus.COMPLETED
    ).all()

    if not completed_items:
        raise HTTPException(
            status_code=400, 
            detail="No completed certificates are available to download for this job yet."
        )

    # Create zip archive in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for item in completed_items:
            output_filename = f"cert_{item.id}.pdf"
            p = Path(item.file_path) if item.file_path else (settings.STORAGE_DIR / output_filename)
            if not p.exists():
                try:
                    custom_attrs = None
                    if item.custom_attributes:
                        try:
                            custom_attrs = json.loads(item.custom_attributes)
                        except Exception:
                            custom_attrs = {"notes": item.custom_attributes}
                    CertificateGenerator.generate_pdf(
                        certificate_id=item.id,
                        recipient_name=item.recipient_name,
                        recipient_email=item.recipient_email,
                        title=job.title,
                        issuer_name=job.issuer_name,
                        issue_date=job.issue_date,
                        output_path=p,
                        custom_attributes=custom_attrs,
                        verification_url=f"/api/v1/certificates/{item.id}/verify"
                    )
                except Exception:
                    pass
            if p.exists():
                archive_name = item.file_name or f"Certificate_{item.id}.pdf"
                zf.write(p, arcname=archive_name)

    zip_buffer.seek(0)
    safe_title = "".join(c for c in job.title if c.isalnum() or c in ("-", "_")).strip() or "certificates"
    filename = f"{safe_title}_{job_id[:8]}.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
