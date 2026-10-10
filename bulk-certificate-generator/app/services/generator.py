import io
from pathlib import Path
from typing import Optional, Dict, Any
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import qrcode

class CertificateGenerator:
    """
    Renders high-quality, professional vector PDF certificates
    using a predefined certificate template.
    """

    @staticmethod
    def generate_pdf(
        certificate_id: str,
        recipient_name: str,
        recipient_email: str,
        title: str,
        issuer_name: str,
        issue_date: str,
        output_path: Path,
        custom_attributes: Optional[Dict[str, Any]] = None,
        verification_url: Optional[str] = None
    ) -> Path:
        """
        Generates a certificate PDF file and saves it to output_path.
        Returns the output path.
        """
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Dimensions for Landscape A4
        width, height = landscape(A4)  # ~841.89 x 595.27 points
        
        c = canvas.Canvas(str(output_path), pagesize=landscape(A4))
        c.setTitle(f"Certificate - {recipient_name}")
        c.setAuthor(issuer_name)
        c.setSubject(title)

        # 1. Background Fill (clean subtle ivory tint)
        c.setFillColor(colors.HexColor("#fafbfe"))
        c.rect(0, 0, width, height, fill=True, stroke=False)

        # 2. Outer Ornamental Borders
        # Deep Blue / Navy primary border
        c.setStrokeColor(colors.HexColor("#0f172a"))
        c.setLineWidth(4)
        c.rect(20, 20, width - 40, height - 40)

        # Gold inner accent border
        c.setStrokeColor(colors.HexColor("#d97706"))
        c.setLineWidth(1.5)
        c.rect(28, 28, width - 56, height - 56)

        # Corner corner ornaments (triangles / diamonds)
        corner_size = 14
        corners = [
            (28, 28),
            (width - 28 - corner_size, 28),
            (28, height - 28 - corner_size),
            (width - 28 - corner_size, height - 28 - corner_size)
        ]
        c.setFillColor(colors.HexColor("#d97706"))
        for cx, cy in corners:
            c.rect(cx, cy, corner_size, corner_size, fill=True, stroke=False)

        # 3. Header: Issuing Organization
        c.setFont("Helvetica-Bold", 13)
        c.setFillColor(colors.HexColor("#475569"))
        c.drawCentredString(width / 2, height - 75, issuer_name.upper())

        # Gold decorative horizontal bar under issuer
        c.setStrokeColor(colors.HexColor("#d97706"))
        c.setLineWidth(1)
        c.line(width / 2 - 80, height - 85, width / 2 + 80, height - 85)

        # 4. Main Certificate Heading
        c.setFont("Helvetica-Bold", 32)
        c.setFillColor(colors.HexColor("#0f172a"))
        c.drawCentredString(width / 2, height - 130, "CERTIFICATE OF ACHIEVEMENT")

        # 5. Subtitle
        c.setFont("Helvetica", 12)
        c.setFillColor(colors.HexColor("#64748b"))
        c.drawCentredString(width / 2, height - 165, "THIS IS PROUDLY PRESENTED TO")

        # 6. Recipient Name (Prominent & distinguished)
        c.setFont("Helvetica-Bold", 30)
        c.setFillColor(colors.HexColor("#1e3a8a"))
        c.drawCentredString(width / 2, height - 215, recipient_name)

        # Gold accent line under recipient name
        c.setStrokeColor(colors.HexColor("#f59e0b"))
        c.setLineWidth(2)
        c.line(width / 2 - 150, height - 228, width / 2 + 150, height - 228)

        # 7. Presentation text
        c.setFont("Helvetica", 13)
        c.setFillColor(colors.HexColor("#334155"))
        c.drawCentredString(
            width / 2, 
            height - 265, 
            "for successfully completing all requirements and demonstrating outstanding proficiency in"
        )

        # 8. Course / Event Title
        c.setFont("Helvetica-Bold", 20)
        c.setFillColor(colors.HexColor("#0f172a"))
        c.drawCentredString(width / 2, height - 305, title)

        # 9. Custom Attributes (if provided, e.g. Grade, Hours, Honors)
        if custom_attributes and isinstance(custom_attributes, dict):
            details = []
            for k, v in custom_attributes.items():
                k_clean = k.replace("_", " ").title()
                details.append(f"{k_clean}: {v}")
            if details:
                c.setFont("Helvetica-Oblique", 11)
                c.setFillColor(colors.HexColor("#475569"))
                c.drawCentredString(width / 2, height - 335, "  •  ".join(details))

        # 10. Footer Section
        footer_y = 100

        # Left Column: Date & Issuer Details
        c.setStrokeColor(colors.HexColor("#94a3b8"))
        c.setLineWidth(1)
        c.line(70, footer_y + 25, 230, footer_y + 25)

        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(colors.HexColor("#1e293b"))
        c.drawCentredString(150, footer_y + 10, issue_date)

        c.setFont("Helvetica", 9)
        c.setFillColor(colors.HexColor("#64748b"))
        c.drawCentredString(150, footer_y - 5, "DATE OF ISSUANCE")

        # Right Column: Authorized Signature Line
        c.setStrokeColor(colors.HexColor("#94a3b8"))
        c.setLineWidth(1)
        c.line(width - 230, footer_y + 25, width - 70, footer_y + 25)

        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(colors.HexColor("#1e293b"))
        c.drawCentredString(width - 150, footer_y + 10, issuer_name)

        c.setFont("Helvetica", 9)
        c.setFillColor(colors.HexColor("#64748b"))
        c.drawCentredString(width - 150, footer_y - 5, "AUTHORIZED SIGNATURE")

        # Center Column: Verification QR Code & Certificate ID
        qr_target = verification_url or f"urn:cert:{certificate_id}"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=4,
            border=1
        )
        qr.add_data(qr_target)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#0f172a", back_color="#fafbfe")
        
        qr_buffer = io.BytesIO()
        img.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)
        qr_image = ImageReader(qr_buffer)
        
        # Draw QR code in bottom center
        qr_size = 54
        c.drawImage(
            qr_image, 
            (width - qr_size) / 2, 
            footer_y - 10, 
            width=qr_size, 
            height=qr_size
        )

        # Certificate ID text
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor("#64748b"))
        c.drawCentredString(width / 2, footer_y - 22, f"Certificate ID: {certificate_id}")
        c.drawCentredString(width / 2, footer_y - 32, f"Recipient: {recipient_email}")

        # Finalize and save
        c.showPage()
        c.save()
        return output_path
