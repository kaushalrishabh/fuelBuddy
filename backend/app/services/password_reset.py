import datetime as dt
import hashlib
import secrets

from sqlalchemy.orm import Session

from app.models.password_reset_token import PasswordResetToken
from app.models.user import User

TOKEN_TTL = dt.timedelta(hours=1)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _naive_utc_now() -> dt.datetime:
    # MySQL's DATETIME has no timezone concept, so everything stored/compared
    # here is naive UTC rather than tz-aware.
    return dt.datetime.now(dt.UTC).replace(tzinfo=None)


def create_reset_token(db: Session, user: User) -> str:
    raw_token = secrets.token_urlsafe(32)
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=_hash_token(raw_token),
            expires_at=_naive_utc_now() + TOKEN_TTL,
        )
    )
    db.commit()
    return raw_token


def consume_reset_token(db: Session, raw_token: str, new_password_hash: str) -> bool:
    token_hash = _hash_token(raw_token)
    record = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == token_hash, PasswordResetToken.used.is_(False))
        .first()
    )
    if record is None or record.expires_at < _naive_utc_now():
        return False

    user = db.get(User, record.user_id)
    if user is None:
        return False

    user.password_hash = new_password_hash
    record.used = True
    db.commit()
    return True
