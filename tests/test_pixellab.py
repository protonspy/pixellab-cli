"""The PixelLab client: one request, its retries, and the wait for a job.

Nothing here touches the network. Provider traffic is replayed through respx, and
the clock is a list the test reads afterwards — a retry policy tested against a real
sleep is a test nobody runs twice.
"""

import base64
import struct

import httpx
import pytest
import respx

from pixellab_cli.config import PIXELLAB_BASE_URL, Credentials
from pixellab_cli.errors import (
    JobFailed,
    PollTimeout,
    ProviderError,
    RateLimited,
    ValidationError,
)
from pixellab_cli.pixellab import (
    MAX_DOWNLOAD_BYTES,
    PixelLabClient,
    _decode_images,
    _usage,
)

CREDENTIALS = Credentials(pixellab_secret="pl-test-token")


def png_bytes(width: int = 64, height: int = 64) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", width, height)


def image_payload() -> dict:
    return {
        "type": "base64",
        "base64": base64.b64encode(png_bytes()).decode(),
        "format": "png",
    }


class Clock:
    """A sleep that records instead of waiting."""

    def __init__(self) -> None:
        self.waits: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.waits.append(seconds)

    @property
    def total(self) -> float:
        return sum(self.waits)


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def client(clock) -> PixelLabClient:
    return PixelLabClient(CREDENTIALS, sleep=clock, max_attempts=4, poll_interval=2.0)


def url(path: str) -> str:
    return f"{PIXELLAB_BASE_URL}{path}"


SPRITE_ARGS = {"description": "a knight", "image_size": {"width": 64, "height": 64}}


class TestASynchronousCall:
    @respx.mock
    def test_the_image_comes_back_decoded(self, client):
        respx.post(url("/create-image-pixflux")).respond(
            json={"image": image_payload(), "usage": {"usd": 0.008, "generations": 1.0}}
        )

        result = client.call("create-image-pixflux", **SPRITE_ARGS)

        assert result.images == [png_bytes()]

    @respx.mock
    def test_the_bearer_token_is_sent(self, client):
        route = respx.post(url("/create-image-pixflux")).respond(
            json={"image": image_payload(), "usage": {"usd": 0.008, "generations": 1.0}}
        )

        client.call("create-image-pixflux", **SPRITE_ARGS)

        assert route.calls.last.request.headers["authorization"] == "Bearer pl-test-token"

    @respx.mock
    def test_the_reported_usage_comes_back_and_is_not_an_estimate(self, client):
        respx.post(url("/create-image-pixflux")).respond(
            json={"image": image_payload(), "usage": {"usd": 0.008, "generations": 1.0}}
        )

        result = client.call("create-image-pixflux", **SPRITE_ARGS)

        assert result.usage.generations == 1.0
        assert result.usage.usd == 0.008
        assert result.usage.estimated is False

    @respx.mock
    def test_a_response_with_no_usage_falls_back_to_the_route_estimate(self, client):
        respx.post(url("/create-image-pixflux")).respond(json={"image": image_payload()})

        result = client.call("create-image-pixflux", **SPRITE_ARGS)

        assert result.usage.estimated is True
        assert result.usage.generations == 1.0

    @respx.mock
    def test_several_images_all_come_back(self, client):
        respx.post(url("/reduce-colors")).respond(
            json={"images": [image_payload(), image_payload()], "usage": {"generations": 0.1}}
        )

        result = client.call("reduce-colors", images=[image_payload()])

        assert len(result.images) == 2

    def test_an_argument_the_route_rejects_never_reaches_the_network(self, client):
        with pytest.raises(ValidationError):
            client.call("create-image-pixflux", description="a knight")

    @respx.mock
    def test_a_get_route_sends_no_body(self, client):
        route = respx.get(url("/balance")).respond(
            json={"credits": {"usd": 5.0}, "subscription": {"generations": 100}}
        )

        client.call("balance")

        assert route.calls.last.request.content == b""


