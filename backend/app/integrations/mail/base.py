from abc import ABC, abstractmethod

from .exception import MailError


class BaseMailClient(ABC):
    def __init__(self, send_mail_from: str):
        self._send_mail_from = send_mail_from

    @property
    def send_mail_from(self) -> str:
        """Sender address"""
        return self._send_mail_from

    def send(
        self,
        to: str,
        subject: str,
        plain: str | None = None,
        html: str | None = None,
    ) -> None:
        """Send one email. At least one of `plain` or `html` is required.

        Raises:
            ValueError: Neither `plain` nor `html` was given.
            MailError: The provider call failed.
        """
        if plain is None and html is None:
            raise ValueError("Either plain or html must be provided")

        try:
            self._send(to=to, subject=subject, plain=plain, html=html)
        except MailError:
            raise
        except Exception as exc:
            raise MailError(
                f"Send mail to {to} failed: "
                f"{exc.__class__.__name__}: {exc}"
            ) from exc

    @abstractmethod
    def _send(
        self,
        *,
        to: str,
        subject: str,
        plain: str | None,
        html: str | None,
    ) -> None:
        """Send one request to the provider. Use send() instead."""
