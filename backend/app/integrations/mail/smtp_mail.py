import smtplib
from email.message import EmailMessage

from .base import BaseMailClient


class SmtpMailClient(BaseMailClient):

    def __init__(
        self,
        host: str,
        port: int,
        send_mail_from: str,
        user: str,
        password: str,
        use_tls: bool = False,
        timeout: float = 30.0,
    ):
        """

        Args:
            host: mail server host
            port: mail server port
            send_mail_from: email sender address
            user: email or username to login mail server. In most case user is send_mail_from
            password: password to login mail server
            use_tls: upgrade the connection with STARTTLS before login
            timeout: socket timeout in seconds
        """
        super().__init__(send_mail_from=send_mail_from)
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.use_tls = use_tls
        self.timeout = timeout

    def _send(
        self,
        *,
        to: str,
        subject: str,
        plain: str | None,
        html: str | None,
    ) -> None:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.send_mail_from
        msg["To"] = to

        if plain is not None:
            msg.set_content(plain)
        if html is not None:
            if plain is not None:
                msg.add_alternative(html, subtype="html")
            else:
                msg.set_content(html, subtype="html")

        with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as server:
            if self.use_tls:
                server.starttls()
            server.login(self.user, self.password)
            server.send_message(msg)