class TestRetry:
    @respx.mock
    def test_a_server_error_is_retried_and_can_succeed(self, client):
        respx.post(url("/create-image-pixflux")).mock(
            side_effect=[
                httpx.Response(500),
                httpx.Response(200, json={"image": image_payload()}),
            ]
        )

        result = client.call("create-image-pixflux", **SPRITE_ARGS)

        assert result.images == [png_bytes()]

    @respx.mock
    def test_a_connection_error_is_retried(self, client):
        respx.post(url("/create-image-pixflux")).mock(
            side_effect=[
                httpx.ConnectError("no route to host"),
                httpx.Response(200, json={"image": image_payload()}),
            ]
        )

        assert client.call("create-image-pixflux", **SPRITE_ARGS).images

    @respx.mock
    def test_retries_are_bounded_and_the_last_status_is_reported(self, client):
        route = respx.post(url("/create-image-pixflux")).respond(500, text="upstream is unwell")

        with pytest.raises(ProviderError) as raised:
            client.call("create-image-pixflux", **SPRITE_ARGS)

        assert route.call_count == 4
        assert raised.value.status == 500

    @respx.mock
    def test_the_wait_grows_between_attempts(self, client, clock):
        respx.post(url("/create-image-pixflux")).respond(500)

        with pytest.raises(ProviderError):
            client.call("create-image-pixflux", **SPRITE_ARGS)

        assert len(clock.waits) == 3
        assert clock.waits == sorted(clock.waits)

    @respx.mock
    def test_a_client_error_is_not_retried(self, client):
        route = respx.post(url("/create-image-pixflux")).respond(
            422, json={"detail": "image_size too large"}
        )

        with pytest.raises(ProviderError) as raised:
            client.call("create-image-pixflux", **SPRITE_ARGS)

        assert route.call_count == 1
        assert "image_size too large" in str(raised.value)

    @respx.mock
    def test_an_unauthorized_response_says_so_plainly(self, client):
        respx.post(url("/create-image-pixflux")).respond(401)

        with pytest.raises(ProviderError) as raised:
            client.call("create-image-pixflux", **SPRITE_ARGS)

        assert raised.value.status == 401

    @respx.mock
    def test_the_token_is_not_echoed_into_the_error(self, client):
        respx.post(url("/create-image-pixflux")).respond(401)

        with pytest.raises(ProviderError) as raised:
            client.call("create-image-pixflux", **SPRITE_ARGS)

        assert "pl-test-token" not in str(raised.value)


class TestRateLimiting:
    @respx.mock
    def test_a_rate_limit_waits_for_the_interval_the_provider_names(self, client, clock):
        respx.post(url("/create-image-pixflux")).mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": "7"}),
                httpx.Response(200, json={"image": image_payload()}),
            ]
        )

        client.call("create-image-pixflux", **SPRITE_ARGS)

        assert clock.waits == [7.0]

    @respx.mock
    def test_a_rate_limit_without_a_header_backs_off(self, client, clock):
        respx.post(url("/create-image-pixflux")).mock(
            side_effect=[
                httpx.Response(529),
                httpx.Response(200, json={"image": image_payload()}),
            ]
        )

        client.call("create-image-pixflux", **SPRITE_ARGS)

        assert len(clock.waits) == 1
        assert clock.waits[0] > 0

    @respx.mock
    def test_a_persistent_rate_limit_is_reported_as_one(self, client):
        respx.post(url("/create-image-pixflux")).respond(429, headers={"Retry-After": "1"})

        with pytest.raises(RateLimited) as raised:
            client.call("create-image-pixflux", **SPRITE_ARGS)

        assert raised.value.retry_after == 1.0


