class MailError(Exception):
    """A mail provider call failed (connection, auth, rejected recipient)."""
