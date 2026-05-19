import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)


def _build_otp_html(code: str) -> str:
    """Build a professional HTML email template for OTP delivery."""
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background-color:#f4f4f7;font-family:Arial,Helvetica,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f4f7;padding:40px 0;">
    <tr>
      <td align="center">
        <table role="presentation" width="480" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
          <!-- Header -->
          <tr>
            <td style="background-color:#4f46e5;padding:28px 32px;text-align:center;">
              <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:600;">{settings.PROJECT_NAME}</h1>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding:36px 32px 24px;">
              <p style="margin:0 0 16px;color:#333333;font-size:16px;line-height:1.5;">
                Hello,
              </p>
              <p style="margin:0 0 24px;color:#333333;font-size:16px;line-height:1.5;">
                Use the verification code below to complete your sign-in. This code is valid for <strong>{settings.OTP_EXPIRE_MINUTES} minutes</strong>.
              </p>
              <!-- OTP Code -->
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center" style="padding:16px 0 28px;">
                    <div style="display:inline-block;background-color:#f0f0ff;border:2px dashed #4f46e5;border-radius:8px;padding:16px 40px;">
                      <span style="font-size:32px;font-weight:700;letter-spacing:8px;color:#4f46e5;font-family:'Courier New',monospace;">{code}</span>
                    </div>
                  </td>
                </tr>
              </table>
              <p style="margin:0 0 8px;color:#666666;font-size:14px;line-height:1.5;">
                If you did not request this code, you can safely ignore this email. Someone may have entered your email address by mistake.
              </p>
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="padding:20px 32px;background-color:#f9fafb;border-top:1px solid #e5e7eb;">
              <p style="margin:0;color:#9ca3af;font-size:12px;text-align:center;line-height:1.5;">
                &copy; {settings.PROJECT_NAME}. This is an automated message, please do not reply.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _build_otp_plain(code: str) -> str:
    """Build a plain-text fallback for the OTP email."""
    return (
        f"Your {settings.PROJECT_NAME} verification code is: {code}\n\n"
        f"This code is valid for {settings.OTP_EXPIRE_MINUTES} minutes.\n\n"
        f"If you did not request this code, please ignore this email."
    )


def send_email_otp(email: str, code: str) -> dict:
    """
    Sends an OTP to the specified email address using SMTP.
    Uses MIME multipart (HTML + plain text) to reduce spam classification.
    """
    try:
        sender = settings.SMTP_FROM or settings.SMTP_USER

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Your verification code for {settings.PROJECT_NAME}"
        msg["From"] = f"{settings.PROJECT_NAME} <{sender}>"
        msg["To"] = email
        msg["Reply-To"] = sender
        msg["X-Mailer"] = settings.PROJECT_NAME

        # Attach plain text first, then HTML (email clients prefer the last part)
        msg.attach(MIMEText(_build_otp_plain(code), "plain", "utf-8"))
        msg.attach(MIMEText(_build_otp_html(code), "html", "utf-8"))

        # Connect and send
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
            "provider": "smtp",
        }
    except Exception as e:
        logger.error(f"Failed to send email OTP to {email}: {str(e)}")
        return {
            "status": "failed",
            "error": str(e),
            "destination": email,
        }
