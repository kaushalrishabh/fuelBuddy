from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.user import User
from app.models.vehicle import Vehicle

settings = get_settings()


def seed_admin_user(db: Session) -> None:
    if not settings.admin_email or not settings.admin_password:
        return
    if db.query(User).first() is not None:
        return

    user = User(email=settings.admin_email, password_hash=hash_password(settings.admin_password))
    db.add(user)
    db.flush()

    vehicle = Vehicle(
        user_id=user.id,
        name="Royal Enfield Classic 350",
        make="Royal Enfield",
        model="Classic 350",
        is_default=True,
    )
    db.add(vehicle)
    db.commit()
