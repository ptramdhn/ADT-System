from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.db.models import SPHRecord, PurchaseOrder, Expense, ProfitSplit, SystemSetting, Withdrawal
from app.services.pdf_service import format_sph_number, format_date_str, generate_sph_pdf
from app.services.profit_service import recalculate_profit_split
from app.core.config import settings
import os
import json
import logging

logger = logging.getLogger(__name__)

# --- SPH CRUD ---
def get_next_sph_sequence(db: Session, date_obj: datetime = None) -> tuple[int, str]:
    if date_obj is None:
        date_obj = datetime.now()
    
    max_seq = db.query(func.max(SPHRecord.sph_seq_number)).scalar() or 0
    next_seq = max_seq + 1
    sph_number = format_sph_number(next_seq, date_obj)
    return next_seq, sph_number

def create_sph(db: Session, company_name: str, up_name: str, items: list, has_warranty: bool = False, warranty_days: int = None, date_obj: datetime = None) -> SPHRecord:
    if date_obj is None:
        date_obj = datetime.now()
        
    next_seq, sph_number = get_next_sph_sequence(db, date_obj)
    date_str = format_date_str(date_obj)
    
    # Calculate total
    total_amount = sum(float(item.get("price", 0)) * float(item.get("qty", 1)) for item in items)

    # Safe PDF filename
    first_item = items[0]["description"] if items else "BARANG"
    safe_item = "".join(c for c in first_item if c.isalnum() or c in (" ", "_", "-")).upper()[:30].strip()
    safe_company = "".join(c for c in company_name if c.isalnum() or c in (" ", "_", "-")).upper()[:20].strip()
    pdf_name = f"SPH_{next_seq:04d}_{safe_item.replace(' ', '_')}_{safe_company.replace(' ', '_')}.pdf"
    dest_path = os.path.join(settings.PDF_OUTPUT_DIR, pdf_name)

    # Generate PDF
    generate_sph_pdf(
        dest_path=dest_path,
        sph_number=sph_number,
        date_str=date_str,
        company_name=company_name,
        up_name=up_name or "-",
        items=items,
        warranty_days=warranty_days if has_warranty else None
    )

    record = SPHRecord(
        sph_seq_number=next_seq,
        sph_number=sph_number,
        date_str=date_str,
        company_name=company_name,
        up_name=up_name or "-",
        has_warranty=has_warranty,
        warranty_days=warranty_days if has_warranty else None,
        pdf_filename=pdf_name,
        status="PENAWARAN",
        total_sph_amount=total_amount
    )
    record.items = items
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

def get_sph_list(db: Session, skip: int = 0, limit: int = 100):
    return db.query(SPHRecord).order_by(desc(SPHRecord.id)).offset(skip).limit(limit).all()

def get_sph_by_id(db: Session, sph_id: int) -> SPHRecord:
    return db.query(SPHRecord).filter(SPHRecord.id == sph_id).first()

def update_sph_status(db: Session, sph_id: int, status: str) -> SPHRecord:
    record = get_sph_by_id(db, sph_id)
    if record:
        record.status = status
        db.commit()
        db.refresh(record)
    return record

def update_sph(
    db: Session,
    sph_id: int,
    company_name: str,
    up_name: str,
    items: list,
    date_str: str = None,
    has_warranty: bool = False,
    warranty_days: int = None
) -> SPHRecord:
    record = get_sph_by_id(db, sph_id)
    if not record:
        return None
    
    total_amount = sum(float(item.get("price", 0)) * float(item.get("qty", 1)) for item in items)
    
    record.company_name = company_name.strip()
    record.up_name = up_name.strip() if up_name else "-"
    if date_str and date_str.strip():
        record.date_str = date_str.strip()
    record.items = items
    record.total_sph_amount = total_amount
    record.has_warranty = has_warranty
    record.warranty_days = warranty_days if has_warranty else None

    # Regenerate PDF so changes appear on PDF preview immediately
    if record.pdf_filename:
        pdf_path = os.path.join(settings.PDF_OUTPUT_DIR, record.pdf_filename)
        try:
            generate_sph_pdf(
                dest_path=pdf_path,
                sph_number=record.sph_number,
                date_str=record.date_str,
                company_name=record.company_name,
                up_name=record.up_name,
                items=record.items,
                warranty_days=record.warranty_days if record.has_warranty else None
            )
        except Exception as e:
            logger.warning(f"Failed to regenerate PDF for SPH {record.sph_number}: {e}")

    db.commit()
    db.refresh(record)
    return record