class TestBackgroundJobs:
    @respx.mock
    def test_a_job_is_polled_until_it_completes(self, client):
        respx.post(url("/animate-with-text-v3")).respond(
            json={"background_job_id": "job-1", "status": "processing"}
        )
        respx.get(url("/background-jobs/job-1")).mock(
            side_effect=[
                httpx.Response(200, json={"id": "job-1", "status": "processing"}),
                httpx.Response(
                    200,
                    json={
                        "id": "job-1",
                        "status": "completed",
                        "usage": {"generations": 1.0},
                        "last_response": {"images": [image_payload()]},
                    },
                ),
            ]
        )

        result = client.call("animate-with-text-v3", first_frame=image_payload(), action="walking")

        assert result.images == [png_bytes()]

    @respx.mock
    def test_the_wait_between_polls_is_the_interval_it_was_given(self, client, clock):
        respx.post(url("/animate-with-text-v3")).respond(
            json={"background_job_id": "job-1", "status": "processing"}
        )
        respx.get(url("/background-jobs/job-1")).mock(
            side_effect=[
                httpx.Response(200, json={"status": "processing"}),
                httpx.Response(200, json={"status": "completed", "last_response": {}}),
            ]
        )

        client.call("animate-with-text-v3", first_frame=image_payload(), action="walking")

        assert clock.waits == [2.0]

    @respx.mock
    def test_a_failed_job_reports_the_provider_message_and_the_job_id(self, client):
        respx.post(url("/animate-with-text-v3")).respond(
            json={"background_job_id": "job-2", "status": "processing"}
        )
        respx.get(url("/background-jobs/job-2")).respond(
            json={"status": "failed", "last_response": {"error": "the model refused"}}
        )

        with pytest.raises(JobFailed) as raised:
            client.call("animate-with-text-v3", first_frame=image_payload(), action="walking")

        assert raised.value.job_id == "job-2"
        assert "the model refused" in str(raised.value)

    @respx.mock
    def test_polling_stops_at_the_bound_and_says_how_to_collect_the_result(self, clock):
        client = PixelLabClient(CREDENTIALS, sleep=clock, poll_interval=2.0, max_poll_seconds=6.0)
        respx.post(url("/animate-with-text-v3")).respond(
            json={"background_job_id": "job-3", "status": "processing"}
        )
        respx.get(url("/background-jobs/job-3")).respond(json={"status": "processing"})

        with pytest.raises(PollTimeout) as raised:
            client.call("animate-with-text-v3", first_frame=image_payload(), action="walking")

        assert raised.value.job_id == "job-3"
        assert "job-3" in raised.value.resume_command
        assert clock.total <= 6.0

    @respx.mock
    def test_a_resource_route_is_polled_on_its_own_path(self, client):
        respx.post(url("/create-tileset")).respond(
            json={"tileset_id": "ts-1", "background_job_id": "job-4", "status": "processing"}
        )
        respx.get(url("/tilesets/ts-1")).respond(
            json={"status": "completed", "images": [image_payload()]}
        )

        result = client.call("create-tileset", lower_description="grass", upper_description="sand")

        assert result.images == [png_bytes()]

    @respx.mock
    def test_the_durable_asset_id_is_returned_alongside_the_result(self, client):
        respx.post(url("/create-character-v3")).respond(
            json={"character_id": "char-9", "background_job_id": "job-5", "status": "processing"}
        )
        respx.get(url("/background-jobs/job-5")).respond(
            json={"status": "completed", "last_response": {"images": [image_payload()]}}
        )

        result = client.call("create-character-v3", description="a knight")

        assert result.ids["character_id"] == "char-9"

    @respx.mock
    def test_a_job_can_be_left_running_instead_of_waited_on(self, client):
        respx.post(url("/create-character-v3")).respond(
            json={"character_id": "char-9", "background_job_id": "job-6", "status": "processing"}
        )

        result = client.call("create-character-v3", description="a knight", wait=False)

        assert result.job_id == "job-6"
        assert result.images == []


class TestAResponseThatSaysHowManyFramesItHas:
    """A template-driven animation returns six frames in `quantized_images` and two
    in `images`. Reading `images` alone collected two of six: the animation looked
    complete and was not.
    """

    def payload(self, **overrides):
        defaults = {
            "frame_count": 6,
            "images": [image_payload(), image_payload()],
            "quantized_images": [image_payload() for _ in range(6)],
        }
        return {**defaults, **overrides}

    def test_the_declared_count_wins_over_a_short_list(self):
        assert len(_decode_images(self.payload())) == 6

    def test_a_list_that_matches_the_count_is_left_alone(self):
        payload = self.payload(images=[image_payload() for _ in range(6)])

        assert len(_decode_images(payload)) == 6

    def test_a_response_with_no_count_is_read_as_before(self):
        payload = {"images": [image_payload(), image_payload()]}

        assert len(_decode_images(payload)) == 2

    def test_a_longer_list_is_not_substituted_for_a_complete_one(self):
        """Only a list that matches the declared count replaces what was found;
        anything else would be guessing which set is the real one."""
        payload = self.payload(quantized_images=[image_payload() for _ in range(9)])

        assert len(_decode_images(payload)) == 2

    def test_the_reported_seconds_reach_the_usage(self):
        """A route priced by time reports it, and dropping it left an animation that
        ran for thirty-six minutes recorded as costing nothing."""
        usage = _usage({"usage": {"seconds": 2174.5, "usd": 0.2466}})

        assert usage is not None
        assert usage.seconds == 2174.5
        assert usage.usd == 0.2466

    def test_a_usage_without_seconds_leaves_them_unset(self):
        usage = _usage({"usage": {"usd": 0.01}})

        assert usage is not None
        assert usage.seconds is None


