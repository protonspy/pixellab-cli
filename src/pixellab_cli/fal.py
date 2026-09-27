"""The fal client: concept images, box art, and heavy edits before PixelLab sees them.

`fal_client` owns the queue protocol, the CDN upload and the polling, so this wraps
it rather than reimplementing it. What is added here is the part fal does not do:
the same argument validation the PixelLab side gets, the same exception hierarchy,
and the results on disk rather than as URLs.

The two directions of travel are opposite and cannot be short-circuited. fal takes
image URLs from its CDN; PixelLab takes base64 inline. An image crossing between
them lands on disk in between — which is also where the person can look at it.
"""

from __future__ import annotations

import base64
import math
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from pixellab_cli.config import Credentials
from pixellab_cli.errors import ProviderError, ValidationError
from pixellab_cli.routes import Param, ParamKind, Route, RouteKind
from pixellab_cli.validate import build_request

QUALITY = ("auto", "low", "medium", "high", "xhigh", "max")
# The tier this tool generates at unless told otherwise, and the highest one it will
# send. fal accepts `xhigh` and `max`; they are the same picture for more money. The
# default is sent rather than omitted, because an omitted tier lets fal apply its own,
# which is `high` — so leaving it out was never neutral.
DEFAULT_QUALITY = "medium"
QUALITY_CEILING = "high"
QUALITY_OFFERED = QUALITY[: QUALITY.index(QUALITY_CEILING) + 1]


def quality_to_send(value: str | None) -> str:
    """The tier to send, refusing one above the ceiling this tool offers.

    Refusing rather than quietly lowering: a caller who asked for `max` and silently
    got `medium` would have no way to tell.
    """
    tier = value or DEFAULT_QUALITY
    if tier not in QUALITY_OFFERED:
        raise ValidationError(
            f"{tier!r} is above {QUALITY_CEILING!r}, which is as high as this tool goes. "
            f"Use one of: {', '.join(QUALITY_OFFERED)}.",
            context={"quality": tier, "ceiling": QUALITY_CEILING},
        )
    return tier


BACKGROUND = ("auto", "transparent", "opaque")
OUTPUT_FORMAT = ("jpeg", "png", "webp")

DOWNLOAD_TIMEOUT = 120.0

# What fal's own dashboard reads for the figure it shows. See `FalClient.balance`
# for why the documented billing route is not the one called.
FAL_BALANCE_URL = "https://rest.alpha.fal.ai/billing/user_balance"
# Short on purpose: this is a line beside an answer the command already has, and
# nobody should wait on it.
BALANCE_TIMEOUT = 15.0

# Shared by all four GPT Image 2.5 endpoints; the two `edit` ones add image_urls
# and mask_url. See docs/wiki/pages/gpt-image-25.md.
_COMMON = (
    Param("prompt", ParamKind.STRING, required=True, help="What to make."),
    Param("quality", ParamKind.STRING, choices=QUALITY, default="high"),
    Param("background", ParamKind.STRING, choices=BACKGROUND, default="auto"),
    Param("output_format", ParamKind.STRING, choices=OUTPUT_FORMAT, default="png"),
    Param("output_compression", ParamKind.INTEGER, minimum=0, maximum=100),
    Param("num_images", ParamKind.INTEGER, minimum=1, maximum=16, default=1),
    Param("image_size", ParamKind.OBJECT, help="A preset name, {width, height}, or 'auto'."),
    Param(
        "sync_mode",
        ParamKind.BOOLEAN,
        default=False,
        help="Return a data URI and keep the result out of fal's request history.",
    ),
)
_EDIT_ONLY = (
    Param("image_urls", ParamKind.STRING_LIST, required=True, max_items=16),
    Param("mask_url", ParamKind.STRING, help="Where the edit is allowed to apply."),
)


def _model(endpoint_id: str, *, edit: bool) -> Route:
    return Route(
        name=endpoint_id,
        method="POST",
        path=endpoint_id,
        kind=RouteKind.SYNCHRONOUS,
        summary=("Edit images" if edit else "Generate an image") + f" with {endpoint_id}.",
        params=(*_COMMON, *_EDIT_ONLY) if edit else _COMMON,
        estimated_generations=0.0,
    )


