from app.workers.celery_app import celery
from app.services.report_service import (
    generate_pdf,
    generate_xlsx,
    build_snapshot
)
from app.core.database import async_session_factory
from app.models.report import Report
import asyncio
import os


REPORT_DIR = "/opt/tender/media/reports"


@celery.task(bind=True)
def generate_pdf_report(self, request_id: int, round_id: int, user_id: int):
    async def _run():
        async with async_session_factory() as db:
            snapshot = await build_snapshot(db, request_id, round_id)

            file_path = generate_pdf(snapshot)

            report = Report(
                request_id=request_id,
                round_id=round_id,
                file_type="PDF",
                file_path=file_path,
                snapshot_data=snapshot,
                created_by=user_id,
            )

            db.add(report)
            await db.commit()

    asyncio.run(_run())


@celery.task(bind=True)
def generate_xlsx_report(self, request_id: int, round_id: int, user_id: int):
    async def _run():
        async with async_session_factory() as db:
            snapshot = await build_snapshot(db, request_id, round_id)

            file_path = generate_xlsx(snapshot)

            report = Report(
                request_id=request_id,
                round_id=round_id,
                file_type="XLSX",
                file_path=file_path,
                snapshot_data=snapshot,
                created_by=user_id,
            )

            db.add(report)
            await db.commit()

    asyncio.run(_run())
