import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.db.database import init_db, get_db
from app.api.sph import router as sph_router
from app.api.po import router as po_router
from app.api.expense import router as expense_router
from app.api.withdrawal import router as withdrawal_router
from app.api.chat import router as chat_router
from app.api.auth import router as auth_router, is_authenticated, get_current_role, is_admin
from app.db import crud

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize MySQL tables on startup
    init_db()
    yield

app = FastAPI(title="ADT-System", lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Register API Routers
app.include_router(auth_router)
app.include_router(sph_router)
app.include_router(po_router)
app.include_router(expense_router)
app.include_router(withdrawal_router)
app.include_router(chat_router)

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if is_authenticated(request):
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(request=request, name="login.html", context={})

@app.get("/logout")
def logout_page():
    res = RedirectResponse(url="/login", status_code=302)
    res.delete_cookie("adt_auth_session")
    return res

@app.get("/", response_class=HTMLResponse)
def dashboard_page(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)
    db = next(get_db())
    summary = crud.get_financial_summary(db)
    recent_sph = crud.get_all_sph(db)[:5]
    recent_po = crud.get_all_pos(db)[:5]
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "active_tab": "dashboard",
            "summary": summary,
            "recent_sph": recent_sph,
            "recent_po": recent_po,
            "current_role": get_current_role(request),
            "is_admin": is_admin(request),
        }
    )

@app.get("/sph", response_class=HTMLResponse)
def sph_list_page(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)
    db = next(get_db())
    sph_list = crud.get_all_sph(db)
    return templates.TemplateResponse(
        request=request,
        name="sph_list.html",
        context={
            "active_tab": "sph",
            "sph_list": sph_list,
            "current_role": get_current_role(request),
            "is_admin": is_admin(request),
        }
    )

@app.get("/po", response_class=HTMLResponse)
def po_list_page(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)
    db = next(get_db())
    po_list = crud.get_all_pos(db)
    return templates.TemplateResponse(
        request=request,
        name="po_list.html",
        context={
            "active_tab": "po",
            "po_list": po_list,
            "current_role": get_current_role(request),
            "is_admin": is_admin(request),
        }
    )

@app.get("/po/{po_id}", response_class=HTMLResponse)
def po_detail_page(request: Request, po_id: int):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)
    db = next(get_db())
    po = crud.get_po_by_id(db, po_id)
    if not po:
        return RedirectResponse(url="/po", status_code=302)
    return templates.TemplateResponse(
        request=request,
        name="po_detail.html",
        context={
            "active_tab": "po",
            "po": po,
            "current_role": get_current_role(request),
            "is_admin": is_admin(request),
        }
    )

@app.get("/financial", response_class=HTMLResponse)
def financial_page(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)
    db = next(get_db())
    summary = crud.get_financial_summary(db)
    balances = crud.get_employee_balances(db)
    withdrawals = crud.get_all_withdrawals(db)
    po_list = crud.get_all_pos(db)
    return templates.TemplateResponse(
        request=request,
        name="financial.html",
        context={
            "active_tab": "financial",
            "summary": summary,
            "balances": balances,
            "withdrawals": withdrawals,
            "po_list": po_list,
            "current_role": get_current_role(request),
            "is_admin": is_admin(request),
        }
    )

@app.get("/chat", response_class=HTMLResponse)
def chat_page(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(
        request=request,
        name="chat.html",
        context={
            "active_tab": "chat",
            "current_role": get_current_role(request),
            "is_admin": is_admin(request),
        }
    )

@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "active_tab": "settings",
            "current_role": get_current_role(request),
            "is_admin": is_admin(request),
        }
    )