# --- PO CRUD ---
def create_po(db: Session, po_number: str, client_name: str, total_po_amount: float, sph_id: int = None, notes: str = None, po_date: datetime = None, po_pdf_filename: str = None, items: list = None) -> PurchaseOrder:
    if po_date is None:
        po_date = datetime.now()
        
    items_str = json.dumps(items, ensure_ascii=False) if items else None

    po = PurchaseOrder(
        sph_id=sph_id,
        po_number=po_number,
        po_date=po_date,
        client_name=client_name,
        total_po_amount=total_po_amount,
        status="DALAM_PENGERJAAN",
        notes=notes,
        po_pdf_filename=po_pdf_filename,
        items_json=items_str
    )
    db.add(po)
    db.flush()

    # If linked to SPH, update SPH status to PO_TURUN
    if sph_id:
        sph = get_sph_by_id(db, sph_id)
        if sph:
            sph.status = "PO_TURUN"

    # Create initial ProfitSplit
    recalculate_profit_split(po, db)

    db.commit()
    db.refresh(po)
    return po

def get_po_list(db: Session, skip: int = 0, limit: int = 100):
    return db.query(PurchaseOrder).order_by(desc(PurchaseOrder.id)).offset(skip).limit(limit).all()

def get_po_by_id(db: Session, po_id: int) -> PurchaseOrder:
    return db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()

def update_po(db: Session, po_id: int, po_number: str, client_name: str, total_po_amount: float, status: str, notes: str = None) -> PurchaseOrder:
    po = get_po_by_id(db, po_id)
    if po:
        po.po_number = po_number
        po.client_name = client_name
        po.total_po_amount = total_po_amount
        po.status = status
        po.notes = notes
        db.commit()
        recalculate_profit_split(po, db)
        db.refresh(po)
    return po


# --- EXPENSE CRUD ---
def add_expense(db: Session, po_id: int, category: str, description: str, amount: float, vendor_name: str = None, notes: str = None, expense_date: datetime = None) -> Expense:
    if expense_date is None:
        expense_date = datetime.now()

    exp = Expense(
        po_id=po_id,
        expense_date=expense_date,
        category=category,
        description=description,
        amount=amount,
        vendor_name=vendor_name,
        notes=notes
    )
    db.add(exp)
    db.flush()

    # Recalculate profit for the PO
    po = get_po_by_id(db, po_id)
    if po:
        recalculate_profit_split(po, db)

    db.commit()
    db.refresh(exp)
    return exp

def delete_expense(db: Session, expense_id: int) -> bool:
    exp = db.query(Expense).filter(Expense.id == expense_id).first()
    if exp:
        po_id = exp.po_id
        db.delete(exp)
        db.commit()
        po = get_po_by_id(db, po_id)
        if po:
            recalculate_profit_split(po, db)
        return True
    return False


# --- PROFIT SPLIT SETTINGS PER PO ---
def update_po_profit_split(db: Session, po_id: int, k1_name: str, k1_percent: float, k2_name: str, k2_percent: float, kas_percent: float) -> ProfitSplit:
    po = get_po_by_id(db, po_id)
    if not po:
        return None
    split = po.profit_split
    if not split:
        split = ProfitSplit(po_id=po.id)
        db.add(split)
    
    split.karyawan_1_name = k1_name
    split.karyawan_1_percent = k1_percent
    split.karyawan_2_name = k2_name
    split.karyawan_2_percent = k2_percent
    split.kas_perusahaan_percent = kas_percent

    db.commit()
    return recalculate_profit_split(po, db)


# --- DASHBOARD METRICS ---
def get_dashboard_summary(db: Session) -> dict:
    total_sph = db.query(func.count(SPHRecord.id)).scalar() or 0
    total_po = db.query(func.count(PurchaseOrder.id)).scalar() or 0
    active_po = db.query(func.count(PurchaseOrder.id)).filter(PurchaseOrder.status == "DALAM_PENGERJAAN").scalar() or 0
    completed_po = db.query(func.count(PurchaseOrder.id)).filter(PurchaseOrder.status == "SELESAI").scalar() or 0

    total_omzet = db.query(func.sum(PurchaseOrder.total_po_amount)).scalar() or 0.0
    total_expense = db.query(func.sum(Expense.amount)).scalar() or 0.0
    total_laba_bersih = max(0.0, total_omzet - total_expense)

    # Sum of profit splits across all POs
    total_k1 = db.query(func.sum(ProfitSplit.karyawan_1_amount)).scalar() or 0.0
    total_k2 = db.query(func.sum(ProfitSplit.karyawan_2_amount)).scalar() or 0.0
    total_kas = db.query(func.sum(ProfitSplit.kas_perusahaan_amount)).scalar() or 0.0

    recent_sph = db.query(SPHRecord).order_by(desc(SPHRecord.id)).limit(5).all()
    recent_po = db.query(PurchaseOrder).order_by(desc(PurchaseOrder.id)).limit(5).all()

    return {
        "total_sph": total_sph,
        "total_po": total_po,
        "active_po": active_po,
        "completed_po": completed_po,
        "total_omzet": total_omzet,
        "total_expense": total_expense,
        "total_laba_bersih": total_laba_bersih,
        "total_k1": total_k1,
        "total_k2": total_k2,
        "total_kas": total_kas,
        "recent_sph": recent_sph,
        "recent_po": recent_po
    }


