from fastapi import APIRouter, Request, Depends, Query
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, selectinload
from app import models, database
from app.dependencies import get_db

router = APIRouter(tags=["Pages"])
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
    # Пагинация
    offset = (page - 1) * per_page
    tenders = db.query(models.Tender).filter(
        models.Tender.status == models.TenderStatus.PUBLISHED
    ).order_by(models.Tender.created_at.desc()).offset(offset).limit(per_page).all()
    
    # Общее количество для пагинации
    total = db.query(models.Tender).filter(models.Tender.status == models.TenderStatus.PUBLISHED).count()
    
    return templates.TemplateResponse("tenders_list.html", {
        "request": request,
        "tenders": tenders,
        "page": page,
        "per_page": per_page,
        "total": total
    })

@router.get("/tender/{tender_id}")
def page_tender_detail(tender_id: int, request: Request, db: Session = Depends(get_db)):
    # Загружаем тендер со связанными данными
    tender = db.query(models.Tender).options(
        selectinload(models.Tender.items),
        selectinload(models.Tender.criteria),
        selectinload(models.Tender.rounds)
    ).filter(models.Tender.id == tender_id).first()
    
    if not tender:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    
    # Находим активный раунд
    active_round = None
    for r in tender.rounds:
        if r.status == models.RoundStatus.ACTIVE:
            active_round = r
            break
    if not active_round and tender.rounds:
        active_round = tender.rounds[-1]  # последний по номеру

    return templates.TemplateResponse("tender_detail.html", {
        "request": request,
        "tender": tender,
        "active_round": active_round
    })
