import uuid
from pathlib import Path
from app.services.generator import CertificateGenerator

def test_certificate_generator_creates_valid_pdf(tmp_path):
    cert_id = str(uuid.uuid4())
    output_file = tmp_path / f"cert_{cert_id}.pdf"
    
    result = CertificateGenerator.generate_pdf(
        certificate_id=cert_id,
        recipient_name="Ada Lovelace",
        recipient_email="ada.lovelace@example.com",
        title="Foundations of Computer Programming",
        issuer_name="Royal Society of Computing",
        issue_date="October 10, 2026",
        output_path=output_file
    )
    
    assert result.exists()
    assert result.is_file()
    assert result.stat().st_size > 1000
    
    # Check PDF magic bytes
    with open(result, "rb") as f:
        header = f.read(5)
        assert header == b"%PDF-"

def test_certificate_generator_with_custom_attributes(tmp_path):
    cert_id = str(uuid.uuid4())
    output_file = tmp_path / f"cert_{cert_id}.pdf"
    custom_attrs = {
        "grade": "Distinction",
        "honors": "Summa Cum Laude",
        "duration_hours": 60
    }
    
    result = CertificateGenerator.generate_pdf(
        certificate_id=cert_id,
        recipient_name="Alan Turing",
        recipient_email="alan.turing@example.com",
        title="Theory of Computation & Cryptanalysis",
        issuer_name="Bletchley Institute",
        issue_date="October 10, 2026",
        output_path=output_file,
        custom_attributes=custom_attrs,
        verification_url="https://certify.example.com/verify/test-id"
    )
    
    assert result.exists()
    assert result.stat().st_size > 1500
    with open(result, "rb") as f:
        assert f.read(5) == b"%PDF-"
