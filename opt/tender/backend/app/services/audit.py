from app.models.audit_log import AuditLog


async def log_action(db, user_id: int, action: str, details: dict):
    audit = AuditLog(
        user_id=user_id,
        action=action,
        details=details,
    )
    db.add(audit)
