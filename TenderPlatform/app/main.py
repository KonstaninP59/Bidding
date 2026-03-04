from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app import models, database
from app.routers import auth, tenders, proposals, pages

# Создаем таблицы (для разработки; в production использовать alembic)
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(
    title="Tender Platform",
    description="Тендерная площадка",
    version="1.0.0"
)

# CORS для разработки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Статика
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Роутеры
app.include_router(auth.router)
app.include_router(tenders.router)
app.include_router(proposals.router)
app.include_router(pages.router)
