"""Which animation route a frame count reaches.

Two routes animate a loose frame and they do not overlap where it matters:
`animate-with-text-v3` stops at sixteen frames, `animate-pixminimax` reaches forty
and is priced by generation time. Sending twenty frames to the first is a rejection;
sending eight to the second is paying a beta route for what the cheap one does.
"""

import pytest

from pixellab_cli.commands.motion import check_pixel_budget, choose_animation_route
from pixellab_cli.errors import ValidationError


class TestChooseAnimationRoute:
    def test_the_default_is_the_cheap_route(self):
        assert choose_animation_route(None).name == "animate-with-text-v3"

    def test_a_count_the_cheap_route_reaches_stays_on_it(self):
        assert choose_animation_route(16).name == "animate-with-text-v3"

    def test_more_frames_than_it_reaches_moves_to_the_long_form_route(self):
        assert choose_animation_route(20).name == "animate-pixminimax"

    def test_the_longest_run_the_long_form_route_takes_is_accepted(self):
        assert choose_animation_route(40).name == "animate-pixminimax"

    def test_more_frames_than_either_route_takes_is_refused(self):
        with pytest.raises(ValidationError) as raised:
            choose_animation_route(44)

        assert "40" in str(raised.value)

    def test_a_count_the_long_form_route_cannot_divide_is_refused(self):
        with pytest.raises(ValidationError) as raised:
            choose_animation_route(18)

        assert "multiple of four" in str(raised.value)

    def test_an_odd_count_on_the_cheap_route_is_refused(self):
        with pytest.raises(ValidationError) as raised:
            choose_animation_route(7)

        assert "even" in str(raised.value)

    def test_too_few_frames_is_refused_with_the_floor(self):
        with pytest.raises(ValidationError) as raised:
            choose_animation_route(2)

        assert "4" in str(raised.value)

    def test_a_named_route_wins_over_the_count(self):
        route = choose_animation_route(8, route_name="animate-pixminimax")

        assert route.name == "animate-pixminimax"

    def test_a_named_route_is_still_held_to_its_own_counts(self):
        with pytest.raises(ValidationError) as raised:
            choose_animation_route(20, route_name="animate-with-text-v3")

        assert "animate-with-text-v3" in str(raised.value)

    def test_a_route_that_is_not_an_animation_route_is_refused(self):
        with pytest.raises(ValidationError) as raised:
            choose_animation_route(8, route_name="create-tileset")

        assert "animate-with-text-v3" in str(raised.value)


class TestThePixelBudget:
    """`animate-with-text-v3` caps width * height * frame_count at 524,288.

    It is the limit a caller actually hits on a large sprite, and the one the frame
    count alone never reveals: sixteen frames is legal, 256x256 is legal, and the two
    together are not. Refused here rather than discovered as a provider rejection.
    """

    def test_a_small_sprite_is_unaffected(self):
        check_pixel_budget("animate-with-text-v3", 16, 64, 64)

    def test_the_budget_is_reached_exactly(self):
        check_pixel_budget("animate-with-text-v3", 8, 256, 256)

    def test_one_frame_past_the_budget_is_refused(self):
        with pytest.raises(ValidationError) as raised:
            check_pixel_budget("animate-with-text-v3", 10, 256, 256)

        assert "524288" in str(raised.value).replace(",", "")

    def test_the_refusal_says_how_many_frames_would_fit(self):
        with pytest.raises(ValidationError) as raised:
            check_pixel_budget("animate-with-text-v3", 16, 256, 256)

        assert "8" in str(raised.value)

    def test_the_largest_square_that_still_takes_sixteen_frames_is_accepted(self):
        check_pixel_budget("animate-with-text-v3", 16, 181, 181)

    def test_one_pixel_wider_no_longer_takes_sixteen(self):
        with pytest.raises(ValidationError):
            check_pixel_budget("animate-with-text-v3", 16, 182, 182)

    def test_an_unknown_size_is_not_guessed_at(self):
        check_pixel_budget("animate-with-text-v3", 16, None, None)

    def test_the_long_form_route_has_no_such_budget(self):
        check_pixel_budget("animate-pixminimax", 40, 256, 256)

    def test_a_zero_side_is_refused_rather_than_skipped(self):
        with pytest.raises(ValidationError) as raised:
            check_pixel_budget("animate-with-text-v3", 8, 0, 256)

        assert "nothing to animate" in str(raised.value)
