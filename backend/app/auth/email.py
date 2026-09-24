"""
Email delivery for password-reset links.

FLAGGED GAP (see implementation report): no email provider is named
anywhere in PRD.md / Architecture.md / Rules.md / Master Build. PRD
Batch B says reset happens "via email" but never specifies SMTP vs a
transactional-email API (SendGrid/SES/etc.) — this is genuinely
unspecified infrastructure, not something I'm entitled to invent per
Rules.md §1 Rule 4.

What's implemented: a swappable interface (justified the same way the
LLM Adapter's provider abstraction is justified in Rules.md §3.1 — a
second real implementation is a near-certainty, not a hypothetical).
The only concrete implementation right now is a development-only
sender that prints the reset link to the console, clearly labelled as
such. Nothing pretends to send a real email — see Rules.md §1 Rule 2
(no fake functionality shipped as if real).

Production needs an explicit decision (SMTP relay, SES, SendGrid,
Postmark, etc.) before Phase 1 can be considered feature-complete for
real users — flagged, not decided here.
"""
from typing import Protocol


class EmailSender(Protocol):
    def send_password_reset_email(self, to_email: str, reset_link: str) -> None: ...


class ConsoleDevEmailSender:
    """Development-only. Never used in production per config wiring in
    service.py — swap for a real provider there once one is chosen."""

    def send_password_reset_email(self, to_email: str, reset_link: str) -> None:
        print(
            f"[DEV EMAIL — NOT A REAL SEND] Password reset for {to_email}: "
            f"{reset_link}"
        )
