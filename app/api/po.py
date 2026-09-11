import os
import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from pypdf import PdfReader

from app.db.database import get_db
from app.db import crud
from app.core.agent_brain import AgentBrain
from app.core.config import settings
from app.api.auth import require_admin
import json

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/po", tags=["Purchase Order"])
brain = AgentBrain()

class POCreateRequest(BaseModel):
    sph_id: Optional[int] = None
    po_number: str
    client_name: str
    total_po_amount: float
    notes: Optional[str] = None
    po_pdf_filename: Optional[str] = None
    items: Optional[list] = None

class POUpdateRequest(BaseModel):
    po_number: str
    client_name: str
    total_po_amount: float
    status: str
    notes: Optional[str] = None
    items: Optional[list] = None

class POItemsUpdateRequest(BaseModel):
    items: list

class ProfitSplitUpdateRequest(BaseModel):
    karyawan_1_name: str
    karyawan_1_percent: float
    karyawan_2_name: str
    karyawan_2_percent: float
    kas_perusahaan_percent: float

@router.post("/upload-extract")
async def upload_and_extract_po(file: UploadFile = File(...), _ = Depends(require_admin)):
    """
    Uploads a PO PDF file, reads text via pypdf, and extracts structured PO fields via Mistral AI.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Hanya file berekstensi .pdf yang diperbolehkan")

    # Generate safe unique filename
    safe_name = "".join(c for c in file.filename if c.isalnum() or c in (" ", "_", "-", ".")).replace(" ", "_")
    unique_filename = f"PO_{uuid.uuid4().hex[:8]}_{safe_name}"
    save_path = os.path.join(settings.PO_UPLOAD_DIR, unique_filename)

    try:
        contents = await file.read()
        with open(save_path, "wb") as f:
            f.write(contents)

        # Extract text from PDF using pypdf
        reader = PdfReader(save_path)
        extracted_text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t:
                extracted_text += t + "\n"

        if not extracted_text.strip():
            return {
                "success": True,
                "filename": unique_filename,
                "data": {
                    "po_number": "",
                    "client_name": "",
                    "total_po_amount": 0,
                    "notes": "Dokumen berupa gambar scan (tidak dapat dibaca teks langsung). Harap verifikasi nomor dan nominal manual.",
                    "items": []
                }
            }

        # Parse text using Mistral AI
        extracted_data = brain.parse_po_pdf_text(extracted_text)
        return {
            "success": True,
            "filename": unique_filename,
            "data": extracted_data
        }

    except Exception as e:
        logger.error(f"Error processing PO upload: {e}")
        raise HTTPException(status_code=500, detail=f"Gagal memproses file PO: {str(e)}")

@router.post("/create")
def create_po_endpoint(req: POCreateRequest, db: Session = Depends(get_db), _ = Depends(require_admin)):
    if not req.po_number.strip() or not req.client_name.strip():
        raise HTTPException(status_code=400, detail="Nomor PO dan Nama Klien wajib diisi")
    
    # Check if duplicate PO number
    existing = db.query(crud.PurchaseOrder).filter(crud.PurchaseOrder.po_number == req.po_number.strip()).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Nomor PO '{req.po_number}' sudah ada di sistem")

    po = crud.create_po(
        db=db,
        po_number=req.po_number.strip(),
        client_name=req.client_name.strip(),
        total_po_amount=req.total_po_amount,
        sph_id=req.sph_id,
        notes=req.notes,
        po_pdf_filename=req.po_pdf_filename,
        items=req.items
    )
    return {"success": True, "message": f"PO {po.po_number} berhasil dibuat", "data": {"id": po.id, "po_number": po.po_number}}

@router.get("/download-pdf/{po_id}")
def download_po_uploaded_pdf(po_id: int, db: Session = Depends(get_db)):
    po = crud.get_po_by_id(db, po_id)
    if not po or not po.po_pdf_filename:
        raise HTTPException(status_code=404, detail="File PDF PO tidak ditemukan untuk PO ini")
    
    pdf_path = os.path.join(settings.PO_UPLOAD_DIR, po.po_pdf_filename)
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="File fisik PDF PO tidak ada di server")

    return FileResponse(
        path=pdf_path,
        filename=po.po_pdf_filename,
        media_type="application/pdf",
        content_disposition_type="inline",
        headers={"Content-Disposition": f'inline; filename="{po.po_pdf_filename}"'}
    )

@router.post("/{po_id}/update")
def update_po_endpoint(po_id: int, req: POUpdateRequest, db: Session = Depends(get_db), _ = Depends(require_admin)):
    po = crud.update_po(
        db=db,
        po_id=po_id,
        po_number=req.po_number,
        client_name=req.client_name,
        total_po_amount=req.total_po_amount,
        status=req.status,
        notes=req.notes
    )
    if not po:
        raise HTTPException(status_code=404, detail="PO tidak ditemukan")
    if req.items is not None:
        po.items_json = json.dumps(req.items, ensure_ascii=False)
        db.commit()
    return {"success": True, "message": "Data PO berhasil diperbarui"}

@router.post("/{po_id}/update-items")
def update_po_items_endpoint(po_id: int, req: POItemsUpdateRequest, db: Session = Depends(get_db), _ = Depends(require_admin)):
    po = crud.get_po_by_id(db, po_id)
    if not po:
        raise HTTPException(status_code=404, detail="PO tidak ditemukan")
    po.items_json = json.dumps(req.items, ensure_ascii=False)
    db.commit()
    db.refresh(po)
    return {"success": True, "message": "Daftar barang PO berhasil diperbarui"}

@router.post("/{po_id}/profit-split")
def update_profit_split_endpoint(po_id: int, req: ProfitSplitUpdateRequest, db: Session = Depends(get_db), _ = Depends(require_admin)):
    total_pct = req.karyawan_1_percent + req.karyawan_2_percent + req.kas_perusahaan_percent
    if abs(total_pct - 100.0) > 0.01:
        raise HTTPException(status_code=400, detail=f"Total persentase harus 100% (saat ini: {total_pct}%)")
        
    split = crud.update_po_profit_split(
        db=db,
        po_id=po_id,
        k1_name=req.karyawan_1_name,
        k1_percent=req.karyawan_1_percent,
        k2_name=req.karyawan_2_name,
        k2_percent=req.karyawan_2_percent,
        kas_percent=req.kas_perusahaan_percent
    )
    if not split:
        raise HTTPException(status_code=404, detail="PO tidak ditemukan")
    return {"success": True, "message": "Persentase bagi hasil berhasil diperbarui"}
