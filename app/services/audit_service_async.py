from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog

async def log_audit_async(
    db: AsyncSession,
    user_id,
    action: str,
    entity: str = None,
    entity_id = None,
    ip_address: str = None
):
    log = AuditLog(
        user_id=user_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        ip_address=ip_address,
    )
    db.add(log)
    await db.flush()