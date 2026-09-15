"""Which animation route a frame count reaches.

Two routes animate a loose frame and they do not overlap where it matters:
`animate-with-text-v3` stops at sixteen frames, `animate-pixminimax` reaches forty
and is priced by generation time. Sending twenty frames to the first is a rejection;
sending eight to the second is paying a beta route for what the cheap one does.
"""

import pytest

from pixellab_cli.commands.motion import choose_animation_route
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
