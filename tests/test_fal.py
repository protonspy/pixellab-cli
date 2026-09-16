import base64

import httpx
import pytest
import respx

from pixellab_cli.config import Credentials
from pixellab_cli.errors import ConfigurationError, ProviderError, ValidationError
from pixellab_cli.fal import ALIASES, MODELS, FalClient, model

CREDENTIALS = Credentials(fal_key="fal-test-key")

CONCEPT_URL = "https://v3.fal.media/files/rabbit/concept.png"
IMAGE_BYTES = b"\x89PNG\r\n\x1a\nconcept"


def subscribe_returning(payload):
    """A stand-in for fal_client.subscribe that records what it was asked for."""
    calls = []

    def subscribe(application, *, arguments):
        calls.append((application, arguments))
        return payload

    subscribe.calls = calls
    return subscribe


class TestModelNames:
    def test_a_short_name_resolves_to_an_endpoint_id(self):
        assert model("concept").path == "openai/gpt-image-2.5/sunburst/text-to-image"

    def test_a_full_endpoint_id_resolves_to_itself(self):
        assert model("openai/gpt-image-2.5/flare/edit").path == "openai/gpt-image-2.5/flare/edit"

    def test_the_default_variant_is_sunburst(self):
        assert model("concept").path == model("sunburst").path
        assert model("edit").path == model("sunburst-edit").path

    def test_an_unknown_name_says_what_the_names_are(self):
        with pytest.raises(KeyError) as raised:
            model("dall-e")

        assert "concept" in str(raised.value)

    def test_every_alias_points_at_a_model_that_exists(self):
        for endpoint_id in ALIASES.values():
            assert endpoint_id in MODELS

    def test_an_edit_model_requires_the_images_it_edits(self):
        assert model("edit").param("image_urls").required

    def test_a_text_to_image_model_has_no_image_slot(self):
        assert model("concept").param("image_urls") is None


class TestGenerate:
    @respx.mock
    def test_the_result_comes_back_as_bytes(self):
        respx.get(CONCEPT_URL).respond(content=IMAGE_BYTES)
        client = FalClient(
            CREDENTIALS, subscribe=subscribe_returning({"images": [{"url": CONCEPT_URL}]})
        )

        result = client.generate("concept", prompt="a castle on a cliff")

        assert result.images == [IMAGE_BYTES]
        assert result.urls == [CONCEPT_URL]

    @respx.mock
    def test_the_endpoint_id_is_what_is_called(self):
        respx.get(CONCEPT_URL).respond(content=IMAGE_BYTES)
        subscribe = subscribe_returning({"images": [{"url": CONCEPT_URL}]})

        FalClient(CREDENTIALS, subscribe=subscribe).generate("flare", prompt="a castle")

        assert subscribe.calls[0][0] == "openai/gpt-image-2.5/flare/text-to-image"

    @respx.mock
    def test_arguments_reach_the_model_as_given(self):
        respx.get(CONCEPT_URL).respond(content=IMAGE_BYTES)
        subscribe = subscribe_returning({"images": [{"url": CONCEPT_URL}]})

        FalClient(CREDENTIALS, subscribe=subscribe).generate(
            "concept", prompt="a castle", quality="max", background="transparent"
        )

        _, arguments = subscribe.calls[0]
        assert arguments == {
            "prompt": "a castle",
            "quality": "max",
            "background": "transparent",
        }

    def test_an_invalid_quality_never_reaches_the_provider(self):
        subscribe = subscribe_returning({"images": []})

        with pytest.raises(ValidationError) as raised:
            FalClient(CREDENTIALS, subscribe=subscribe).generate(
                "concept", prompt="a castle", quality="ultra"
            )

        assert subscribe.calls == []
        assert "xhigh" in str(raised.value)

    def test_editing_without_images_is_rejected_before_the_call(self):
        with pytest.raises(ValidationError) as raised:
            FalClient(CREDENTIALS, subscribe=subscribe_returning({})).generate(
                "edit", prompt="give him a cape"
            )

        assert "image_urls" in str(raised.value)

    def test_a_missing_credential_is_reported_before_the_call(self):
        subscribe = subscribe_returning({"images": []})

        with pytest.raises(ConfigurationError):
            FalClient(Credentials(), subscribe=subscribe).generate("concept", prompt="a castle")

        assert subscribe.calls == []

    def test_a_provider_failure_becomes_the_shared_error_type(self):
        def subscribe(application, *, arguments):
            raise RuntimeError("queue is on fire")

        with pytest.raises(ProviderError) as raised:
            FalClient(CREDENTIALS, subscribe=subscribe).generate("concept", prompt="a castle")

        assert "queue is on fire" in str(raised.value)

    def test_the_key_is_not_echoed_into_a_failure(self):
        def subscribe(application, *, arguments):
            raise RuntimeError("rejected key fal-test-key")

        with pytest.raises(ProviderError) as raised:
            FalClient(CREDENTIALS, subscribe=subscribe).generate("concept", prompt="a castle")

        assert "fal-test-key" not in str(raised.value.context)

    def test_a_data_uri_result_is_decoded_without_a_download(self):
        encoded = base64.b64encode(IMAGE_BYTES).decode()
        payload = {"images": [{"url": f"data:image/png;base64,{encoded}"}]}

        result = FalClient(CREDENTIALS, subscribe=subscribe_returning(payload)).generate(
            "concept", prompt="a castle", sync_mode=True
        )

        assert result.images == [IMAGE_BYTES]

    @respx.mock
    def test_a_download_failure_is_reported_as_a_provider_error(self):
        respx.get(CONCEPT_URL).respond(404)
        client = FalClient(
            CREDENTIALS, subscribe=subscribe_returning({"images": [{"url": CONCEPT_URL}]})
        )

        with pytest.raises(ProviderError) as raised:
            client.generate("concept", prompt="a castle")

        assert "download" in str(raised.value)

    def test_the_cost_of_a_fal_call_is_recorded_as_unknown(self):
        result = FalClient(CREDENTIALS, subscribe=subscribe_returning({"images": []})).generate(
            "concept", prompt="a castle"
        )

        assert result.usd is None


