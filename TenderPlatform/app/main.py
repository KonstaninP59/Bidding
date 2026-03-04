from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app import models, database
from app.routers import auth, tenders, proposals, pages # Добавили pages

# Создаем таблицы
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(
    title="Tender Platform",
    description="Тендерная площадка",
    version="1.0.0"
)

# Статика
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Роутеры API (JSON)
app.include_router(auth.router)
app.include_router(tenders.router)
app.include_router(proposals.router)

# Роутеры Страниц (HTML)
app.include_router(pages.router)