# --- WITHDRAWAL CRUD ---
def add_withdrawal(db: Session, karyawan_name: str, amount: float, po_id: int = None, payment_method: str = "Transfer Bank", notes: str = None, withdrawal_date: datetime = None) -> Withdrawal:
    if withdrawal_date is None:
        withdrawal_date = datetime.now()
    w = Withdrawal(
        karyawan_name=karyawan_name,
        amount=amount,
        po_id=po_id,
        payment_method=payment_method,
        notes=notes,
        withdrawal_date=withdrawal_date
    )
    db.add(w)
    db.commit()
    db.refresh(w)
    return w

def delete_withdrawal(db: Session, withdrawal_id: int) -> bool:
    w = db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).first()
    if w:
        db.delete(w)
        db.commit()
        return True
    return False

def get_withdrawals_list(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Withdrawal).order_by(desc(Withdrawal.withdrawal_date)).offset(skip).limit(limit).all()

def get_karyawan_balance_summary(db: Session) -> dict:
    # Total Earned
    total_earned_k1 = db.query(func.sum(ProfitSplit.karyawan_1_amount)).scalar() or 0.0
    total_earned_k2 = db.query(func.sum(ProfitSplit.karyawan_2_amount)).scalar() or 0.0

    # Total Withdrawn
    total_withdrawn_k1 = db.query(func.sum(Withdrawal.amount)).filter(Withdrawal.karyawan_name == "Karyawan 1").scalar() or 0.0
    total_withdrawn_k2 = db.query(func.sum(Withdrawal.amount)).filter(Withdrawal.karyawan_name == "Karyawan 2").scalar() or 0.0

    balance_k1 = total_earned_k1 - total_withdrawn_k1
    balance_k2 = total_earned_k2 - total_withdrawn_k2

    return {
        "k1": {
            "name": "Karyawan 1",
            "earned": total_earned_k1,
            "withdrawn": total_withdrawn_k1,
            "balance": balance_k1
        },
        "k2": {
            "name": "Karyawan 2",
            "earned": total_earned_k2,
            "withdrawn": total_withdrawn_k2,
            "balance": balance_k2
        }
    }

# Aliases for compatibility
get_all_sph = get_sph_list
get_all_pos = get_po_list
get_financial_summary = get_dashboard_summary
get_employee_balances = get_karyawan_balance_summary
get_all_withdrawals = get_withdrawals_list

def get_dashboard_summary(db: Session) -> dict:
    total_sph = db.query(func.count(SPHRecord.id)).scalar() or 0
    sph_po_turun_count = db.query(func.count(SPHRecord.id)).filter(SPHRecord.status == "PO_TURUN").scalar() or 0
    total_po = db.query(func.count(PurchaseOrder.id)).scalar() or 0
    active_po = db.query(func.count(PurchaseOrder.id)).filter(PurchaseOrder.status == "DALAM_PENGERJAAN").scalar() or 0
    completed_po = db.query(func.count(PurchaseOrder.id)).filter(PurchaseOrder.status == "SELESAI").scalar() or 0

    total_omzet = float(db.query(func.sum(PurchaseOrder.total_po_amount)).scalar() or 0.0)
    total_expense = float(db.query(func.sum(Expense.amount)).scalar() or 0.0)
    total_laba_bersih = max(0.0, total_omzet - total_expense)
    average_margin = (total_laba_bersih / total_omzet * 100.0) if total_omzet > 0 else 0.0

    # Sum of profit splits across all POs
    total_k1 = float(db.query(func.sum(ProfitSplit.karyawan_1_amount)).scalar() or 0.0)
    total_k2 = float(db.query(func.sum(ProfitSplit.karyawan_2_amount)).scalar() or 0.0)
    total_kas = float(db.query(func.sum(ProfitSplit.kas_perusahaan_amount)).scalar() or 0.0)

    recent_sph = db.query(SPHRecord).order_by(desc(SPHRecord.id)).limit(5).all()
    recent_po = db.query(PurchaseOrder).order_by(desc(PurchaseOrder.id)).limit(5).all()

    return {
        "total_sph": total_sph,
        "sph_po_turun_count": sph_po_turun_count,
        "total_po": total_po,
        "active_po": active_po,
        "completed_po": completed_po,
        "total_omzet": total_omzet,
        "total_expense": total_expense,
        "total_pengeluaran": total_expense,
        "total_laba_bersih": total_laba_bersih,
        "average_margin": average_margin,
        "total_k1": total_k1,
        "total_karyawan_1": total_k1,
        "total_k2": total_k2,
        "total_karyawan_2": total_k2,
        "total_kas": total_kas,
        "recent_sph": recent_sph,
        "recent_po": recent_po
    }

get_financial_summary = get_dashboard_summary
