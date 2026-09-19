import pytest

from pixellab_cli.errors import (
    MAX_INLINE_LENGTH,
    ConfigurationError,
    JobFailed,
    PixellabCliError,
    PollTimeout,
    ProviderError,
    RateLimited,
    ValidationError,
    redact,
)


class TestRedact:
    def test_a_short_string_survives_untouched(self):
        assert redact("a tiny knight sprite") == "a tiny knight sprite"

    def test_a_credential_is_replaced_wherever_it_appears(self):
        assert redact("Bearer sk-live-42", secrets=("sk-live-42",)) == "Bearer <redacted>"

    def test_a_credential_nested_in_a_dictionary_is_replaced(self):
        context = {"headers": {"Authorization": "Bearer sk-live-42"}}

        assert redact(context, secrets=("sk-live-42",)) == {
            "headers": {"Authorization": "Bearer <redacted>"}
        }

    def test_an_empty_secret_does_not_redact_everything(self):
        assert redact("anything", secrets=("",)) == "anything"

    def test_a_long_string_is_elided_by_length(self):
        payload = "A" * (MAX_INLINE_LENGTH + 1)

        assert redact(payload) == f"<elided {MAX_INLINE_LENGTH + 1} characters>"

    def test_a_string_exactly_at_the_limit_survives(self):
        payload = "A" * MAX_INLINE_LENGTH

        assert redact(payload) == payload

    def test_bytes_are_elided_by_length(self):
        assert redact(b"1234") == "<elided 4 bytes>"

    def test_a_list_of_payloads_is_elided_item_by_item(self):
        payloads = ["A" * (MAX_INLINE_LENGTH + 1), "small"]

        assert redact(payloads) == [f"<elided {MAX_INLINE_LENGTH + 1} characters>", "small"]

    def test_a_tuple_comes_back_as_a_list_of_redacted_items(self):
        assert redact(("small", "also small")) == ["small", "also small"]

    def test_numbers_and_booleans_pass_through(self):
        assert redact({"seed": 7, "no_background": True, "scale": 8.0}) == {
            "seed": 7,
            "no_background": True,
            "scale": 8.0,
        }


class TestErrorRendering:
    def test_a_message_without_context_renders_as_itself(self):
        assert str(PixellabCliError("nothing to say")) == "nothing to say"

    def test_context_is_rendered_after_the_message_in_a_stable_order(self):
        error = PixellabCliError("bad route", context={"route": "resize", "attempt": 2})

        assert str(error) == "bad route (attempt=2, route='resize')"

    def test_an_image_payload_in_the_context_is_elided(self):
        error = PixellabCliError("rejected", context={"image": "A" * 5000})

        assert "AAAA" not in str(error)
        assert "elided 5000 characters" in str(error)

    def test_a_credential_in_the_context_is_redacted(self):
        error = PixellabCliError(
            "rejected",
            context={"authorization": "Bearer sk-live-42"},
            secrets=("sk-live-42",),
        )

        assert "sk-live-42" not in str(error)


class TestHierarchy:
    @pytest.mark.parametrize(
        "error",
        [
            ConfigurationError("missing"),
            ValidationError("bad argument"),
            ProviderError("refused"),
            RateLimited("slow down"),
            JobFailed("failed", job_id="job-1"),
            PollTimeout("gave up", job_id="job-1", resume_command="pixellab job show job-1"),
        ],
    )
    def test_every_error_is_catchable_as_one_type(self, error):
        assert isinstance(error, PixellabCliError)

    def test_rate_limited_is_a_provider_error(self):
        assert isinstance(RateLimited("slow down"), ProviderError)

    def test_a_provider_error_keeps_the_status_it_was_given(self):
        assert ProviderError("refused", status=422).status == 422

    def test_rate_limited_keeps_the_retry_after_it_was_given(self):
        assert RateLimited("slow down", status=429, retry_after=2.5).retry_after == 2.5

    def test_a_failed_job_names_its_id_in_the_message(self):
        error = JobFailed("the model refused", job_id="job-7")

        assert error.job_id == "job-7"
        assert "job-7" in str(error)

    def test_a_poll_timeout_names_the_command_that_resumes_it(self):
        error = PollTimeout(
            "still running",
            job_id="job-7",
            resume_command="pixellab job show job-7",
        )

        assert error.resume_command == "pixellab job show job-7"
        assert "pixellab job show job-7" in str(error)


class TestTheMessageLosesItsSecrets:
    """The ledger already substitutes secrets out of a recorded error; stderr should match.

    A provider's own wording reaches PixellabCliError verbatim, and an error quoting the
    request that failed can quote a credential with it.
    """

    def test_a_credential_in_the_message_is_substituted(self):
        failure = PixellabCliError(
            "fal refused: key pl-secret-value is invalid", secrets=("pl-secret-value",)
        )

        assert "pl-secret-value" not in str(failure)
        assert "<redacted>" in str(failure)

    def test_a_long_message_keeps_its_length(self):
        # redact() elides long strings, which is right for a recorded argument and wrong
        # for a sentence somebody has to read.
        sentence = "no route can make 900x900. " + " ".join(
            f"route-{n} tops out at 512" for n in range(20)
        )

        failure = PixellabCliError(sentence)

        assert str(failure) == sentence
        assert "elided" not in str(failure)

    def test_a_message_with_no_secret_is_untouched(self):
        failure = PixellabCliError("plain trouble", secrets=("pl-secret-value",))

        assert str(failure) == "plain trouble"
