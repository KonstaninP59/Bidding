from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app import models
from app.database import engine
from app.routers import (
    auth, pages, proposals, tenders, invitations,
    admin, rounds, evaluation, qna, 
    # reports
)

# Создание таблиц (для разработки)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Tender Platform", description="Тендерная площадка", version="1.0.0")

# CORS
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
app.include_router(pages.router)
app.include_router(tenders.router)
app.include_router(proposals.router)
app.include_router(invitations.router)
app.include_router(admin.router)
app.include_router(rounds.router)
app.include_router(evaluation.router)
app.include_router(qna.router)
# app.include_router(reports.router)
