"""Picking the route, which is picking the price.

Three image routes overlap, cost differently and stop at different sizes. Getting
this wrong is not a cosmetic bug: it is either a rejected call or a call at four
times the price it needed to be.
"""

import pytest

from pixellab_cli.errors import ValidationError
from pixellab_cli.routing import choose_image_route, parse_size


class TestParseSize:
    def test_a_pair_is_width_by_height(self):
        assert parse_size("96x64") == {"width": 96, "height": 64}

    def test_one_number_means_a_square(self):
        assert parse_size("64") == {"width": 64, "height": 64}

    def test_the_separator_can_be_an_asterisk(self):
        assert parse_size("96*64") == {"width": 96, "height": 64}

    def test_whitespace_around_it_is_ignored(self):
        assert parse_size(" 64 x 64 ") == {"width": 64, "height": 64}

    def test_something_that_is_not_a_size_is_refused_by_name(self):
        with pytest.raises(ValidationError) as raised:
            parse_size("big")

        assert "big" in str(raised.value)

    def test_a_zero_side_is_refused(self):
        with pytest.raises(ValidationError):
            parse_size("0x64")

    def test_a_negative_side_is_refused(self):
        with pytest.raises(ValidationError):
            parse_size("-8x64")


class TestChooseImageRoute:
    def test_the_default_is_the_cheapest_widest_route(self):
        assert choose_image_route({"width": 64, "height": 64}).name == "create-image-pixflux"

    def test_a_style_image_forces_the_only_route_with_a_style_slot(self):
        route = choose_image_route({"width": 64, "height": 64}, has_style_image=True)

        assert route.name == "create-image-bitforge"
        assert route.param("style_image") is not None

    def test_a_size_beyond_the_default_route_moves_to_the_one_that_reaches_it(self):
        assert choose_image_route({"width": 512, "height": 512}).name == "create-image-pixen"

    def test_the_boundary_of_the_default_route_still_uses_it(self):
        assert choose_image_route({"width": 400, "height": 400}).name == "create-image-pixflux"

    def test_a_style_image_at_a_size_bitforge_cannot_reach_is_refused(self):
        with pytest.raises(ValidationError) as raised:
            choose_image_route({"width": 400, "height": 400}, has_style_image=True)

        assert "style" in str(raised.value)

    def test_a_size_no_route_can_satisfy_is_refused_before_anything_is_spent(self):
        with pytest.raises(ValidationError) as raised:
            choose_image_route({"width": 1024, "height": 1024})

        assert "1024x1024" in str(raised.value)

    def test_the_refusal_names_every_route_and_its_ceiling(self):
        with pytest.raises(ValidationError) as raised:
            choose_image_route({"width": 1024, "height": 1024})

        message = str(raised.value)
        assert "create-image-pixflux" in message
        assert "create-image-pixen" in message
        assert "create-image-bitforge" in message

    def test_an_explicit_route_wins_over_the_choice(self):
        route = choose_image_route({"width": 64, "height": 64}, route_name="create-image-bitforge")

        assert route.name == "create-image-bitforge"

    def test_an_explicit_route_is_still_held_to_its_own_size_limit(self):
        with pytest.raises(ValidationError) as raised:
            choose_image_route({"width": 400, "height": 400}, route_name="create-image-bitforge")

        assert "create-image-bitforge" in str(raised.value)

    def test_an_explicit_route_that_is_not_an_image_route_is_refused(self):
        with pytest.raises(ValidationError) as raised:
            choose_image_route({"width": 64, "height": 64}, route_name="create-tileset")

        assert "create-image-pixflux" in str(raised.value)

    def test_an_unknown_route_name_is_refused_with_the_names_that_work(self):
        with pytest.raises(ValidationError) as raised:
            choose_image_route({"width": 64, "height": 64}, route_name="make-art")

        assert "create-image-pixen" in str(raised.value)

    def test_pixen_still_enforces_its_own_divisibility_rule(self):
        # 510 is inside Pixen's area but not divisible by four; the route's own
        # validation catches it, and routing must not claim otherwise.
        route = choose_image_route({"width": 510, "height": 400})

        assert route.name == "create-image-pixen"
