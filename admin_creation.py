import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.models.user import User
from app.models.user_role import UserRole
from app.core.security import hash_password

def create_default_admin():
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == "admin").first()
        if existing:
            print(f"Admin already exists: {existing.username}")
            return

        admin_password = os.getenv("ADMIN_PASSWORD")
        if not admin_password:
            admin_password = input("Set admin password: ")

        admin = User(
            username="admin",
            password_hash=hash_password(admin_password),
            status="ACTIVE",
        )
        db.add(admin)
        db.flush()

        db.add(UserRole(user_id=admin.user_id, role="ADMIN"))
        db.commit()
        print(f"Admin created successfully: admin")
    except Exception as e:
        db.rollback()
        print(f"Error creating admin: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_default_admin()
