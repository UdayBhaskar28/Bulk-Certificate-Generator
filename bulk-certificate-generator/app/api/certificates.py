from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CertificateItem, CertificateStatus
from app.schemas import (
    CertificateItemResponse,
    CertificateVerificationResponse
)

from app.config import settings
from app.services.generator import CertificateGenerator

router = APIRouter(prefix="/certificates", tags=["Certificates"])

def ensure_certificate_file_exists(cert: CertificateItem) -> Path:
    output_filename = f"cert_{cert.id}.pdf"
    file_path = Path(cert.file_path) if cert.file_path else (settings.STORAGE_DIR / output_filename)
    if not file_path.exists():
        try:
            import json
            custom_attrs = None
            if cert.custom_attributes:
                try:
                    custom_attrs = json.loads(cert.custom_attributes)
                except Exception:
                    custom_attrs = {"notes": cert.custom_attributes}
            
            job = cert.job
            title = job.title if job else "Certificate of Completion"
            issuer_name = job.issuer_name if job else "Issuing Authority"
            issue_date = job.issue_date if job else "Certificate Date"

            CertificateGenerator.generate_pdf(
                certificate_id=cert.id,
                recipient_name=cert.recipient_name,
                recipient_email=cert.recipient_email,
                title=title,
                issuer_name=issuer_name,
                issue_date=issue_date,
                output_path=file_path,
                custom_attributes=custom_attrs,
                verification_url=f"/api/v1/certificates/{cert.id}/verify"
            )
        except Exception:
            pass
    return file_path

@router.get("/{certificate_id}", response_model=CertificateItemResponse)
def get_certificate_details(certificate_id: str, db: Session = Depends(get_db)):
    """
    Get metadata for a specific certificate.
    """
    cert = db.query(CertificateItem).filter(CertificateItem.id == certificate_id).first()
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Certificate '{certificate_id}' not found."
        )

    return CertificateItemResponse(
        id=cert.id,
        job_id=cert.job_id,
        recipient_name=cert.recipient_name,
        recipient_email=cert.recipient_email,
        custom_attributes=cert.custom_attributes,
        status=cert.status,
        file_name=cert.file_name,
        file_size=cert.file_size,
        download_url=f"/api/v1/certificates/{cert.id}/download" if cert.status == CertificateStatus.COMPLETED else None,
        preview_url=f"/api/v1/certificates/{cert.id}/preview" if cert.status == CertificateStatus.COMPLETED else None,
        verification_url=f"/api/v1/certificates/{cert.id}/verify",
        error_message=cert.error_message,
        created_at=cert.created_at,
        generated_at=cert.generated_at
    )

@router.get("/{certificate_id}/download")
def download_certificate_pdf(certificate_id: str, db: Session = Depends(get_db)):
    """
    Download the generated certificate PDF as an attachment.
    """
    cert = db.query(CertificateItem).filter(CertificateItem.id == certificate_id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found.")

    if cert.status != CertificateStatus.COMPLETED:
        raise HTTPException(
            status_code=400, 
            detail=f"Certificate is not ready for download. Current status: {cert.status}"
        )

    file_path = ensure_certificate_file_exists(cert)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Certificate file not found on disk.")

    download_name = cert.file_name or f"Certificate_{cert.id}.pdf"
    return FileResponse(
        path=str(file_path),
        filename=download_name,
        media_type="application/pdf",
        content_disposition_type="attachment"
    )

@router.get("/{certificate_id}/preview")
def preview_certificate_pdf(certificate_id: str, db: Session = Depends(get_db)):
    """
    Stream the certificate PDF for inline browser viewing.
    """
    cert = db.query(CertificateItem).filter(CertificateItem.id == certificate_id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found.")

    if cert.status != CertificateStatus.COMPLETED:
        raise HTTPException(
            status_code=400, 
            detail=f"Certificate preview not available. Current status: {cert.status}"
        )

    file_path = ensure_certificate_file_exists(cert)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Certificate file not found on disk.")

    download_name = cert.file_name or f"Certificate_{cert.id}.pdf"
    return FileResponse(
        path=str(file_path),
        filename=download_name,
        media_type="application/pdf",
        content_disposition_type="inline"
    )

@router.get("/{certificate_id}/verify", response_model=CertificateVerificationResponse)
def verify_certificate(certificate_id: str, db: Session = Depends(get_db)):
    """
    Public verification endpoint to verify the authenticity of a certificate.
    """
    cert = db.query(CertificateItem).filter(CertificateItem.id == certificate_id).first()
    if not cert:
        return CertificateVerificationResponse(
            valid=False,
            certificate_id=certificate_id,
            verification_status="NOT_FOUND"
        )

    if cert.status != CertificateStatus.COMPLETED:
        return CertificateVerificationResponse(
            valid=False,
            certificate_id=certificate_id,
            recipient_name=cert.recipient_name,
            recipient_email=cert.recipient_email,
            verification_status=f"INVALID_STATUS_{cert.status}"
        )

    job = cert.job
    return CertificateVerificationResponse(
        valid=True,
        certificate_id=cert.id,
        recipient_name=cert.recipient_name,
        recipient_email=cert.recipient_email,
        title=job.title if job else None,
        issuer_name=job.issuer_name if job else None,
        issue_date=job.issue_date if job else None,
        issued_at=cert.generated_at,
        verification_status="VERIFIED_AUTHENTIC",
        download_url=f"/api/v1/certificates/{cert.id}/download"
    )
