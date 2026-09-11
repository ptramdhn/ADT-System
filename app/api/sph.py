import os
import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from pypdf import PdfReader

from app.db.database import get_db
from app.db import crud
from app.core.agent_brain import AgentBrain
from app.core.config import settings
from app.api.auth import require_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sph", tags=["SPH"])
brain = AgentBrain()

class ItemModel(BaseModel):
    description: str
    price: float

class AIExtractRequest(BaseModel):
    prompt: str

class SPHCreateRequest(BaseModel):
    company_name: str
    up_name: Optional[str] = "-"
    items: List[ItemModel]
    has_warranty: bool = False
    warranty_days: Optional[int] = 30
    uploaded_pdf_filename: Optional[str] = None

class SPHUpdateRequest(BaseModel):
    company_name: str
    up_name: Optional[str] = "-"
    date_str: Optional[str] = None
    items: List[ItemModel]
    has_warranty: bool = False
    warranty_days: Optional[int] = 30

class SPHStatusUpdateRequest(BaseModel):
    status: str

@router.post("/extract-prompt")
def extract_sph_prompt_endpoint(req: AIExtractRequest, _ = Depends(require_admin)):
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt tidak boleh kosong")
    
    try:
        extracted_data = brain.parse_sph_instruction(req.prompt)
        return {"success": True, "data": extracted_data}
    except Exception as e:
        logger.error(f"Error extracting SPH prompt: {e}")
        raise HTTPException(status_code=500, detail=f"Gagal mengekstrak prompt AI: {str(e)}")

@router.post("/upload-extract")
async def upload_and_extract_sph(file: UploadFile = File(...), _ = Depends(require_admin)):
    """
    Uploads an existing SPH PDF file, reads text via pypdf, and extracts structured SPH fields via Mistral AI.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Hanya file berekstensi .pdf yang diperbolehkan")

    # Generate safe unique filename
    safe_name = "".join(c for c in file.filename if c.isalnum() or c in (" ", "_", "-", ".")).replace(" ", "_")
    unique_filename = f"SPH_UP_{uuid.uuid4().hex[:8]}_{safe_name}"
    save_path = os.path.join(settings.PDF_OUTPUT_DIR, unique_filename)

    try:
        contents = await file.read()
        with open(save_path, "wb") as f:
            f.write(contents)

        # Extract text using pypdf
        reader = PdfReader(save_path)
        extracted_text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t:
                extracted_text += t + "\n"

        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="Tidak dapat mengekstrak teks dari PDF ini. Pastikan PDF bukan hasil scan/gambar.")

        # Pass to AgentBrain Mistral extractor
        extracted_data = brain.parse_sph_pdf_text(extracted_text)
        return {
            "success": True,
            "filename": unique_filename,
            "data": extracted_data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing SPH upload: {e}")
        raise HTTPException(status_code=500, detail=f"Gagal memproses file SPH: {str(e)}")

@router.post("/create")
def create_sph_endpoint(req: SPHCreateRequest, db: Session = Depends(get_db), _ = Depends(require_admin)):
    if not req.items:
        raise HTTPException(status_code=400, detail="Minimal harus ada 1 barang dalam penawaran")
    
    items_data = [item.model_dump() for item in req.items]
    record = crud.create_sph(
        db=db,
        company_name=req.company_name,
        up_name=req.up_name,
        items=items_data,
        has_warranty=req.has_warranty,
        warranty_days=req.warranty_days
    )
    
    # If a custom uploaded PDF was provided, we can assign or copy it if appropriate
    if req.uploaded_pdf_filename:
        uploaded_path = os.path.join(settings.PDF_OUTPUT_DIR, req.uploaded_pdf_filename)
        if os.path.exists(uploaded_path):
            record.pdf_filename = req.uploaded_pdf_filename
            db.commit()
            db.refresh(record)

    return {
        "success": True,
        "message": f"SPH {record.sph_number} berhasil dibuat",
        "data": {
            "id": record.id,
            "sph_number": record.sph_number,
            "pdf_filename": record.pdf_filename
        }
    }

@router.get("/{sph_id}/detail")
def get_sph_detail_endpoint(sph_id: int, db: Session = Depends(get_db)):
    record = crud.get_sph_by_id(db, sph_id)
    if not record:
        raise HTTPException(status_code=404, detail="SPH tidak ditemukan")
    
    total_est = sum(it.get("price", 0) * (it.get("qty", 1) if "qty" in it else 1) for it in record.items)
    return {
        "success": True,
        "data": {
            "id": record.id,
            "sph_number": record.sph_number,
            "date_str": record.date_str,
            "company_name": record.company_name,
            "up_name": record.up_name,
            "status": record.status,
            "has_warranty": record.has_warranty,
            "warranty_days": record.warranty_days,
            "pdf_filename": record.pdf_filename,
            "items": record.items,
            "total_estimated": total_est
        }
    }

@router.get("/download/{sph_id}")
def download_sph_pdf(sph_id: int, db: Session = Depends(get_db)):
    record = crud.get_sph_by_id(db, sph_id)
    if not record:
        raise HTTPException(status_code=404, detail="SPH tidak ditemukan")
    
    pdf_path = os.path.join(settings.PDF_OUTPUT_DIR, record.pdf_filename)
    if not os.path.exists(pdf_path):
        from app.services.pdf_service import generate_sph_pdf
        generate_sph_pdf(
            dest_path=pdf_path,
            sph_number=record.sph_number,
            date_str=record.date_str,
            company_name=record.company_name,
            up_name=record.up_name,
            items=record.items,
            warranty_days=record.warranty_days if record.has_warranty else None
        )

    return FileResponse(
        path=pdf_path,
        filename=record.pdf_filename,
        media_type="application/pdf",
        content_disposition_type="inline",
        headers={"Content-Disposition": f'inline; filename="{record.pdf_filename}"'}
    )

@router.post("/{sph_id}/status")
def update_status_endpoint(sph_id: int, req: SPHStatusUpdateRequest, db: Session = Depends(get_db), _ = Depends(require_admin)):
    record = crud.update_sph_status(db, sph_id, req.status)
    if not record:
        raise HTTPException(status_code=404, detail="SPH tidak ditemukan")
    return {"success": True, "message": "Status berhasil diupdate", "status": record.status}

@router.put("/{sph_id}")
@router.post("/{sph_id}/update")
def update_sph_endpoint(sph_id: int, req: SPHUpdateRequest, db: Session = Depends(get_db), _ = Depends(require_admin)):
    if not req.items:
        raise HTTPException(status_code=400, detail="Minimal harus ada 1 barang dalam penawaran")
    
    items_data = [item.model_dump() for item in req.items]
    record = crud.update_sph(
        db=db,
        sph_id=sph_id,
        company_name=req.company_name,
        up_name=req.up_name,
        items=items_data,
        date_str=req.date_str,
        has_warranty=req.has_warranty,
        warranty_days=req.warranty_days
    )
    if not record:
        raise HTTPException(status_code=404, detail="SPH tidak ditemukan")
        
    return {
        "success": True,
        "message": f"SPH {record.sph_number} berhasil diperbarui",
        "data": {
            "id": record.id,
            "sph_number": record.sph_number,
            "total_sph_amount": record.total_sph_amount
        }
    }
