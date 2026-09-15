"""Credentials, and what to say when one is missing.

Two providers, two accounts, two environment variables, and no configuration file:
a token in a file is a token that gets committed. The message a missing credential
produces is part of the product — it is read by someone who does not yet know where
the value comes from, which is why the URL is in it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from pixellab_cli.errors import ConfigurationError

PIXELLAB_SECRET_VAR = "PIXELLAB_SECRET"
FAL_KEY_VAR = "FAL_KEY"

PIXELLAB_ACCOUNT_URL = "https://www.pixellab.ai/account"
FAL_KEYS_URL = "https://fal.ai/dashboard/keys"

PIXELLAB_BASE_URL = "https://api.pixellab.ai/v2"


@dataclass(frozen=True)
class Credentials:
    """Whatever credentials are present. Absence is normal; using one is not."""

    pixellab_secret: str | None = None
    fal_key: str | None = None

    @property
    def secrets(self) -> tuple[str, ...]:
        """Every credential value held, for the redaction pass in `errors.redact`."""
        return tuple(value for value in (self.pixellab_secret, self.fal_key) if value)

    def require_pixellab(self) -> str:
        if not self.pixellab_secret:
            raise ConfigurationError(
                f"{PIXELLAB_SECRET_VAR} is not set. "
                f"Get the bearer token from {PIXELLAB_ACCOUNT_URL} and export it as "
                f"{PIXELLAB_SECRET_VAR}. A browser session cookie is a different "
                f"credential and will not work here."
            )
        return self.pixellab_secret

    def require_fal(self) -> str:
        if not self.fal_key:
            raise ConfigurationError(
                f"{FAL_KEY_VAR} is not set. "
                f"Create a key at {FAL_KEYS_URL} and export it as {FAL_KEY_VAR}."
            )
        return self.fal_key


def load_credentials(environment: dict[str, str] | None = None) -> Credentials:
    """Read both credentials from the environment.

    Whitespace is stripped and an empty value is treated as absent, because
    `export PIXELLAB_SECRET=` is a far more common mistake than a token of spaces.
    """
    source = os.environ if environment is None else environment
    return Credentials(
        pixellab_secret=(source.get(PIXELLAB_SECRET_VAR) or "").strip() or None,
        fal_key=(source.get(FAL_KEY_VAR) or "").strip() or None,
    )
