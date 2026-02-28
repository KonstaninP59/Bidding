from fastapi import APIRouter, Depends
from app.workers.report_tasks import (
    generate_pdf_report,
    generate_xlsx_report
)
from app.api.v1.deps import require_permissions

router = APIRouter(prefix="/requests", tags=["Reports"])


@router.post("/{request_id}/generate-pdf")
async def generate_pdf_endpoint(
    request_id: int,
    round_id: int,
    user=Depends(require_permissions(["generate_reports"]))
):
    task = generate_pdf_report.delay(request_id, round_id, user.id)
    return {"task_id": task.id}


@router.post("/{request_id}/generate-xlsx")
async def generate_xlsx_endpoint(
    request_id: int,
    round_id: int,
    user=Depends(require_permissions(["generate_reports"]))
):
    task = generate_xlsx_report.delay(request_id, round_id, user.id)
    return {"task_id": task.id}
