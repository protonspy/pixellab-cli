"""The PixelLab client: one request, its retries, and the wait for a job.

One retry policy for every route, and one polling loop for the two polling shapes,
because a policy per route is a policy nobody can reason about. What varies per
route is data in the catalogue, not code here.
"""

from __future__ import annotations

import random
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import httpx

from pixellab_cli import catalog, images
from pixellab_cli.config import PIXELLAB_BASE_URL, Credentials
from pixellab_cli.errors import (
    JobFailed,
    PollTimeout,
    ProviderError,
    RateLimited,
    ValidationError,
)
from pixellab_cli.routes import Route, RouteKind
from pixellab_cli.validate import build_request

# A synchronous generation route holds the connection open while it generates, so
# its timeout is measured in minutes; everything else should answer at once.
REQUEST_TIMEOUT = 30.0
# How much of a provider-named URL is read before it is refused. Well above any
# asset this tool makes, and well below what would hurt to hold in memory.
MAX_DOWNLOAD_BYTES = 64 * 1024 * 1024

GENERATION_TIMEOUT = 300.0

DEFAULT_MAX_ATTEMPTS = 4
DEFAULT_BACKOFF = 1.0
DEFAULT_POLL_INTERVAL = 3.0
DEFAULT_MAX_POLL_SECONDS = 900.0

RETRY_STATUSES = frozenset({429, 500, 502, 503, 504, 529})
RATE_LIMIT_STATUSES = frozenset({429, 529})


@dataclass(frozen=True)
class Usage:
    """What a call cost. `estimated` says whether the provider or the table said so.

    `seconds` is reported by the routes priced by time, and dropping it left an
    animation that ran for thirty-six minutes recorded as costing nothing.
    """

    generations: float = 0.0
    usd: float = 0.0
    estimated: bool = False
    seconds: float | None = None