MODELS: dict[str, Route] = {
    endpoint_id: _model(endpoint_id, edit=endpoint_id.endswith("/edit"))
    for endpoint_id in (
        "openai/gpt-image-2.5/sunburst/text-to-image",
        "openai/gpt-image-2.5/sunburst/edit",
        "openai/gpt-image-2.5/flare/text-to-image",
        "openai/gpt-image-2.5/flare/edit",
    )
}

# Short names, because an agent should not have to spell an endpoint id to draw a
# picture. `sunburst` is the default variant: nothing measured here separates the
# two, and fal publishes no comparison.
ALIASES: dict[str, str] = {
    "concept": "openai/gpt-image-2.5/sunburst/text-to-image",
    "edit": "openai/gpt-image-2.5/sunburst/edit",
    "sunburst": "openai/gpt-image-2.5/sunburst/text-to-image",
    "sunburst-edit": "openai/gpt-image-2.5/sunburst/edit",
    "flare": "openai/gpt-image-2.5/flare/text-to-image",
    "flare-edit": "openai/gpt-image-2.5/flare/edit",
}


def model(name: str) -> Route:
    """Resolve a short name or a full endpoint id to a model."""
    endpoint_id = ALIASES.get(name, name)
    try:
        return MODELS[endpoint_id]
    except KeyError:
        known = ", ".join(sorted(ALIASES))
        raise KeyError(f"no fal model named {name!r}. Known names: {known}") from None


@dataclass
class FalResult:
    """What one fal call produced."""

    model: str
    images: list[bytes] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    request_id: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    # fal publishes no price for these endpoints, so the cost in money is recorded as
    # unknown rather than as a number nobody checked.
    usd: float | None = None
    # How long fal says the finished job took. Absent from the generation response,
    # present on the queue's status for a finished request, and the unit fal bills a
    # time-priced model on — so it is the one thing here that can be known.
    seconds: float | None = None


class FalClient:
    """Calls fal. Knows nothing about files beyond reading one and writing one."""

    def __init__(
        self,
        credentials: Credentials,
        *,
        subscribe: Callable[..., Any] | None = None,
        upload_file: Callable[[str], str] | None = None,
        status: Callable[..., Any] | None = None,
        http: httpx.Client | None = None,
    ) -> None:
        self._credentials = credentials
        self._subscribe = subscribe
        self._status = status
        self._upload_file = upload_file
        self._http = http

    def upload(self, path: str | Path) -> str:
        """Put a local file on fal's CDN and return the URL a model can read."""
        key = self._credentials.require_fal()
        upload = self._upload_file or _uploading_with(key)
        try:
            return upload(str(path))
        except Exception as failure:  # fal raises its own exception types
            raise ProviderError(
                f"could not upload {Path(path).name} to fal: {failure}",
                context={"path": str(path)},
                secrets=self._credentials.secrets,
            ) from failure

    def generate(self, name: str, **arguments: Any) -> FalResult:
        """Run a model to completion and return the images as bytes."""
        route = model(name)
        key = self._credentials.require_fal()
        body = build_request(route, arguments)

        subscribe = self._subscribe or _subscribing_with(key)
        try:
            payload = subscribe(route.path, arguments=body)
        except Exception as failure:  # fal raises its own exception types
            raise ProviderError(
                f"fal refused {route.path}: {failure}",
                context={"model": route.path, "arguments": body},
                secrets=self._credentials.secrets,
            ) from failure

        payload = payload if isinstance(payload, dict) else {"images": []}
        found = payload.get("images", [])
        urls = [item.get("url", "") for item in found if isinstance(item, dict)]
        request_id = payload.get("request_id")
        return FalResult(
            model=route.path,
            urls=[url for url in urls if url],
            images=[self._fetch(url) for url in urls if url],
            request_id=request_id,
            seconds=self._seconds(route.path, request_id, key),
            raw=payload,
        )

    def balance(self) -> float | None:
        """What fal says is left on the account, in USD, or None if it will not say.

        The documented route is `GET /v1/account/billing?expand=credits` on
        `api.fal.ai`, and it answers `403 authorization_error` to the key this tool
        holds: that key is API scope and billing is admin scope. Asking someone to
        mint a second, wider key so a free line can be printed is the worse trade.
        What fal's own dashboard calls takes the key we already have and answers with
        a bare number.

        Undocumented, and the host says `alpha`, so this is a ceiling rather than a
        contract — `None` on anything unexpected, and the caller says fal did not
        report rather than failing. The balance of the other provider is the answer
        this command has always given and must not be lost to this one.
        """
        key = self._credentials.fal_key
        if not key:
            return None
        try:
            if self._http is not None:
                response = self._http.get(
                    FAL_BALANCE_URL,
                    headers={"Authorization": f"Key {key}"},
                    timeout=BALANCE_TIMEOUT,
                )
            else:
                with httpx.Client(timeout=BALANCE_TIMEOUT) as client:
                    response = client.get(FAL_BALANCE_URL, headers={"Authorization": f"Key {key}"})
            response.raise_for_status()
            held = float(response.text.strip())
        except (httpx.HTTPError, ValueError):
            return None
        # `inf` and `nan` parse, and a balance printed as `$nan` is worse than one
        # not printed: it reads as a number the account actually holds.
        return held if math.isfinite(held) else None

    def _seconds(self, application: str, request_id: str | None, key: str) -> float | None:
        """How long fal says the finished job took, or None if it will not say.

        The generation response carries no usage, but the queue's status for a
        finished request carries `metrics.inference_time` — which is what fal bills a
        time-priced model on, and the only thing about one of these calls that can be
        known rather than guessed.

        Asking is free and the work is already paid for by the time we ask, so a
        failure here costs nothing and must not turn a finished generation into an
        error. The cost is recorded as unknown instead.
        """
        if not request_id:
            return None
        status = self._status or _status_with(key)
        try:
            reported = status(application, request_id)
        except Exception:  # fal raises its own exception types
            return None
        metrics = reported.get("metrics") if isinstance(reported, dict) else None
        seconds = metrics.get("inference_time") if isinstance(metrics, dict) else None
        return float(seconds) if isinstance(seconds, (int, float)) else None

    def _fetch(self, url: str) -> bytes:
        """Download one result. A data URI under `sync_mode` never leaves the process."""
        if url.startswith("data:"):
            _, _, encoded = url.partition(",")
            return base64.b64decode(encoded)
        try:
            if self._http is not None:
                return _get(self._http, url)
            with httpx.Client(timeout=DOWNLOAD_TIMEOUT) as client:
                return _get(client, url)
        except httpx.HTTPError as failure:
            raise ProviderError(
                f"could not download the fal result: {failure}",
                context={"url": url},
                secrets=self._credentials.secrets,
            ) from failure


