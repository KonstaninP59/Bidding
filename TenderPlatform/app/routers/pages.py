from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app import models, database

router = APIRouter(tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Главная страница
@router.get("/")
def page_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Страница входа
@router.get("/login")
def page_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Страница регистрации
@router.get("/register")
def page_register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

# Список тендеров
@router.get("/tenders-list")
def page_tenders_list(request: Request, db: Session = Depends(get_db)):
    # Получаем все тендеры (в реальном проекте тут нужна пагинация)
    tenders = db.query(models.Tender).filter(models.Tender.status == models.TenderStatus.PUBLISHED).all()
    return templates.TemplateResponse("tenders_list.html", {"request": request, "tenders": tenders})

# Детальная страница тендера
@router.get("/tender/{tender_id}")
def page_tender_detail(tender_id: int, request: Request, db: Session = Depends(get_db)):
    tender = db.query(models.Tender).filter(models.Tender.id == tender_id).first()
    
    # Находим активный раунд
    active_round = None
    for r in tender.rounds:
        if r.status == models.RoundStatus.ACTIVE:
            active_round = r
            break
            
    # Если активного нет, берем первый запланированный или последний завершенный
    if not active_round and tender.rounds:
        active_round = tender.rounds[0]

    return templates.TemplateResponse("tender_detail.html", {
        "request": request, 
        "tender": tender,
        "active_round": active_round
    })
