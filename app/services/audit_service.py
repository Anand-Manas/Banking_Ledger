from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog

def log_audit(db: Session, user_id, action: str, entity: str = None, entity_id = None):
    log = AuditLog(
        user_id=user_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
    )
    db.add(log)
