import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

settings = get_settings()


def send_password_reset_email(to_email: str, reset_link: str) -> None:
    if not settings.smtp_host:
        return

    message = EmailMessage()
    message["Subject"] = "Reset your FuelBuddy password"
    message["From"] = settings.smtp_from or settings.smtp_user or "no-reply@fuelbuddy.app"
    message["To"] = to_email
    message.set_content(f"Reset your FuelBuddy password here (valid for 1 hour): {reset_link}")

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        if settings.smtp_user and settings.smtp_password:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(message)
