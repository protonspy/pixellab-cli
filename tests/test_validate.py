"""The gate between an argument and a paid call.

Every test here describes money not spent: a 422 from PixelLab is cheap on its own,
but a 422 on step four of a recipe has three paid steps behind it.
"""

import pytest

from pixellab_cli import catalog
from pixellab_cli.errors import ValidationError
from pixellab_cli.images import EncodedImage
from pixellab_cli.routes import (
    OUTLINE,
    Param,
    ParamKind,
    Route,
    RouteKind,
    SizeLimit,
)
from pixellab_cli.validate import build_request

PIXFLUX = Route(
    name="create-image-pixflux",
    method="POST",
    path="/create-image-pixflux",
    kind=RouteKind.SYNCHRONOUS,
    params=(
        Param("description", ParamKind.STRING, required=True),
        Param(
            "image_size",
            ParamKind.SIZE,
            required=True,
            size=SizeLimit(min_area=32 * 32, max_area=400 * 400),
        ),
        Param("outline", ParamKind.STRING, choices=OUTLINE),
        Param("text_guidance_scale", ParamKind.NUMBER, default=8.0),
        Param("seed", ParamKind.INTEGER, minimum=0),
        Param("no_background", ParamKind.BOOLEAN, default=False),
    ),
)

PIXEN = Route(
    name="create-image-pixen",
    method="POST",
    path="/create-image-pixen",
    kind=RouteKind.SYNCHRONOUS,
    params=(
        Param("description", ParamKind.STRING, required=True),
        Param(
            "image_size",
            ParamKind.SIZE,
            required=True,
            size=SizeLimit(min_side=16, max_area=512 * 512, divisible_by=4, square_below=32),
        ),
    ),
)

ANIMATE = Route(
    name="animate-with-text-v3",
    method="POST",
    path="/animate-with-text-v3",
    kind=RouteKind.BACKGROUND_JOB,
    params=(
        Param("first_frame", ParamKind.IMAGE, required=True, size=SizeLimit(max_side=256)),
        Param("action", ParamKind.STRING, required=True),
        Param("frame_count", ParamKind.INTEGER, minimum=4, maximum=16, default=8),
        Param("directions", ParamKind.STRING_LIST, max_items=8),
    ),
    result_id_field="background_job_id",
    poll_path="/background-jobs/{id}",
)


class TestRequiredAndUnknown:
    def test_a_valid_request_passes_through_with_its_arguments(self):
        body = build_request(
            PIXFLUX, {"description": "a knight", "image_size": {"width": 64, "height": 64}}
        )

        assert body["description"] == "a knight"
        assert body["image_size"] == {"width": 64, "height": 64}

    def test_a_missing_required_parameter_is_named(self):
        with pytest.raises(ValidationError) as raised:
            build_request(PIXFLUX, {"description": "a knight"})

        assert "image_size" in str(raised.value)

    def test_an_unknown_parameter_is_named_alongside_what_the_route_accepts(self):
        with pytest.raises(ValidationError) as raised:
            build_request(
                PIXFLUX,
                {
                    "description": "a knight",
                    "image_size": {"width": 64, "height": 64},
                    "shading": "flat shading",
                },
            )

        message = str(raised.value)
        assert "shading" in message
        assert "outline" in message

    def test_a_parameter_left_out_is_simply_absent_rather_than_sent_as_none(self):
        body = build_request(
            PIXFLUX, {"description": "a knight", "image_size": {"width": 64, "height": 64}}
        )

        assert "seed" not in body
        assert "outline" not in body

    def test_an_explicit_none_is_treated_as_absent(self):
        body = build_request(
            PIXFLUX,
            {"description": "a knight", "image_size": {"width": 64, "height": 64}, "seed": None},
        )

        assert "seed" not in body


class TestChoices:
    def test_a_value_outside_an_enumerated_set_is_rejected(self):
        with pytest.raises(ValidationError) as raised:
            build_request(
                PIXFLUX,
                {
                    "description": "a knight",
                    "image_size": {"width": 64, "height": 64},
                    "outline": "black outline",
                },
            )

        assert "outline" in str(raised.value)

    def test_the_rejection_lists_the_values_that_would_have_worked(self):
        with pytest.raises(ValidationError) as raised:
            build_request(
                PIXFLUX,
                {
                    "description": "a knight",
                    "image_size": {"width": 64, "height": 64},
                    "outline": "black outline",
                },
            )

        assert "single color black outline" in str(raised.value)

    def test_a_value_inside_the_set_is_accepted(self):
        body = build_request(
            PIXFLUX,
            {
                "description": "a knight",
                "image_size": {"width": 64, "height": 64},
                "outline": "lineless",
            },
        )

        assert body["outline"] == "lineless"