def _get(client: httpx.Client, url: str) -> bytes:
    response = client.get(url)
    response.raise_for_status()
    return response.content


def _subscribing_with(key: str) -> Callable[..., Any]:
    """Hand fal the key we were given, rather than hoping it is in the environment.

    `fal_client`'s module-level helpers read `FAL_KEY` from the process environment
    and nothing else, so a key from `.pixellab.json` satisfied `require_fal` and then
    failed the call with "No credentials found". The client takes the key directly;
    passing it there also keeps it out of the environment a subprocess would inherit.
    """

    def subscribe(application: str, *, arguments: dict[str, Any]) -> Any:
        import fal_client

        # `subscribe` returns the model's own output, which carries no request id:
        # the id exists only for the moment the job is enqueued. Catching it there
        # and putting it where the rest of this module already looks for it is what
        # makes the finished job findable afterwards — and its timing with it.
        enqueued: list[str] = []
        payload = fal_client.SyncClient(key=key).subscribe(
            application, arguments=arguments, on_enqueue=enqueued.append
        )
        if isinstance(payload, dict) and not payload.get("request_id") and enqueued:
            payload = {**payload, "request_id": enqueued[0]}
        return payload

    return subscribe


def _status_with(key: str) -> Callable[..., Any]:
    """Read a finished request's status, which is where the timing lives."""

    def status(application: str, request_id: str) -> Any:
        import fal_client

        reported = fal_client.SyncClient(key=key).status(application, request_id)
        # The client returns a `Completed` object rather than the raw document, and
        # the timing hangs off its `metrics`. A plain mapping is what the caller reads,
        # so the one field that matters is lifted into one.
        if isinstance(reported, dict):
            return reported
        return {"metrics": getattr(reported, "metrics", None)}

    return status


def _uploading_with(key: str) -> Callable[[str], str]:
    def upload(path: str) -> str:
        import fal_client

        return fal_client.SyncClient(key=key).upload_file(path)

    return upload
