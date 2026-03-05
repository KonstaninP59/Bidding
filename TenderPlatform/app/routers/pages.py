from fastapi import APIRouter, Request, Depends, Query
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, selectinload
from app import models
from app.dependencies import get_db, get_current_active_user, get_current_customer, get_current_admin
from typing import Optional

router = APIRouter(tags=["Страницы"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def page_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/login")
def page_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/register")
def page_register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@router.get("/tenders-list")
def page_tenders_list(
    request: Request,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50)
):
    offset = (page - 1) * per_page
    tenders = db.query(models.Tender).filter(
        models.Tender.status == models.TenderStatus.PUBLISHED
    ).order_by(models.Tender.created_at.desc()).offset(offset).limit(per_page).all()
    total = db.query(models.Tender).filter(models.Tender.status == models.TenderStatus.PUBLISHED).count()
    return templates.TemplateResponse("tenders_list.html", {
        "request": request,
        "tenders": tenders,
        "page": page,
        "per_page": per_page,
        "total": total
    })


@router.get("/tender/{tender_id}")
def page_tender_detail(tender_id: int, request: Request, db: Session = Depends(get_db), token: Optional[str] = Query(None)):
    tender = db.query(models.Tender).options(
        selectinload(models.Tender.items),
        selectinload(models.Tender.criteria),
        selectinload(models.Tender.rounds)
    ).filter(models.Tender.id == tender_id).first()
    if not tender:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    active_round = next((r for r in tender.rounds if r.status == models.RoundStatus.ACTIVE), None)
    return templates.TemplateResponse("tender_detail.html", {
        "request": request,
        "tender": tender,
        "active_round": active_round,
        "token": token
    })


@router.get("/profile")
def page_profile(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    company = db.query(models.Company).filter(models.Company.id == current_user.company_id).first()
    documents = db.query(models.CompanyDocument).filter(models.CompanyDocument.company_id == company.id).all() if company else []
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": current_user,
        "company": company,
        "documents": documents
    })


# --- Кабинет заказчика ---
@router.get("/customer/dashboard")
def customer_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_customer)
):
    tenders = db.query(models.Tender).filter(models.Tender.owner_id == current_user.id).order_by(models.Tender.created_at.desc()).all()
    return templates.TemplateResponse("customer/dashboard.html", {
        "request": request,
        "tenders": tenders
    })


@router.get("/customer/tender/new")
def customer_new_tender(request: Request, current_user: models.User = Depends(get_current_customer)):
    return templates.TemplateResponse("customer/create_tender.html", {"request": request})


@router.get("/customer/tender/{tender_id}")
def customer_tender_detail(tender_id: int, request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_customer)):
    tender = db.query(models.Tender).filter(
        models.Tender.id == tender_id,
        models.Tender.owner_id == current_user.id
    ).options(
        selectinload(models.Tender.items),
        selectinload(models.Tender.criteria),
        selectinload(models.Tender.rounds).selectinload(models.TenderRound.proposals),
        selectinload(models.Tender.invitations)
    ).first()
    if not tender:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    return templates.TemplateResponse("customer/tender_detail.html", {
        "request": request,
        "tender": tender
    })


@router.get("/customer/tender/{tender_id}/rounds")
def customer_rounds(tender_id: int, request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_customer)):
    tender = db.query(models.Tender).filter(
        models.Tender.id == tender_id,
        models.Tender.owner_id == current_user.id
    ).options(
        selectinload(models.Tender.rounds),
        selectinload(models.Tender.invitations)
    ).first()
    if not tender:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    suppliers = db.query(models.User).filter(
        models.User.role == models.UserRole.SUPPLIER,
        models.User.company.has(models.Company.accreditation_status == models.SupplierStatus.ACCREDITED)
    ).all()
    return templates.TemplateResponse("customer/round_management.html", {
        "request": request,
        "tender": tender,
        "suppliers": suppliers
    })


@router.get("/customer/tender/{tender_id}/evaluation")
def customer_evaluation(tender_id: int, request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_customer)):
    tender = db.query(models.Tender).filter(
        models.Tender.id == tender_id,
        models.Tender.owner_id == current_user.id
    ).options(
        selectinload(models.Tender.criteria),
        selectinload(models.Tender.rounds).selectinload(models.TenderRound.proposals).selectinload(models.Proposal.values),
        selectinload(models.Tender.rounds).selectinload(models.TenderRound.proposals).selectinload(models.Proposal.supplier)
    ).first()
    if not tender:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    # Берём последний завершённый раунд
    last_round = next((r for r in reversed(tender.rounds) if r.status == models.RoundStatus.COMPLETED), None)
    proposals = last_round.proposals if last_round else []
    return templates.TemplateResponse("customer/evaluation.html", {
        "request": request,
        "tender": tender,
        "round": last_round,
        "proposals": proposals
    })


# --- Кабинет поставщика ---
@router.get("/supplier/dashboard")
def supplier_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Проверка роли
    if current_user.role != models.UserRole.SUPPLIER:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    # Приглашения
    invitations = db.query(models.TenderInvitation).filter(
        models.TenderInvitation.supplier_email == current_user.email
    ).all()
    # Предложения
    proposals = db.query(models.Proposal).filter(
        models.Proposal.supplier_id == current_user.id
    ).options(
        selectinload(models.Proposal.round).selectinload(models.TenderRound.tender)
    ).all()
    return templates.TemplateResponse("supplier/dashboard.html", {
        "request": request,
        "invitations": invitations,
        "proposals": proposals
    })


# --- Админка ---
@router.get("/admin/")
def admin_index(request: Request, current_user: models.User = Depends(get_current_admin)):
    return templates.TemplateResponse("admin/index.html", {"request": request})


@router.get("/admin/accreditation")
def admin_accreditation(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin)):
    companies = db.query(models.Company).filter(
        models.Company.accreditation_status.in_([models.SupplierStatus.ON_CHECK, models.SupplierStatus.DRAFT])
    ).all()
    return templates.TemplateResponse("admin/accreditation.html", {
        "request": request,
        "companies": companies
    })


@router.get("/admin/users")
def admin_users(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin)):
    users = db.query(models.User).all()
    return templates.TemplateResponse("admin/users.html", {
        "request": request,
        "users": users
    })
