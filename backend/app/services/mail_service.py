from fastapi import Depends
from typing import Annotated
import smtplib
from email.message import EmailMessage
from app.core.config import get_settings
from .template_service import TemplateService, TemplateServiceDep


class MailService:
    def __init__(
        self,
        template_service: TemplateService,
        host: str,
        port: int,
        send_mail_from: str,
        user: str,
        password: str,
        use_tls: bool = False,
    ):
        """

        Args:
            host: mail server host
            port: mail server port
            send_mail_from: email sender address
            user: email or username to login mail server. In most case user is mail_send_from,
            password: password to login mail server
            use_tls:
            template_service: template service to render HTML content
        """
        self.host = host
        self.port = port
        self.send_mail_from = send_mail_from
        self.user = user
        self.password = password
        self.use_tls = use_tls
        self.template_service = template_service

    def send_email(
        self,
        to: str,
        subject: str,
        plain_content: str | None = None,
        html_content: str | None = None,
    ):
        if (plain_content is None) and (html_content is None):
            raise ValueError("Either plain_content or html_content must be provided")

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.send_mail_from
        msg["To"] = to

        if plain_content is not None:
            msg.set_content(plain_content)
        if html_content is not None:
            msg.add_alternative(html_content, subtype="html")

        with smtplib.SMTP(self.host, self.port) as mail_server:
            if self.use_tls:
                mail_server.starttls()
            mail_server.login(self.user, self.password)
            mail_server.sendmail(self.send_mail_from, to, msg.as_string())

    def send_template_email(
        self,
        to: str,
        subject: str,
        template_name: str,
        context: dict | None = None,
        plain_content: str | None = None,
    ):
        html_content = self.template_service.render(
            template_name=template_name, context=context
        )
        self.send_email(
            to=to,
            subject=subject,
            plain_content=plain_content,
            html_content=html_content,
        )


def get_mail_service(template_service: TemplateServiceDep) -> MailService:
    settings = get_settings()
    return MailService(
        template_service=template_service,
        host=settings.SMTP_SERVER,
        port=settings.SMTP_PORT,
        send_mail_from=settings.SMTP_SEND_MAIL_FROM,
        user=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD.get_secret_value(),
        use_tls=settings.SMTP_USE_TLS,
    )


MailServiceDep = Annotated[MailService, Depends(get_mail_service)]
