import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple, Any

from app.config import settings
from app.database import SessionLocal
from app.models import GenerationJob, CertificateItem, JobStatus, CertificateStatus
from app.schemas import EMAIL_REGEX
from app.services.generator import CertificateGenerator

logger = logging.getLogger(__name__)

def validate_recipient_data(name: Any, email: Any) -> Tuple[bool, str]:
    """
    Validates recipient name and email format.
    Returns (is_valid, error_message).
    """
    if not isinstance(name, str) or not name.strip():
        return False, "Recipient name cannot be empty or non-string."
    
    if not isinstance(email, str) or not email.strip():
        return False, "Recipient email cannot be empty or non-string."
    
    clean_email = email.strip().lower()
    if not EMAIL_REGEX.match(clean_email):
        return False, f"Invalid email address format: '{email}'"
        
    return True, ""

def process_bulk_job(job_id: str):
    """
    Background worker task to process all certificates for a job.
    Provides strict failure isolation: an individual failure will
    never stop other certificates in the batch.
    """
    db = SessionLocal()
    try:
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found for processing.")
            return

        job.status = JobStatus.PROCESSING
        job.updated_at = datetime.now(timezone.utc)
        db.commit()

        items = db.query(CertificateItem).filter(
            CertificateItem.job_id == job_id,
            CertificateItem.status == CertificateStatus.PENDING
        ).all()

        for item in items:
            try:
                # 1. Validation check
                is_valid, validation_err = validate_recipient_data(item.recipient_name, item.recipient_email)
                if not is_valid:
                    item.status = CertificateStatus.FAILED
                    item.error_message = validation_err
                    job.failed_count += 1
                else:
                    item.status = CertificateStatus.GENERATING
                    db.commit()

                    # 2. Parse custom attributes if present
                    custom_attrs = None
                    if item.custom_attributes:
                        try:
                            custom_attrs = json.loads(item.custom_attributes)
                        except Exception:
                            custom_attrs = {"notes": item.custom_attributes}

                    # 3. Destination file path
                    output_filename = f"cert_{item.id}.pdf"
                    output_path = settings.STORAGE_DIR / output_filename
                    verification_url = f"/api/v1/certificates/{item.id}/verify"

                    # 4. Generate Certificate PDF
                    CertificateGenerator.generate_pdf(
                        certificate_id=item.id,
                        recipient_name=item.recipient_name,
                        recipient_email=item.recipient_email,
                        title=job.title,
                        issuer_name=job.issuer_name,
                        issue_date=job.issue_date,
                        output_path=output_path,
                        custom_attributes=custom_attrs,
                        verification_url=verification_url
                    )

                    # 5. Update item status to COMPLETED
                    safe_name = "".join(c for c in item.recipient_name if c.isalnum() or c in (" ", "_", "-")).strip()
                    item.file_path = str(output_path)
                    item.file_name = f"Certificate_{safe_name.replace(' ', '_')}_{item.id[:8]}.pdf"
                    item.file_size = output_path.stat().st_size if output_path.exists() else 0
                    item.status = CertificateStatus.COMPLETED
                    item.generated_at = datetime.now(timezone.utc)
                    job.success_count += 1

            except Exception as exc:
                logger.exception(f"Error generating certificate for item {item.id}: {exc}")
                item.status = CertificateStatus.FAILED
                item.error_message = f"Generation error: {str(exc)}"
                job.failed_count += 1

            # Update progress tracking
            job.processed_count += 1
            job.updated_at = datetime.now(timezone.utc)
            db.commit()

        # Job completion status evaluation
        job.completed_at = datetime.now(timezone.utc)
        job.updated_at = datetime.now(timezone.utc)

        if job.total_count == 0:
            job.status = JobStatus.COMPLETED
        elif job.success_count == job.total_count:
            job.status = JobStatus.COMPLETED
        elif job.success_count > 0 and job.failed_count > 0:
            job.status = JobStatus.PARTIALLY_COMPLETED
            job.error_summary = f"{job.failed_count} of {job.total_count} certificates failed generation."
        elif job.failed_count == job.total_count:
            job.status = JobStatus.FAILED
            job.error_summary = "All certificates in this job failed validation or generation."

        db.commit()

    except Exception as exc:
        logger.exception(f"Fatal error while processing job {job_id}: {exc}")
        if 'job' in locals() and job:
            job.status = JobStatus.FAILED
            job.error_summary = f"Job processing aborted: {str(exc)}"
            db.commit()
    finally:
        db.close()
