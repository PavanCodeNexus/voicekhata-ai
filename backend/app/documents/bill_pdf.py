import os
import datetime
from pathlib import Path
from app.config import settings

def create_simple_pdf(filename: str, lines: list, title: str, subtitle: str, total_due: float) -> str:
    """
    Generates a clean, valid PDF 1.4 document using pure Python standard library.
    Zero external dependencies required.
    """
    pdf_path = settings.BILLS_DIR / filename
    
    # PDF stream commands
    # 350 x 500 pt page
    stream_lines = []
    
    # Top banner background (dark navy #0B0F19)
    stream_lines.append("0.043 0.059 0.098 rg") # Fill color
    stream_lines.append("0 430 350 70 re f")
    
    # Top Banner Accent line (cyan #00F2FE)
    stream_lines.append("0.0 0.949 0.996 rg")
    stream_lines.append("0 427 350 3 re f")
    
    # Header text (White)
    stream_lines.append("1.0 1.0 1.0 rg") # White
    stream_lines.append("BT /F1 16 Tf 25 465 Td (Sri Krishna Provision Stores) Tj ET")
    stream_lines.append("0.7 0.8 0.9 rg")
    stream_lines.append("BT /F1 9 Tf 25 442 Td (Zero-Touch Smart Voice Ledger Receipt) Tj ET")
    
    # Content block
    stream_lines.append("0.1 0.1 0.1 rg") # Dark text
    y = 395
    for l in lines:
        safe_line = l.replace("(", "[").replace(")", "]")
        stream_lines.append(f"BT /F1 10 Tf 25 {y} Td ({safe_line}) Tj ET")
        y -= 18
        
    # Divider line
    stream_lines.append("0.8 0.8 0.8 RG 1 w") # Stroke color
    stream_lines.append("25 240 m 325 240 l S")
    
    # Total Outstanding Balance Box (Light grey background)
    stream_lines.append("0.96 0.97 0.98 rg")
    stream_lines.append("25 155 300 70 re f")
    stream_lines.append("0.8 0.85 0.9 RG 1 w")
    stream_lines.append("25 155 300 70 re S")
    
    stream_lines.append("0.1 0.1 0.1 rg")
    stream_lines.append("BT /F1 10 Tf 40 200 Td (Total Outstanding Balance:) Tj ET")
    
    # Total Balance in Red (or Green if cleared)
    if total_due > 0:
        stream_lines.append("0.85 0.15 0.15 rg") # Red
    else:
        stream_lines.append("0.1 0.65 0.25 rg") # Green
    stream_lines.append(f"BT /F1 16 Tf 40 172 Td (Rs. {total_due:.2f}) Tj ET")
    
    # Footer
    stream_lines.append("0.4 0.45 0.5 rg")
    stream_lines.append(f"BT /F1 8.5 Tf 25 125 Td (UPI Payment VPA: {settings.SHOP_UPI_VPA}) Tj ET")
    stream_lines.append("BT /F1 8.5 Tf 25 105 Td (Thank you for your business! Please clear dues on time.) Tj ET")
    stream_lines.append("BT /F1 8 Tf 45 40 Td (Receipt, not a GST invoice  *  Powered by VoiceKhata AI) Tj ET")
    
    content_stream = "\n".join(stream_lines)
    content_bytes = content_stream.encode("latin1")
    content_len = len(content_bytes)
    
    # Construct complete valid PDF 1.4 structure
    objects = []
    
    # 1: Catalog
    objects.append("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    # 2: Pages
    objects.append("2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    # 3: Page (350x500 MediaBox)
    objects.append("3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 350 500] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n")
    # 4: Contents
    objects.append(f"4 0 obj\n<< /Length {content_len} >>\nstream\n{content_stream}\nendstream\nendobj\n")
    # 5: Standard Base Font (Helvetica)
    objects.append("5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")
    
    pdf_header = "%PDF-1.4\n"
    body = "".join(objects)
    
    # Cross-reference table
    xref_pos = len(pdf_header.encode("latin1"))
    offsets = [0]
    cur_offset = xref_pos
    
    for obj in objects:
        offsets.append(cur_offset)
        cur_offset += len(obj.encode("latin1"))
        
    xref = f"xref\n0 {len(offsets)}\n0000000000 65535 f \n"
    for o in offsets[1:]:
        xref += f"{o:010d} 00000 n \n"
        
    trailer = f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{cur_offset}\n%%EOF\n"
    
    full_pdf = pdf_header + body + xref + trailer
    
    with open(pdf_path, "wb") as f:
        f.write(full_pdf.encode("latin1"))
        
    return str(pdf_path)

def generate_bill_pdf(
    bill_no: int,
    customer_name: str,
    amount_rupees: float,
    kind: str,
    new_balance_rupees: float,
    txn_time: str
) -> str:
    """
    FR-B2: Generates clean PDF bill/receipt.
    Labelled: 'Receipt, not a GST invoice'.
    """
    filename = f"bill_{bill_no}_{datetime.date.today().isoformat()}.pdf"
    kind_label = "Credit Sale (Udhaar)" if kind == "credit_sale" else "Payment Received (Jama)"
    
    lines = [
        f"RECEIPT NO: #{bill_no}",
        f"Date: {txn_time}",
        f"Customer: {customer_name}",
        f"Transaction Type: {kind_label}",
        f"Amount: Rs. {amount_rupees:.2f}"
    ]
    
    return create_simple_pdf(
        filename=filename,
        lines=lines,
        title=settings.SHOP_NAME,
        subtitle="Zero-Touch Smart Voice Ledger Receipt",
        total_due=new_balance_rupees
    )
