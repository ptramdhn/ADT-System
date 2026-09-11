import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from app.core.config import settings

ROMAN_MONTHS = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]
INDONESIAN_MONTHS = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember"
]

def get_roman_month(month: int) -> str:
    if 1 <= month <= 12:
        return ROMAN_MONTHS[month - 1]
    return "I"

def get_indonesian_month_name(month: int) -> str:
    if 1 <= month <= 12:
        return INDONESIAN_MONTHS[month - 1]
    return "Januari"

def format_sph_number(seq_num: int, date_obj: datetime) -> str:
    roman_m = get_roman_month(date_obj.month)
    return f"No. {seq_num:04d}/SPH/ADT/{roman_m}/{date_obj.year}"

def format_date_str(date_obj: datetime) -> str:
    m_name = get_indonesian_month_name(date_obj.month)
    return f"Jakarta, {date_obj.day:02d} {m_name} {date_obj.year}"

def angka_ke_terbilang_hari(n: int) -> str:
    if n == 14:
        return "14 (empat belas)"
    elif n == 30:
        return "30 (tiga puluh)"
    elif n == 7:
        return "7 (tujuh)"
    elif n == 60:
        return "60 (enam puluh)"
    elif n == 90:
        return "90 (sembilan puluh)"
    
    units = ["", "satu", "dua", "tiga", "empat", "lima", "enam", "tujuh", "delapan", "sembilan", "sepuluh", "sebelas"]
    if n <= 11:
        return f"{n} ({units[n]})"
    elif n < 20:
        return f"{n} ({units[n-10]} belas)"
    elif n < 100:
        tens = n // 10
        ones = n % 10
        ones_str = " " + units[ones] if ones > 0 else ""
        return f"{n} ({units[tens]} puluh{ones_str})"
    return f"{n}"

def escape_pdf_text(text: str) -> str:
    if not text:
        return ""
    text = str(text)
    replacements = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        "\u2300": "Ø",
        "\u2205": "Ø",
        "\u00d7": "x",
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"'
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text

