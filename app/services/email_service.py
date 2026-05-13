import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger(__name__)

def send_email_otp(email: str, code: str) -> dict:
    """
    Sends an OTP to the specified email address using SMTP.
    """
    try:
        msg = EmailMessage()
        msg.set_content(f"Your verification code is: {code}\n\nThis code will expire in {settings.OTP_EXPIRE_MINUTES} minutes.")
        msg['Subject'] = f"{code} is your {settings.PROJECT_NAME} verification code"
        msg['From'] = settings.SMTP_FROM or settings.SMTP_USER
        msg['To'] = email

        # Connect to the SMTP server and send the email
        # We use SMTP_SSL for port 465, or SMTP with starttls for port 587
        if settings.SMTP_PORT == 465:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
                smtp.starttls()
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                smtp.send_message(msg)

        logger.info(f"Successfully sent OTP to {email}")
        return {
            "status": "sent",
            "destination": email,
            "provider": "smtp"
        }
    except Exception as e:
        logger.error(f"Failed to send email OTP to {email}: {str(e)}")
        # In development, we might still want to return a 'sent' status or at least log the code
        return {
            "status": "failed",
            "error": str(e),
            "destination": email
        }