class TestAJobThatReturnsAnAddressRatherThanBytes:
    """R4.9. `create-ui-asset` completes into `/ui-assets/{id}`, whose payload carries
    `image_url` and no base64 at all — a real one, read off the account:

        {"id": "43d70268-…", "status": "completed",
         "image_url": "https://backblaze.pixellab.ai/file/…/full.png?v=1789936808"}

    Thirty generations were charged for a panel that was never collected."""

    PANEL_URL = "https://backblaze.pixellab.ai/file/pixellab-characters/ui/x/y/full.png?v=1"

    def a_completed_panel(self):
        respx.post(url("/create-ui-asset")).respond(
            json={"ui_asset_id": "ui-1", "background_job_id": "job-1", "status": "processing"}
        )
        respx.get(url("/ui-assets/ui-1")).respond(
            json={
                "id": "ui-1",
                "status": "completed",
                "size": {"width": 192, "height": 192},
                "image_url": self.PANEL_URL,
            }
        )

    @respx.mock
    def test_the_image_is_fetched_from_the_address(self, client):
        self.a_completed_panel()
        respx.get(self.PANEL_URL).respond(content=png_bytes())

        result = client.call("create-ui-asset", description="a wooden panel")

        assert result.images == [png_bytes()]

    @respx.mock
    def test_the_address_is_fetched_without_the_bearer_token(self, client):
        """These links carry their own access in the identifier, like a rotation URL."""
        self.a_completed_panel()
        asset = respx.get(self.PANEL_URL).respond(content=png_bytes())

        client.call("create-ui-asset", description="a wooden panel")

        assert "authorization" not in asset.calls.last.request.headers

    @respx.mock
    def test_bytes_in_the_payload_are_still_preferred(self, client):
        """A payload carrying both is not fetched twice: the bytes are already here."""
        respx.post(url("/create-ui-asset")).respond(
            json={"ui_asset_id": "ui-1", "background_job_id": "job-1", "status": "processing"}
        )
        respx.get(url("/ui-assets/ui-1")).respond(
            json={"status": "completed", "images": [image_payload()], "image_url": self.PANEL_URL}
        )
        asset = respx.get(self.PANEL_URL).respond(content=png_bytes())

        result = client.call("create-ui-asset", description="a wooden panel")

        assert result.images == [png_bytes()]
        assert not asset.called


class TestCollectingAJobThatReturnsAnAddress:
    """R4.9 through the resume path. `create-ui-asset` can time out, and what it tells
    the caller to run is `pixellab-cli job show <id>` — which collects by id alone. A
    charged panel must not be lost one hop later than the one this fix closed."""

    PANEL_URL = "https://backblaze.pixellab.ai/file/pixellab-characters/ui/x/y/full.png?v=1"

    @respx.mock
    def test_the_image_is_fetched_from_the_address(self, client):
        job = "5bf5ee44-06e1-4a6f-9e5a-1e0e5ef0a6d1"
        respx.get(url(f"/background-jobs/{job}")).respond(
            json={"status": "completed", "last_response": {"image_url": self.PANEL_URL}}
        )
        respx.get(self.PANEL_URL).respond(content=png_bytes())

        result = client.collect(job)

        assert result.images == [png_bytes()]


class TestAnIdentifierThatWouldLeaveItsPath:
    """A path parameter is interpolated into the URL, and the request carries the
    bearer token — so a dot segment or a separator in one is a URL of somebody else's
    choosing, reached with this caller's credential. `collect` already refuses it for a
    job id; every path parameter is refused the same way, before anything is sent."""

    @pytest.mark.parametrize(
        "identifier",
        ["../characters/char-9", "ui-1/../../balance", "a\\b", "..", "ui-1/extra"],
    )
    @respx.mock
    def test_it_is_refused_before_the_request(self, client, identifier):
        route = respx.get(url(f"/ui-assets/{identifier}"))

        with pytest.raises(ValidationError):
            client.call("ui-asset", ui_asset_id=identifier)

        assert not route.called

    @respx.mock
    def test_an_ordinary_identifier_still_goes_through(self, client):
        respx.get(url("/ui-assets/ui-1")).respond(json={"id": "ui-1", "status": "completed"})

        result = client.call("ui-asset", ui_asset_id="ui-1")

        assert result.raw["id"] == "ui-1"


