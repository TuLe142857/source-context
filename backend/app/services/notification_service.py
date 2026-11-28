from typing import Annotated

from fastapi import Depends

from app.core.config import get_settings
from app.core.templating import TemplateRenderer, get_template_renderer
from app.integrations.mail import BaseMailClient, get_mail_client


class NotificationService:
    """Send user-facing notifications by purpose.

    Callers say what to notify (e.g. a registration OTP); this service picks
    the template, subject and context, renders it and sends it. Sending is
    blocking, so async callers should run it in a background task or a thread.
    """

    def __init__(self, mail_client: BaseMailClient, renderer: TemplateRenderer) -> None:
        self.mail_client = mail_client
        self.renderer = renderer

    def send_registration_otp(self, to: str, otp: str, expire_minutes: int) -> None:
        """Email a registration OTP.

        Args:
            to: recipient email
            otp: plain OTP code
            expire_minutes: minutes until the OTP expires, shown in the email

        Raises:
            MailError: the mail provider failed to send.
        """
        html = self.renderer.render(
            "registration_otp",
            {"otp_code": otp, "expire_minutes": expire_minutes},
        )
        self.mail_client.send(
            to=to,
            subject="Verify your Source Context account",
            html=html,
        )


def get_notification_service() -> NotificationService:
    return NotificationService(
        mail_client=get_mail_client(get_settings()),
        renderer=get_template_renderer(),
    )


NotificationServiceDep = Annotated[
    NotificationService, Depends(get_notification_service)
]