class TestUpload:
    def test_a_local_file_becomes_a_cdn_url(self, tmp_path):
        path = tmp_path / "reference.png"
        path.write_bytes(IMAGE_BYTES)
        client = FalClient(CREDENTIALS, upload_file=lambda _: CONCEPT_URL)

        assert client.upload(path) == CONCEPT_URL

    def test_an_upload_failure_becomes_the_shared_error_type(self, tmp_path):
        def upload(_):
            raise OSError("the CDN said no")

        with pytest.raises(ProviderError) as raised:
            FalClient(CREDENTIALS, upload_file=upload).upload(tmp_path / "reference.png")

        assert "the CDN said no" in str(raised.value)

    def test_uploading_without_a_credential_is_reported(self, tmp_path):
        with pytest.raises(ConfigurationError):
            FalClient(Credentials(), upload_file=lambda _: CONCEPT_URL).upload(tmp_path / "x.png")


class TestSharedValidation:
    def test_fal_models_are_validated_by_the_same_machinery_as_pixellab_routes(self):
        # One validator, one set of error messages, whichever provider is being
        # called — that is the point of describing a fal model as a Route.
        with pytest.raises(ValidationError) as raised:
            FalClient(CREDENTIALS, subscribe=subscribe_returning({})).generate(
                "concept", prompt="a castle", num_images=99
            )

        assert "num_images" in str(raised.value)

    @respx.mock
    def test_an_injected_http_client_is_reused_for_the_download(self):
        respx.get(CONCEPT_URL).respond(content=IMAGE_BYTES)
        with httpx.Client() as http:
            client = FalClient(
                CREDENTIALS,
                subscribe=subscribe_returning({"images": [{"url": CONCEPT_URL}]}),
                http=http,
            )

            assert client.generate("concept", prompt="a castle").images == [IMAGE_BYTES]


class TestTheKeyReachesFal:
    """`require_fal` knowing the key is not the same as fal being given it.

    A key from `.pixellab.json` passed the check and then failed the call, because
    `fal_client`'s module-level helpers read `FAL_KEY` from the process environment
    and nothing else.
    """

    @pytest.fixture
    def recording_client(self, monkeypatch):
        keys = []

        class FakeSyncClient:
            def __init__(self, key=None, **_):
                keys.append(key)

            def subscribe(self, application, arguments):
                return {"images": []}

            def upload_file(self, path):
                return "https://v3.fal.media/files/rabbit/uploaded.png"

        monkeypatch.delenv("FAL_KEY", raising=False)
        monkeypatch.setattr("fal_client.SyncClient", FakeSyncClient)
        FakeSyncClient.keys = keys
        return FakeSyncClient

    def test_generating_passes_the_configured_key(self, recording_client):
        FalClient(CREDENTIALS).generate("concept", prompt="a castle")

        assert recording_client.keys == ["fal-test-key"]

    def test_uploading_passes_the_configured_key(self, recording_client, tmp_path):
        source = tmp_path / "sprite.png"
        source.write_bytes(IMAGE_BYTES)

        FalClient(CREDENTIALS).upload(source)

        assert recording_client.keys == ["fal-test-key"]

    def test_a_missing_key_is_still_refused_before_any_call(self, recording_client):
        with pytest.raises(ConfigurationError):
            FalClient(Credentials()).generate("concept", prompt="a castle")

        assert recording_client.keys == []