class TestNumbers:
    def test_a_value_below_the_minimum_is_rejected(self):
        with pytest.raises(ValidationError) as raised:
            build_request(ANIMATE, {"first_frame": {}, "action": "walking", "frame_count": 2})

        assert "frame_count" in str(raised.value)

    def test_a_value_above_the_maximum_is_rejected(self):
        with pytest.raises(ValidationError) as raised:
            build_request(ANIMATE, {"first_frame": {}, "action": "walking", "frame_count": 32})

        assert "frame_count" in str(raised.value)

    def test_a_value_at_the_boundary_is_accepted(self):
        body = build_request(ANIMATE, {"first_frame": {}, "action": "walking", "frame_count": 16})

        assert body["frame_count"] == 16

    def test_a_string_where_a_number_belongs_is_rejected(self):
        with pytest.raises(ValidationError) as raised:
            build_request(ANIMATE, {"first_frame": {}, "action": "walking", "frame_count": "eight"})

        assert "frame_count" in str(raised.value)

    def test_a_boolean_is_not_accepted_as_an_integer(self):
        # bool is an int in Python and False would sail through as 0 frames.
        with pytest.raises(ValidationError):
            build_request(ANIMATE, {"first_frame": {}, "action": "walking", "frame_count": True})


class TestSizes:
    def test_an_area_above_the_maximum_is_rejected(self):
        with pytest.raises(ValidationError) as raised:
            build_request(
                PIXFLUX, {"description": "a knight", "image_size": {"width": 512, "height": 512}}
            )

        assert "image_size" in str(raised.value)

    def test_the_rejection_describes_the_bounds_that_would_have_worked(self):
        with pytest.raises(ValidationError) as raised:
            build_request(
                PIXFLUX, {"description": "a knight", "image_size": {"width": 512, "height": 512}}
            )

        assert "160000" in str(raised.value)

    def test_an_area_below_the_minimum_is_rejected(self):
        with pytest.raises(ValidationError):
            build_request(
                PIXFLUX, {"description": "a knight", "image_size": {"width": 16, "height": 16}}
            )

    def test_a_side_below_the_minimum_is_rejected(self):
        with pytest.raises(ValidationError):
            build_request(
                PIXEN, {"description": "a knight", "image_size": {"width": 8, "height": 8}}
            )

    def test_a_side_not_divisible_by_the_step_is_rejected(self):
        with pytest.raises(ValidationError) as raised:
            build_request(
                PIXEN, {"description": "a knight", "image_size": {"width": 66, "height": 64}}
            )

        assert "divisible by 4" in str(raised.value)

    def test_a_non_square_below_the_square_threshold_is_rejected(self):
        with pytest.raises(ValidationError) as raised:
            build_request(
                PIXEN, {"description": "a knight", "image_size": {"width": 24, "height": 32}}
            )

        assert "square" in str(raised.value)

    def test_a_square_below_the_threshold_is_accepted(self):
        body = build_request(
            PIXEN, {"description": "a knight", "image_size": {"width": 24, "height": 24}}
        )

        assert body["image_size"] == {"width": 24, "height": 24}

    def test_a_size_that_is_not_a_width_and_height_pair_is_rejected(self):
        with pytest.raises(ValidationError) as raised:
            build_request(PIXFLUX, {"description": "a knight", "image_size": 64})

        assert "image_size" in str(raised.value)

    def test_a_size_with_a_non_integer_side_is_rejected(self):
        with pytest.raises(ValidationError):
            build_request(
                PIXFLUX, {"description": "a knight", "image_size": {"width": 64.5, "height": 64}}
            )


class TestImages:
    def test_an_image_within_the_side_limit_is_accepted(self):
        body = build_request(
            ANIMATE, {"first_frame": {"width": 256, "height": 256}, "action": "walking"}
        )

        assert body["first_frame"] == {"width": 256, "height": 256}

    def test_an_image_over_the_side_limit_is_rejected_before_it_is_uploaded(self):
        with pytest.raises(ValidationError) as raised:
            build_request(
                ANIMATE, {"first_frame": {"width": 512, "height": 512}, "action": "walking"}
            )

        assert "first_frame" in str(raised.value)

    def test_an_image_whose_dimensions_are_unknown_is_passed_through(self):
        # An already-encoded payload carries no dimensions; the route will judge it.
        body = build_request(ANIMATE, {"first_frame": {"base64": "..."}, "action": "walking"})

        assert body["first_frame"] == {"base64": "..."}


class TestLists:
    def test_a_list_within_the_item_limit_is_accepted(self):
        body = build_request(
            ANIMATE,
            {"first_frame": {}, "action": "walking", "directions": ["south", "north"]},
        )

        assert body["directions"] == ["south", "north"]

    def test_a_list_over_the_item_limit_is_rejected(self):
        with pytest.raises(ValidationError) as raised:
            build_request(
                ANIMATE,
                {"first_frame": {}, "action": "walking", "directions": ["south"] * 9},
            )

        assert "directions" in str(raised.value)

    def test_a_bare_string_where_a_list_belongs_is_rejected(self):
        with pytest.raises(ValidationError):
            build_request(ANIMATE, {"first_frame": {}, "action": "walking", "directions": "south"})


class TestRedaction:
    def test_a_rejection_does_not_echo_an_encoded_payload_back(self):
        with pytest.raises(ValidationError) as raised:
            build_request(
                ANIMATE,
                {"first_frame": {"base64": "A" * 5000}, "action": "walking", "frame_count": 3},
            )

        assert "AAAA" not in str(raised.value)


