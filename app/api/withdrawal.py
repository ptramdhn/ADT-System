from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.db.database import get_db
from app.db import crud
from app.api.auth import require_admin

router = APIRouter(prefix="/api/withdrawals", tags=["Withdrawals"])

class WithdrawalCreateRequest(BaseModel):
    karyawan_name: str # "Karyawan 1" or "Karyawan 2"
    amount: float
    po_id: Optional[int] = None
    payment_method: Optional[str] = "Transfer Bank"
    notes: Optional[str] = None
    withdrawal_date: Optional[datetime] = None

@router.post("/create")
def create_withdrawal_endpoint(req: WithdrawalCreateRequest, db: Session = Depends(get_db), _ = Depends(require_admin)):
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Nominal pengambilan harus lebih dari Rp 0")
    if req.karyawan_name not in ["Karyawan 1", "Karyawan 2"]:
        raise HTTPException(status_code=400, detail="Pilihan karyawan harus 'Karyawan 1' atau 'Karyawan 2'")

    w = crud.add_withdrawal(
        db=db,
        karyawan_name=req.karyawan_name,
        amount=req.amount,
        po_id=req.po_id,
        payment_method=req.payment_method,
        notes=req.notes,
        withdrawal_date=req.withdrawal_date
    )
    return {"success": True, "message": f"Pengambilan uang Rp {w.amount:,.0f} untuk {w.karyawan_name} berhasil dicatat", "data": {"id": w.id}}

@router.delete("/{withdrawal_id}")
def delete_withdrawal_endpoint(withdrawal_id: int, db: Session = Depends(get_db), _ = Depends(require_admin)):
    success = crud.delete_withdrawal(db, withdrawal_id)
    if not success:
        raise HTTPException(status_code=404, detail="Data pengambilan tidak ditemukan")
    return {"success": True, "message": "Catatan pengambilan uang berhasil dihapus"}
