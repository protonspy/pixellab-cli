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
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from pixellab_cli.config import Credentials
from pixellab_cli.errors import ProviderError
from pixellab_cli.routes import Param, ParamKind, Route, RouteKind
from pixellab_cli.validate import build_request

QUALITY = ("auto", "low", "medium", "high", "xhigh", "max")
BACKGROUND = ("auto", "transparent", "opaque")
OUTPUT_FORMAT = ("jpeg", "png", "webp")

DOWNLOAD_TIMEOUT = 120.0

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
    # fal reports no usage on the response and this project has not confirmed a
    # price for these endpoints, so the cost of a fal call is recorded as unknown
    # rather than as a number nobody checked.
    usd: float | None = None


class FalClient:
    """Calls fal. Knows nothing about files beyond reading one and writing one."""

    def __init__(
        self,
        credentials: Credentials,
        *,
        subscribe: Callable[..., Any] | None = None,
        upload_file: Callable[[str], str] | None = None,
        http: httpx.Client | None = None,
    ) -> None:
        self._credentials = credentials
        self._subscribe = subscribe
        self._upload_file = upload_file
        self._http = http

    def upload(self, path: str | Path) -> str:
        """Put a local file on fal's CDN and return the URL a model can read."""
        self._credentials.require_fal()
        upload = self._upload_file or _default_upload
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
        self._credentials.require_fal()
        body = build_request(route, arguments)

        subscribe = self._subscribe or _default_subscribe
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
        return FalResult(
            model=route.path,
            urls=[url for url in urls if url],
            images=[self._fetch(url) for url in urls if url],
            request_id=payload.get("request_id"),
            raw=payload,
        )

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


def _default_subscribe(application: str, *, arguments: dict[str, Any]) -> Any:
    import fal_client

    return fal_client.subscribe(application, arguments=arguments)


def _default_upload(path: str) -> str:
    import fal_client

    return fal_client.upload_file(path)