FRAMES = Route(
    name="transfer-outfit-v2",
    method="POST",
    path="/transfer-outfit-v2",
    kind=RouteKind.BACKGROUND_JOB,
    result_id_field="background_job_id",
    poll_path="/background-jobs/{id}",
    params=(
        Param(
            "frames",
            ParamKind.IMAGE_LIST,
            required=True,
            min_items=2,
            max_items=16,
            size=SizeLimit(max_side=256),
        ),
    ),
)


def _frame(width: int, height: int) -> dict:
    """A frame in the shape this route takes it: the size beside the image, not on it."""
    return {"image": {"base64": "AAAA"}, "size": {"width": width, "height": height}}


class TestAListOfImages:
    def test_a_list_below_the_floor_is_rejected(self):
        with pytest.raises(ValidationError) as raised:
            build_request(FRAMES, {"frames": [_frame(64, 64)]})

        assert "at least 2" in str(raised.value)

    def test_a_list_over_the_ceiling_is_rejected(self):
        with pytest.raises(ValidationError) as raised:
            build_request(FRAMES, {"frames": [_frame(64, 64)] * 17})

        assert "at most 16" in str(raised.value)

    def test_one_oversized_frame_is_rejected_although_the_others_fit(self):
        with pytest.raises(ValidationError) as raised:
            build_request(FRAMES, {"frames": [_frame(64, 64), _frame(300, 64)]})

        assert "300x64" in str(raised.value)

    def test_a_list_within_both_bounds_is_accepted(self):
        body = build_request(FRAMES, {"frames": [_frame(64, 64), _frame(64, 64)]})

        assert len(body["frames"]) == 2

    def test_a_frame_whose_size_is_unreadable_is_left_to_the_route(self):
        body = build_request(FRAMES, {"frames": [{"base64": "AAAA"}, {"base64": "BBBB"}]})

        assert len(body["frames"]) == 2


class TestAnEncodedImageIsMeasured:
    """A limit that only binds when the caller happens to keep the dimensions is not
    a limit. `EncodedImage` carries the size read out of the file; `as_payload` drops
    it, so a caller that serialised first handed over an image nothing could judge.
    """

    ROUTE = catalog.route("create-character-v3")

    def encoded(self, width: int, height: int) -> EncodedImage:
        return EncodedImage(base64="ZmFrZQ==", format="png", width=width, height=height)

    def test_a_reference_over_the_limit_is_refused(self):
        with pytest.raises(ValidationError) as refusal:
            build_request(
                self.ROUTE,
                {"description": "a knight", "reference_image": self.encoded(384, 384)},
            )

        assert "384x384" in str(refusal.value)

    def test_a_reference_within_the_limit_is_sent_as_the_payload(self):
        body = build_request(
            self.ROUTE,
            {"description": "a knight", "reference_image": self.encoded(256, 256)},
        )

        assert body["reference_image"] == {"type": "base64", "base64": "ZmFrZQ==", "format": "png"}

    def test_an_image_whose_size_could_not_be_read_is_still_sent(self):
        body = build_request(
            self.ROUTE,
            {"description": "a knight", "reference_image": EncodedImage(base64="ZmFrZQ==")},
        )

        assert body["reference_image"]["base64"] == "ZmFrZQ=="


class TestAStyleImageMatchesTheOutput:
    """Bitforge renders the style image at the output size and refuses a mismatch
    with a 500 — which is charged, like every other failed generation.
    """

    ROUTE = catalog.route("create-image-bitforge")

    def request(self, style: EncodedImage, width: int = 128, height: int = 128):
        return build_request(
            self.ROUTE,
            {
                "description": "a knight",
                "image_size": {"width": width, "height": height},
                "style_image": style,
            },
        )

    def test_a_mismatched_style_image_is_refused(self):
        with pytest.raises(ValidationError) as refusal:
            self.request(EncodedImage(base64="ZmFrZQ==", width=270, height=265))

        assert "270x265" in str(refusal.value)
        assert "128x128" in str(refusal.value)

    def test_a_matching_style_image_is_accepted(self):
        body = self.request(EncodedImage(base64="ZmFrZQ==", width=128, height=128))

        assert body["style_image"]["base64"] == "ZmFrZQ=="

    def test_a_style_image_of_unknown_size_is_left_to_the_route(self):
        body = self.request(EncodedImage(base64="ZmFrZQ=="))

        assert body["style_image"]["base64"] == "ZmFrZQ=="


class TestAnEnumeratedListChecksEachItem:
    """R3.3. A list parameter enumerates what each item may be, not what the whole
    list may be — `directions=["north"]` is one allowed value, not an unknown one."""

    def test_a_list_of_allowed_values_passes(self):
        route = catalog.route("object-animations")

        body = build_request(route, {"object_id": "obj-1", "directions": ["north", "south"]})

        assert body["directions"] == ["north", "south"]

    def test_one_item_outside_the_set_is_refused_and_named(self):
        route = catalog.route("object-animations")

        with pytest.raises(ValidationError) as refused:
            build_request(route, {"object_id": "obj-1", "directions": ["north", "sideways"]})

        assert "sideways" in str(refused.value)