class TestWhatADownloadWillHold:
    """The address is the provider's and is fetched without anybody asking, so how
    much is read is not the provider's decision to make."""

    ADDRESS = "https://backblaze.pixellab.ai/file/pixellab-characters/ui/x/y/full.png"

    @respx.mock
    def test_a_body_past_the_ceiling_is_refused(self, client):
        respx.get(self.ADDRESS).respond(content=b"x" * (MAX_DOWNLOAD_BYTES + 1))

        with pytest.raises(ProviderError) as refused:
            client.download(self.ADDRESS)

        assert "ceiling" in str(refused.value)

    @respx.mock
    def test_a_declared_length_past_the_ceiling_is_refused_as_well(self, client):
        respx.get(self.ADDRESS).respond(
            content=b"x", headers={"Content-Length": str(MAX_DOWNLOAD_BYTES + 1)}
        )

        with pytest.raises(ProviderError):
            client.download(self.ADDRESS)

    @respx.mock
    def test_an_ordinary_asset_comes_through(self, client):
        respx.get(self.ADDRESS).respond(content=png_bytes())

        assert client.download(self.ADDRESS) == png_bytes()


class TestAJobIdInsideAListOfObjects:
    """R4.10. `objects/{id}/animations` answers with `submissions`: one object per
    direction, each carrying its own job. The first is followed, exactly as the flat
    list of a character animation is."""

    def a_submission(self, direction, job):
        return {"direction": direction, "status": "processing", "background_job_id": job}

    @respx.mock
    def test_the_first_submission_is_the_job_that_is_polled(self, client):
        respx.post(url("/objects/obj-1/animations")).respond(
            json={
                "animation_group_id": "group-1",
                "object_id": "obj-1",
                "description": "it turns on the spot",
                "mode": "v3",
                "frame_count": 8,
                "submissions": [
                    self.a_submission("south", "job-south"),
                    self.a_submission("east", "job-east"),
                ],
            }
        )
        polled = respx.get(url("/background-jobs/job-south")).respond(
            json={"status": "completed", "last_response": {"images": [image_payload()]}}
        )

        result = client.call(
            "object-animations", object_id="obj-1", animation_description="it turns"
        )

        assert polled.called
        assert result.images == [png_bytes()]

    @respx.mock
    def test_a_submission_with_no_job_is_not_polled_as_one(self, client):
        """`background_job_id` is nullable, and a dictionary is not a job id."""
        respx.post(url("/objects/obj-1/animations")).respond(
            json={
                "animation_group_id": "group-1",
                "object_id": "obj-1",
                "description": "it turns",
                "mode": "v3",
                "frame_count": 8,
                "submissions": [{"direction": "south", "status": "failed"}],
            }
        )

        with pytest.raises(ProviderError):
            client.call("object-animations", object_id="obj-1", animation_description="it turns")


class TestAJobIdTheProviderChose:
    """R3.6 on the other half of the same problem. The identifier a response hands
    back is interpolated into the poll path, and the request that follows carries the
    bearer token — a response is not more trustworthy than an argument here."""

    @respx.mock
    def test_a_job_id_carrying_a_path_is_refused_before_it_is_polled(self, client):
        respx.post(url("/objects/obj-1/animations")).respond(
            json={
                "animation_group_id": "group-1",
                "object_id": "obj-1",
                "description": "it turns",
                "mode": "v3",
                "frame_count": 8,
                "submissions": [
                    {
                        "direction": "south",
                        "status": "processing",
                        "background_job_id": "../../v2/characters",
                    }
                ],
            }
        )
        elsewhere = respx.get(url("/characters"))

        with pytest.raises(ValidationError):
            client.call("object-animations", object_id="obj-1", animation_description="it turns")

        assert not elsewhere.called

    @respx.mock
    def test_the_flat_list_of_a_character_animation_is_guarded_too(self, client):
        """`characters/animations` returns its ids one layer shallower; one rule."""
        respx.post(url("/characters/animations")).respond(
            json={"background_job_ids": ["../../v2/balance"], "status": "processing"}
        )

        with pytest.raises(ValidationError):
            client.call("characters-animations", character_id="char-9", action_description="walk")
