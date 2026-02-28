from fastapi import APIRouter
from celery.result import AsyncResult
from app.workers.celery_app import celery

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("/{task_id}/status")
async def task_status(task_id: str):
    task = AsyncResult(task_id, app=celery)
    return {
        "status": task.status
    }
