import json
import os
import sys
from datetime import datetime

# Project root
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from app.db.database import SessionLocal, engine, Base
from app.db.models import PurchaseOrder, SPHRecord, Expense, ProfitSplit, Withdrawal, SystemSetting

def import_all():
    print("Creating tables if not exist...")
    Base.metadata.create_all(bind=engine)

    backup_file = os.path.join(BASE_DIR, "data_backup.json")
    if not os.path.exists(backup_file):
        print(f"File {backup_file} not found!")
        return

    with open(backup_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    db = SessionLocal()
    try:
        # Check existing count
        existing_pos = db.query(PurchaseOrder).count()
        if existing_pos > 0:
            print(f"Database already contains {existing_pos} Purchase Orders. Skipping import.")
            return

        print("Importing SPH records...")
        for s in data.get("sph_records", []):
            rec = SPHRecord(
                id=s["id"],
                sph_seq_number=s["sph_seq_number"],
                sph_number=s["sph_number"],
                date_str=s["date_str"],
                company_name=s["company_name"],
                up_name=s.get("up_name", "-"),
                items_json=s["items_json"],
                has_warranty=s.get("has_warranty", False),
                warranty_days=s.get("warranty_days"),
                pdf_filename=s["pdf_filename"],
                status=s.get("status", "PENAWARAN"),
                total_sph_amount=s.get("total_sph_amount", 0.0),
                created_at=datetime.fromisoformat(s["created_at"]) if s.get("created_at") else datetime.now()
            )
            db.add(rec)
        db.commit()

        print("Importing Purchase Orders...")
        for p in data.get("purchase_orders", []):
            rec = PurchaseOrder(
                id=p["id"],
                sph_id=p.get("sph_id"),
                po_number=p["po_number"],
                po_date=datetime.fromisoformat(p["po_date"]) if p.get("po_date") else datetime.now(),
                client_name=p["client_name"],
                total_po_amount=p["total_po_amount"],
                status=p.get("status", "DALAM_PENGERJAAN"),
                po_pdf_filename=p.get("po_pdf_filename"),
                notes=p.get("notes"),
                items_json=p.get("items_json"),
                created_at=datetime.fromisoformat(p["created_at"]) if p.get("created_at") else datetime.now()
            )
            db.add(rec)
        db.commit()

        print("Importing Expenses...")
        for e in data.get("expenses", []):
            rec = Expense(
                id=e["id"],
                po_id=e["po_id"],
                expense_date=datetime.fromisoformat(e["expense_date"]) if e.get("expense_date") else datetime.now(),
                category=e.get("category", "Material"),
                description=e["description"],
                amount=e["amount"],
                vendor_name=e.get("vendor_name"),
                notes=e.get("notes"),
                created_at=datetime.fromisoformat(e["created_at"]) if e.get("created_at") else datetime.now()
            )
            db.add(rec)
        db.commit()

        print("Importing Profit Splits...")
        for sp in data.get("profit_splits", []):
            rec = ProfitSplit(
                id=sp["id"],
                po_id=sp["po_id"],
                karyawan_1_name=sp.get("karyawan_1_name", "Karyawan 1"),
                karyawan_1_percent=sp.get("karyawan_1_percent", 25.0),
                karyawan_1_amount=sp.get("karyawan_1_amount", 0.0),
                karyawan_2_name=sp.get("karyawan_2_name", "Karyawan 2"),
                karyawan_2_percent=sp.get("karyawan_2_percent", 25.0),
                karyawan_2_amount=sp.get("karyawan_2_amount", 0.0),
                kas_perusahaan_percent=sp.get("kas_perusahaan_percent", 50.0),
                kas_perusahaan_amount=sp.get("kas_perusahaan_amount", 0.0),
                notes=sp.get("notes"),
                updated_at=datetime.fromisoformat(sp["updated_at"]) if sp.get("updated_at") else datetime.now()
            )
            db.add(rec)
        db.commit()

        print("Importing Withdrawals...")
        for w in data.get("withdrawals", []):
            rec = Withdrawal(
                id=w["id"],
                po_id=w.get("po_id"),
                karyawan_name=w["karyawan_name"],
                withdrawal_date=datetime.fromisoformat(w["withdrawal_date"]) if w.get("withdrawal_date") else datetime.now(),
                amount=w["amount"],
                payment_method=w.get("payment_method", "Transfer Bank"),
                notes=w.get("notes"),
                created_at=datetime.fromisoformat(w["created_at"]) if w.get("created_at") else datetime.now()
            )
            db.add(rec)
        db.commit()

        print("All data successfully imported into the database!")
    except Exception as exc:
        db.rollback()
        print(f"Error importing data: {exc}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    import_all()