@dataclass
class Result:
    """Everything one call produced."""

    route: str
    images: list[bytes] = field(default_factory=list)
    ids: dict[str, str] = field(default_factory=dict)
    usage: Usage = field(default_factory=Usage)
    job_id: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class PixelLabClient:
    """Calls PixelLab REST v2. Knows nothing about files, commands or the ledger."""

    def __init__(
        self,
        credentials: Credentials,
        *,
        base_url: str = PIXELLAB_BASE_URL,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        backoff: float = DEFAULT_BACKOFF,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        max_poll_seconds: float = DEFAULT_MAX_POLL_SECONDS,
    ) -> None:
        self._credentials = credentials
        self._base_url = base_url.rstrip("/")
        self._client = client
        self._sleep = sleep
        self._max_attempts = max_attempts
        self._backoff = backoff
        self._poll_interval = poll_interval
        self._max_poll_seconds = max_poll_seconds

    # ------------------------------------------------------------------ calling

    def call(self, route_name: str, *, wait: bool = True, **arguments: Any) -> Result:
        """Run a route end to end: validate, send, and wait for the result.

        `wait=False` submits and returns the job id without polling — for a batch
        that puts several jobs in flight before collecting any of them.
        """
        route = catalog.route(route_name)
        body = build_request(route, arguments)
        path, body = _split_path(route, body)

        if route.returns_bytes:
            return Result(route=route.name, images=[self._fetch(f"{self._base_url}{path}")])

        payload = self._request(route.method, path, body, route=route)

        result = Result(route=route.name, raw=payload)
        self._collect_ids(route, payload, result)
        self._collect_usage(route, payload, result)

        if route.kind is RouteKind.SYNCHRONOUS:
            result.images = _decode_images(payload)
            return result

        result.job_id = _poll_id(route, payload)
        if not wait:
            return result
        return self._await(route, result)

    def download(self, url: str) -> bytes:
        """Fetch a generated asset from the URL PixelLab returned.

        These links are unauthenticated: the unguessable identifier in them is the
        access key. They are treated as intentional share links — fetched without a
        bearer token, recorded in the manifest, and not committed anywhere.
        """
        return self._fetch(url, authenticated=False)

    def _fetch(self, url: str, *, authenticated: bool = True) -> bytes:
        headers = (
            {"Authorization": f"Bearer {self._credentials.require_pixellab()}"}
            if authenticated
            else {}
        )
        try:
            if self._client is not None:
                response = self._client.get(url, headers=headers, timeout=GENERATION_TIMEOUT)
            else:
                with httpx.Client(timeout=GENERATION_TIMEOUT) as client:
                    response = client.get(url, headers=headers)
            response.raise_for_status()
            return self._within_the_ceiling(response, url)
        except httpx.HTTPError as failure:
            raise ProviderError(
                f"could not download from PixelLab: {failure}",
                context={"url": url},
                secrets=self._credentials.secrets,
            ) from failure

    def _within_the_ceiling(self, response: httpx.Response, url: str) -> bytes:
        """The body, refused rather than held where it is larger than any asset here.

        The address comes from the provider's response and is fetched without anybody
        asking, so how much is read must not be the provider's decision. The ceiling
        is far above every asset this tool generates — a spritesheet ZIP of eight
        directions is orders below it — so reaching it means something is wrong
        rather than something is large.
        """
        declared = response.headers.get("Content-Length")
        try:
            if declared is not None and int(declared) > MAX_DOWNLOAD_BYTES:
                raise ProviderError(
                    f"refused a {int(declared)} byte download: nothing here is that "
                    f"large, and the ceiling is {MAX_DOWNLOAD_BYTES}",
                    context={"url": url, "bytes": int(declared)},
                    secrets=self._credentials.secrets,
                )
        except ValueError:
            pass
        body = response.content
        if len(body) > MAX_DOWNLOAD_BYTES:
            raise ProviderError(
                f"refused a {len(body)} byte download: nothing here is that large, "
                f"and the ceiling is {MAX_DOWNLOAD_BYTES}",
                context={"url": url, "bytes": len(body)},
                secrets=self._credentials.secrets,
            )
        return body

    # ------------------------------------------------------------------ requests

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None,
        *,
        route: Route | None = None,
    ) -> dict[str, Any]:
        token = self._credentials.require_pixellab()
        timeout = (
            GENERATION_TIMEOUT
            if route is not None and route.kind is RouteKind.SYNCHRONOUS and method == "POST"
            else REQUEST_TIMEOUT
        )
        url = f"{self._base_url}{path}"
        headers = {"Authorization": f"Bearer {token}"}
        context = {"route": route.name if route else path, "arguments": body}

        last: ProviderError | None = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                response = self._send(method, url, headers, body, timeout)
            except httpx.HTTPError as failure:
                last = ProviderError(
                    f"could not reach PixelLab: {failure}",
                    context=context,
                    secrets=self._credentials.secrets,
                )
                self._wait_before_retry(attempt, None)
                continue

            if response.status_code < 400:
                return _json(response)

            last = self._failure(response, context)
            if response.status_code not in RETRY_STATUSES:
                raise last
            if attempt == self._max_attempts:
                break
            self._wait_before_retry(attempt, _retry_after(response))

        raise last if last else ProviderError("PixelLab could not be reached", context=context)

    def _send(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: dict[str, Any] | None,
        timeout: float,
    ) -> httpx.Response:
        request_body = body if method != "GET" and body else None
        if self._client is not None:
            return self._client.request(
                method, url, headers=headers, json=request_body, timeout=timeout
            )
        with httpx.Client(timeout=timeout) as client:
            return client.request(method, url, headers=headers, json=request_body)

    def _failure(self, response: httpx.Response, context: dict[str, Any]) -> ProviderError:
        detail = _detail(response)
        message = f"PixelLab returned {response.status_code}: {detail}"
        if response.status_code in RATE_LIMIT_STATUSES:
            return RateLimited(
                message,
                status=response.status_code,
                retry_after=_retry_after(response),
                context=context,
                secrets=self._credentials.secrets,
            )
        return ProviderError(
            message,
            status=response.status_code,
            context=context,
            secrets=self._credentials.secrets,
        )

    def _wait_before_retry(self, attempt: int, retry_after: float | None) -> None:
        if retry_after is not None:
            self._sleep(retry_after)
            return
        # Exponential, with jitter, so a batch that hits the ceiling together does
        # not come back together.
        delay = self._backoff * (2 ** (attempt - 1))
        self._sleep(delay + random.random() * self._backoff)

    # ------------------------------------------------------------------- polling

    def _await(self, route: Route, result: Result) -> Result:
        job_id = result.job_id
        if not job_id:
            raise ProviderError(
                f"{route.name} returned no {route.result_id_field} to poll",
                context={"route": route.name},
                secrets=self._credentials.secrets,
            )
        payload = self._poll(job_id, route.poll_path or "", route.name)
        result = _complete(route, payload, result)
        if not result.images:
            # `create-ui-asset` completes into `/ui-assets/{id}`, which carries the
            # panel's address and no bytes anywhere — so the decoder found nothing and
            # a call charged at thirty generations wrote no image. Fetched here rather
            # than in the decoder, which is a function over a payload and has no
            # client. Only `image_url`, and only because a real payload was seen
            # holding it: the same rule the decoder states for `quantized_images`.
            result.images = [self.download(address) for address in _image_urls(payload)]
        return result

    def collect(self, job_id: str) -> Result:
        """Wait for a background job named by its id alone, and return what it made.

        The polling above belongs to a call in flight and knows its route. This does
        not: a job id is all that survives a `PollTimeout`, and the work behind it was
        charged whether or not anybody was still waiting.
        """
        # The id goes into a URL path, and dot segments in it are normalised against
        # the whole URL: `../../v2/characters` reaches another endpoint on the host,
        # carrying this caller's bearer token. Every id the provider issues is a
        # UUID, so anything else is refused rather than escaped and sent anyway.
        try:
            uuid.UUID(job_id)
        except (ValueError, AttributeError, TypeError):
            raise ValidationError(
                f"{job_id!r} is not a job id; they are UUIDs",
                context={"job": job_id},
            ) from None

        payload = self._poll(job_id, catalog.BACKGROUND_JOBS_PATH, f"job {job_id}")
        body = payload.get("last_response") or payload
        result = Result(route="background-job", job_id=job_id, raw=payload)
        result.images = _decode_images(body) or [
            # The same address the waited-for path fetches. This is the path a
            # `create-ui-asset` that outran the wait is *told* to use, so a panel
            # already charged for must not be lost one hop later.
            self.download(address)
            for address in _image_urls(body)
        ]
        result.usage = _usage(payload) or _usage(body) or Usage(estimated=True)
        # The same provenance the ordinary path keeps. A collected job knowing less
        # about itself than a waited-for one is drift, not a decision.
        for key, value in body.items():
            if key.endswith("_id") and isinstance(value, str):
                result.ids[key] = value
        return result

    def _poll(self, job_id: str, poll_path: str, subject: str) -> dict[str, Any]:
        """Wait for one background job and return its completed payload.

        One loop for both callers. They were two, and had already drifted: the one
        that collected a job by id dropped the identifiers the other kept, and said
        nothing about the call having been charged.
        """
        _refuse_a_path_of_its_own("job", job_id, subject)
        path = poll_path.replace("{id}", job_id)
        waited = 0.0
        while True:
            payload = self._request("GET", path, None)
            status = str(payload.get("status", "")).lower()
            if status == "completed":
                return payload
            if status == "failed":
                raise JobFailed(
                    f"{subject} failed: {_job_error(payload)}",
                    job_id=job_id,
                    context={"job": job_id},
                )
            if waited + self._poll_interval > self._max_poll_seconds:
                raise PollTimeout(
                    f"{subject} was still running after {waited:.0f}s. "
                    f"It has been charged either way.",
                    job_id=job_id,
                    resume_command=f"pixellab-cli job show {job_id}",
                    context={"job": job_id},
                )
            self._sleep(self._poll_interval)
            waited += self._poll_interval

    # ------------------------------------------------------------------ results

    def _collect_ids(self, route: Route, payload: dict[str, Any], result: Result) -> None:
        for field_name in (route.asset_id_field, route.result_id_field):
            value = payload.get(field_name) if field_name else None
            if isinstance(value, str):
                result.ids[field_name] = value

    def _collect_usage(self, route: Route, payload: dict[str, Any], result: Result) -> None:
        result.usage = _usage(payload) or Usage(
            generations=route.estimated_generations, estimated=True
        )


