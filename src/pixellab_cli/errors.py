"""The exception hierarchy, and the redaction every exception passes through.

Errors here are read by two audiences that want the same thing: a person at a
terminal, and an agent deciding what to do next. Both need the provider's own
wording — a paraphrase of a 422 is a paraphrase of the only useful sentence — and
neither may ever be handed a credential.

Redaction is applied once, where the arguments are attached to the exception, rather
than at each raise site. A raise site added six months from now would not remember.
"""

from __future__ import annotations

from typing import Any

# Anything longer than this in a request is an encoded image, not a description.
# Image payloads are the bulk of a PixelLab request and are worthless in an error.
MAX_INLINE_LENGTH = 256


def redact(value: Any, secrets: tuple[str, ...] = ()) -> Any:
    """Return `value` with credentials removed and long payloads elided.

    Recurses through dictionaries, lists and tuples. Strings are elided by length
    rather than by key name, so a new image parameter is covered the day it is added
    instead of the day someone remembers to list it.
    """
    if isinstance(value, str):
        for secret in secrets:
            if secret and secret in value:
                value = value.replace(secret, "<redacted>")
        if len(value) > MAX_INLINE_LENGTH:
            return f"<elided {len(value)} characters>"
        return value
    if isinstance(value, dict):
        return {key: redact(item, secrets) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(item, secrets) for item in value]
    if isinstance(value, (bytes, bytearray)):
        return f"<elided {len(value)} bytes>"
    return value


class PixellabCliError(Exception):
    """Base for everything this tool raises on purpose.

    Carries an optional `context` dictionary — the arguments, the route, the job id —
    which is redacted on the way in and rendered after the message.
    """

    def __init__(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
        secrets: tuple[str, ...] = (),
    ) -> None:
        super().__init__(message)
        self.message = message
        self.context: dict[str, Any] = redact(context or {}, secrets)

    def __str__(self) -> str:
        if not self.context:
            return self.message
        detail = ", ".join(f"{key}={value!r}" for key, value in sorted(self.context.items()))
        return f"{self.message} ({detail})"


class ConfigurationError(PixellabCliError):
    """A credential or setting the tool needs is missing or unusable."""


class ValidationError(PixellabCliError):
    """An argument the route rejects, caught before the request is sent."""


class ProviderError(PixellabCliError):
    """The provider refused the request, and the retries are spent."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        context: dict[str, Any] | None = None,
        secrets: tuple[str, ...] = (),
    ) -> None:
        super().__init__(message, context=context, secrets=secrets)
        self.status = status


class RateLimited(ProviderError):
    """429 or 529, still refused after backing off.

    PixelLab publishes no endpoint reporting the account's concurrency limit, so this
    is the only way the ceiling is ever observed.
    """

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        retry_after: float | None = None,
        context: dict[str, Any] | None = None,
        secrets: tuple[str, ...] = (),
    ) -> None:
        super().__init__(message, status=status, context=context, secrets=secrets)
        self.retry_after = retry_after


class JobFailed(ProviderError):
    """A background job resolved to `failed`. It was charged anyway."""

    def __init__(
        self,
        message: str,
        *,
        job_id: str,
        context: dict[str, Any] | None = None,
        secrets: tuple[str, ...] = (),
    ) -> None:
        super().__init__(message, context={"job_id": job_id, **(context or {})}, secrets=secrets)
        self.job_id = job_id


class PollTimeout(PixellabCliError):
    """Polling stopped before the job resolved.

    This is not a failure of the generation: the job may still be running and has
    already been paid for. The message carries what is needed to collect it later.
    """

    def __init__(
        self,
        message: str,
        *,
        job_id: str,
        resume_command: str,
        context: dict[str, Any] | None = None,
        secrets: tuple[str, ...] = (),
    ) -> None:
        super().__init__(
            message,
            context={"job_id": job_id, "resume": resume_command, **(context or {})},
            secrets=secrets,
        )
        self.job_id = job_id
        self.resume_command = resume_command
