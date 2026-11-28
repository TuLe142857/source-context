from app.core.config import Settings

from .base import BaseMailClient
from .smtp_mail import SmtpMailClient


def get_mail_client(config: Settings) -> BaseMailClient:
    return SmtpMailClient(
        host=config.SMTP_SERVER,
        port=config.SMTP_PORT,
        send_mail_from=config.SMTP_SEND_MAIL_FROM,
        user=config.SMTP_USER,
        password=config.SMTP_PASSWORD.get_secret_value(),
        use_tls=config.SMTP_USE_TLS,
    )