def _complete(route: Route, payload: dict[str, Any], result: Result) -> Result:
    """Fold a completed job's payload into the result built from the submit call."""
    body = payload.get("last_response") or payload
    result.images = _decode_images(body)
    reported = _usage(payload) or _usage(body)
    if reported is not None:
        result.usage = reported
    for key, value in body.items():
        if key.endswith("_id") and isinstance(value, str):
            result.ids.setdefault(key, value)
    result.raw = payload
    return result


def _image_urls(payload: dict[str, Any]) -> list[str]:
    """The addresses a completed job gives instead of bytes, if it gives any."""
    body = payload.get("last_response") or payload
    address = body.get("image_url")
    return [address] if isinstance(address, str) and address else []


def _decode_images(payload: dict[str, Any]) -> list[bytes]:
    """Every image in a response, whether it arrived as `image` or as `images`.

    A response that says how many frames it has is believed. A template-driven
    animation returns six frames in `quantized_images` and two in `images`, so
    reading `images` alone silently collected two of six — the animation looked
    complete and was not, which is the failure this whole module is written against.
    """
    found: list[Any] = []
    single = payload.get("image")
    if single:
        found.append(single)
    many = payload.get("images")
    if isinstance(many, list):
        found.extend(many)

    declared = payload.get("frame_count")
    if isinstance(declared, int) and declared > len(found):
        # Only `quantized_images`, and only because a real payload was seen holding
        # it. `frames` is the other field that carries a frame per entry, and the
        # vendored schema says those are public URLs — base64-decoding one raises,
        # and a URL that happened to survive padding would be written as a PNG of
        # nothing. A field is read when it has been seen, not when it sounds right.
        for field_name in ("quantized_images",):
            complete = payload.get(field_name)
            if isinstance(complete, list) and len(complete) == declared:
                found = list(complete)
                break
    return [images.decode(item) for item in found]


