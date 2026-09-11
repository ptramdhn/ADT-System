from fastapi import APIRouter, Request, Response, HTTPException, Depends
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/auth", tags=["Auth"])

ADMIN_PIN = "010126"
VIEWER_PIN = "161616"
COOKIE_NAME = "adt_auth_session"

TOKEN_ADMIN = "adt_session_admin_010126"
TOKEN_VIEWER = "adt_session_viewer_161616"

class PINRequest(BaseModel):
    pin: str

@router.post("/verify-pin")
def verify_pin_endpoint(req: PINRequest, response: Response):
    pin = req.pin.strip()
    if pin == ADMIN_PIN:
        response.set_cookie(
            key=COOKIE_NAME,
            value=TOKEN_ADMIN,
            max_age=30 * 24 * 3600,
            httponly=True,
            samesite="lax"
        )
        return {"success": True, "role": "admin", "message": "Login berhasil (Akses Penuh Admin)"}
    elif pin == VIEWER_PIN:
        response.set_cookie(
            key=COOKIE_NAME,
            value=TOKEN_VIEWER,
            max_age=30 * 24 * 3600,
            httponly=True,
            samesite="lax"
        )
        return {"success": True, "role": "viewer", "message": "Login berhasil (Akses Hanya Lihat / Viewer)"}
    else:
        raise HTTPException(status_code=401, detail="PIN yang Anda masukkan salah")

@router.get("/logout")
def logout_endpoint(response: Response):
    res = RedirectResponse(url="/login", status_code=302)
    res.delete_cookie(COOKIE_NAME)
    return res

def get_current_role(request: Request) -> Optional[str]:
    token = request.cookies.get(COOKIE_NAME)
    if token == TOKEN_ADMIN or token == "authenticated_010126":
        return "admin"
    elif token == TOKEN_VIEWER:
        return "viewer"
    return None

def is_authenticated(request: Request) -> bool:
    return get_current_role(request) is not None

def is_admin(request: Request) -> bool:
    return get_current_role(request) == "admin"

def require_admin(request: Request):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Sesi login telah berakhir, silakan login kembali.")
    if not is_admin(request):
        raise HTTPException(status_code=403, detail="Akses ditolak: Akun Anda memiliki izin 'Hanya Lihat' (Read-Only) dan tidak dapat mengubah/menambah/menghapus data.")

