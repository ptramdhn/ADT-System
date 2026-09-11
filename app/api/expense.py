from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.db.database import get_db
from app.db import crud
from app.api.auth import require_admin

router = APIRouter(prefix="/api/expenses", tags=["Expenses"])

class ExpenseCreateRequest(BaseModel):
    po_id: int
    category: str
    description: str
    amount: float
    vendor_name: Optional[str] = None
    notes: Optional[str] = None

@router.post("/create")
def create_expense_endpoint(req: ExpenseCreateRequest, db: Session = Depends(get_db), _ = Depends(require_admin)):
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Nominal pengeluaran harus lebih dari 0")
    if not req.description.strip():
        raise HTTPException(status_code=400, detail="Deskripsi pengeluaran wajib diisi")

    po = crud.get_po_by_id(db, req.po_id)
    if not po:
        raise HTTPException(status_code=404, detail="PO terkait tidak ditemukan")

    exp = crud.add_expense(
        db=db,
        po_id=req.po_id,
        category=req.category,
        description=req.description.strip(),
        amount=req.amount,
        vendor_name=req.vendor_name,
        notes=req.notes
    )
    return {"success": True, "message": "Pengeluaran berhasil dicatat", "data": {"id": exp.id, "amount": exp.amount}}

@router.delete("/{expense_id}")
def delete_expense_endpoint(expense_id: int, db: Session = Depends(get_db), _ = Depends(require_admin)):
    success = crud.delete_expense(db, expense_id)
    if not success:
        raise HTTPException(status_code=404, detail="Pengeluaran tidak ditemukan")
    return {"success": True, "message": "Pengeluaran berhasil dihapus"}