def _usage(payload: dict[str, Any]) -> Usage | None:
    reported = payload.get("usage")
    if not isinstance(reported, dict):
        return None
    seconds = reported.get("seconds")
    return Usage(
        generations=float(reported.get("generations") or 0.0),
        usd=float(reported.get("usd") or 0.0),
        estimated=False,
        seconds=float(seconds) if isinstance(seconds, (int, float)) else None,
    )


def _poll_id(route: Route, payload: dict[str, Any]) -> str | None:
    value = payload.get(route.result_id_field) if route.result_id_field else None
    if isinstance(value, str):
        return value
    # `characters/animations` returns one job per direction; the first is the one to
    # follow, and the rest are recorded in the raw payload.
    if isinstance(value, list) and value:
        first = value[0]
        # `objects/{id}/animations` reports the same thing one layer in: `submissions`
        # holds an object per direction, each with its own job. Which identifier is
        # followed is this module's rule, not the route's shape, so it is one rule.
        if isinstance(first, dict):
            nested = first.get("background_job_id")
            return str(nested) if isinstance(nested, str) else None
        return str(first)
    return None


# What may not appear in a value that becomes part of a URL path. A separator opens a
# segment of somebody else's choosing and a dot segment climbs out of the one this
# route owns — either way the request still carries the bearer token, so the check is
# here, at the one place every path parameter passes through, rather than at each
# caller that remembers to make it.
PATH_SEPARATORS = ("/", "\\")


def _refuse_a_path_of_its_own(name: str, value: str, route: str) -> None:
    """Refuse a value that would take the URL somewhere the route did not name.

    Used for both halves of the same problem: a path parameter the caller supplied,
    and the job identifier the *provider* supplied, which is interpolated into the
    poll path by the very next request — and that request carries the bearer token.
    A response is not more trustworthy than an argument here; it is the same URL.
    """
    if any(mark in value for mark in PATH_SEPARATORS) or ".." in value:
        raise ValidationError(
            f"{name} is part of the address this is sent to, so it carries no path "
            f"of its own: {value!r}",
            context={"route": route, name: value},
        )


def _split_path(route: Route, body: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Move the path parameters out of the body and into the URL."""
    if not route.path_params:
        return route.path, body
    remaining = dict(body)
    values = {name: remaining.pop(name, "") for name in route.path_params}
    for name, value in values.items():
        _refuse_a_path_of_its_own(name, str(value), route.name)
    return route.path.format(**values), remaining


def _retry_after(response: httpx.Response) -> float | None:
    raw = response.headers.get("Retry-After")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _json(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {"result": payload}


def _detail(response: httpx.Response) -> str:
    """The provider's own words, which are the only useful part of a 4xx."""
    try:
        payload = response.json()
    except ValueError:
        return (response.text or "no detail").strip()[:500]
    if isinstance(payload, dict):
        detail = payload.get("detail") or payload.get("message") or payload
        return str(detail)[:500]
    return str(payload)[:500]


def _job_error(payload: dict[str, Any]) -> str:
    body = payload.get("last_response")
    if isinstance(body, dict):
        for key in ("error", "detail", "message"):
            if body.get(key):
                return str(body[key])
    return str(payload.get("error") or payload.get("detail") or "no reason given")
