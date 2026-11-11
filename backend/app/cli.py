import argparse
import getpass

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models.user import User


def reset_password() -> None:
    email = input("Email: ").strip()
    password = getpass.getpass("New password: ")
    confirm = getpass.getpass("Confirm new password: ")
    if password != confirm:
        print("Passwords do not match.")
        return

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            print(f"No user found with email {email}")
            return
        user.password_hash = hash_password(password)
        db.commit()
        print("Password updated.")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("reset-password")
    args = parser.parse_args()

    if args.command == "reset-password":
        reset_password()


if __name__ == "__main__":
    main()