def generate_sph_pdf(dest_path: str, sph_number: str, date_str: str, company_name: str, up_name: str, items: list, warranty_days: int = None):
    os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
    
    doc = SimpleDocTemplate(
        dest_path,
        pagesize=A4,
        rightMargin=54,
        leftMargin=54,
        topMargin=40,
        bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    style_normal = ParagraphStyle(
        name='NormalCustom',
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#000000')
    )
    
    style_bold = ParagraphStyle(
        name='BoldCustom',
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#000000')
    )
    
    style_center = ParagraphStyle(
        name='CenterCustom',
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#000000')
    )
    
    style_table_header = ParagraphStyle(
        name='TableHeader',
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#000000')
    )

    style_header_title = ParagraphStyle(
        name='HeaderTitle',
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=16,
        textColor=colors.HexColor('#111827')
    )
    
    style_header_subtitle = ParagraphStyle(
        name='HeaderSubtitle',
        fontName='Helvetica',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor('#4B5563')
    )
    
    style_header_contact = ParagraphStyle(
        name='HeaderContact',
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        alignment=TA_RIGHT,
        textColor=colors.HexColor('#1F2937')
    )

    story = []
    
    # --- HEADER ---
    logo_path = str(settings.LOGO_PATH)
    if os.path.exists(logo_path):
        logo_img = Image(logo_path, width=72, height=60)
        title_p = Paragraph("PT ANUGRAH DJAYA TUNGGAL", style_header_title)
        subtitle_p = Paragraph("Mengerjakan Barang Teknik & General Supplier", style_header_subtitle)
        
        inner_table = Table([[logo_img, [title_p, subtitle_p]]], colWidths=[78, 259])
        inner_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (1,0), (1,0), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
        ]))
        header_left_flowable = inner_table
    else:
        title_p = Paragraph("PT ANUGRAH DJAYA TUNGGAL", style_header_title)
        subtitle_p = Paragraph("Mengerjakan Barang Teknik & General Supplier", style_header_subtitle)
        header_left_flowable = Table([[[title_p, subtitle_p]]])
        header_left_flowable.setStyle(TableStyle([('PADDING', (0,0), (-1,-1), 0)]))
        
    contact_text = (
        "Jl. Luar Batang, Penjaringan,<br/>"
        "Jakarta Utara<br/>"
        "+62 858-8891-2997  <font color='#DC2626'>&#9742;</font><br/>"
        "anugrahdjayatunggal@gmail.com  <font color='#DC2626'>&#9993;</font>"
    )
    contact_p = Paragraph(contact_text, style_header_contact)
    
    header_table = Table([[header_left_flowable, contact_p]], colWidths=[337, 150])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 4))
    
    # Decorative lines
    blue_line = HRFlowable(
        width="37%",
        thickness=3,
        color=colors.HexColor("#1E3A8A"),
        hAlign='LEFT',
        spaceBefore=0,
        spaceAfter=2
    )
    black_line = HRFlowable(
        width="100%",
        thickness=0.5,
        color=colors.HexColor("#000000"),
        hAlign='LEFT',
        spaceBefore=0,
        spaceAfter=15
    )
    story.append(blue_line)
    story.append(black_line)
    
    # --- METADATA ---
    meta_text = f"{date_str}<br/>{sph_number}"
    story.append(Paragraph(meta_text, style_normal))
    story.append(Spacer(1, 15))
    
    # --- RECIPIENT ---
    safe_company = escape_pdf_text(company_name)
    safe_up = escape_pdf_text(up_name)
    recipient_text = f"Kepada Yth,<br/><b>{safe_company}</b><br/>Up : {safe_up}"
    story.append(Paragraph(recipient_text, style_normal))
    story.append(Spacer(1, 15))
    
    # --- GREETING ---
    opening_text = (
        "Dengan Hormat,<br/><br/>"
        "Bersama surat ini, kami dari <b>PT Anugrah Djaya Tunggal</b> bermaksud untuk mengajukan penawaran harga atas "
        "kebutuhan material sebagaimana tertera pada tabel berikut:"
    )
    story.append(Paragraph(opening_text, style_normal))
    story.append(Spacer(1, 12))
    
    # --- TABLE ---
    table_data = [[
        Paragraph("No", style_table_header),
        Paragraph("Deskripsi Barang & Spesifikasi Teknis", style_table_header),
        Paragraph("Harga Satuan (Rp)", style_table_header)
    ]]
    
    for idx, item in enumerate(items, 1):
        desc = escape_pdf_text(item.get("description", ""))
        price = float(item.get("price", 0))
        price_str = f"{price:,.0f}".replace(",", ".")
        table_data.append([
            Paragraph(str(idx), style_center),
            Paragraph(desc, style_center),
            Paragraph(price_str, style_center)
        ])
        
    pricing_table = Table(table_data, colWidths=[40, 310, 137])
    pricing_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#000000')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(pricing_table)
    story.append(Spacer(1, 10))
    
    # --- TERMS ---
    terms = ["Harga Netto, Tidak Termasuk PPN"]
    if warranty_days:
        days_str = angka_ke_terbilang_hari(warranty_days)
        terms.append(
            f"Garansi: Berlaku selama {days_str} hari kalender terhitung sejak barang diterima secara sah oleh pihak pembeli. "
            "Garansi terbatas pada penggantian barang (replacement) akibat cacat produksi pabrik (manufacturing defect), "
            "dan tidak berlaku untuk kerusakan yang disebabkan oleh kesalahan instalasi, modifikasi, atau kelalaian penggunaan (human error) oleh pihak pembeli."
        )
        
    for term in terms:
        story.append(Paragraph(f"• {term}", style_normal))
        
    story.append(Spacer(1, 20))
    
    # --- CLOSING ---
    closing_text = (
        f"Demikian surat penawaran harga ini kami sampaikan. Besar harapan kami untuk dapat menjalin kerja sama "
        f"yang baik dengan {company_name}."
    )
    story.append(Paragraph(closing_text, style_normal))
    story.append(Spacer(1, 35))
    
    # --- SIGNATURE ---
    sig_text = (
        "Hormat kami,<br/><br/><br/><br/><br/>"
        "<b>Aditya Putra Ramadhan</b><br/>"
        "Hp. 085888912997"
    )
    story.append(Paragraph(sig_text, style_normal))
    
    doc.build(story)
    return dest_path
