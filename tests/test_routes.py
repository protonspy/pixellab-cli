import pytest

from pixellab_cli.routes import (
    DETAIL,
    DIRECTION,
    OUTLINE,
    SHADING,
    VIEW,
    Param,
    ParamKind,
    Route,
    RouteKind,
    SizeLimit,
)


class TestStyleVocabulary:
    def test_the_enums_are_the_strings_the_api_expects_spaces_included(self):
        assert "single color black outline" in OUTLINE
        assert "highly detailed shading" in SHADING
        assert "highly detailed" in DETAIL
        assert "low top-down" in VIEW

    def test_there_are_eight_directions_in_compass_order_pairs(self):
        assert len(DIRECTION) == 8
        assert set(DIRECTION) == {
            "north",
            "north-east",
            "east",
            "south-east",
            "south",
            "south-west",
            "west",
            "north-west",
        }

    def test_detail_and_shading_are_not_the_same_vocabulary(self):
        # They read alike and are routinely confused; `highly detailed` is a detail
        # level and `highly detailed shading` is a shading level.
        assert set(DETAIL).isdisjoint(SHADING)


class TestSizeLimit:
    def test_an_empty_limit_describes_itself_as_unbounded(self):
        assert SizeLimit().describe() == "no size limits"

    def test_every_bound_appears_in_the_description(self):
        described = SizeLimit(
            min_side=16,
            max_side=512,
            min_area=1024,
            max_area=262144,
            divisible_by=4,
            square_below=32,
        ).describe()

        assert "at least 16" in described
        assert "at most 512" in described
        assert "area at least 1024" in described
        assert "area at most 262144" in described
        assert "divisible by 4" in described
        assert "square when either side is below 32" in described


class TestRoute:
    def _synchronous(self, **overrides) -> Route:
        defaults = dict(
            name="create-image-pixflux",
            method="POST",
            path="/create-image-pixflux",
            kind=RouteKind.SYNCHRONOUS,
            params=(
                Param("description", ParamKind.STRING, required=True),
                Param("outline", ParamKind.STRING, choices=OUTLINE),
            ),
        )
        return Route(**{**defaults, **overrides})

    def test_param_names_lists_every_parameter(self):
        assert self._synchronous().param_names == {"description", "outline"}

    def test_param_finds_one_by_name(self):
        assert self._synchronous().param("outline").choices == OUTLINE

    def test_param_returns_none_for_one_the_route_does_not_accept(self):
        assert self._synchronous().param("shading") is None

    def test_a_synchronous_route_needs_no_polling_fields(self):
        route = self._synchronous()

        assert route.result_id_field is None
        assert route.poll_path is None

    def test_a_background_route_must_name_what_it_is_polled_by(self):
        with pytest.raises(ValueError, match="polled by"):
            Route(
                name="create-character-v3",
                method="POST",
                path="/create-character-v3",
                kind=RouteKind.BACKGROUND_JOB,
                params=(),
            )

    def test_a_resource_route_must_name_the_path_it_is_polled_on(self):
        with pytest.raises(ValueError, match="polled"):
            Route(
                name="create-1-direction-object",
                method="POST",
                path="/create-1-direction-object",
                kind=RouteKind.RESOURCE,
                params=(),
                result_id_field="object_id",
            )

    def test_a_background_route_with_both_fields_is_accepted(self):
        route = Route(
            name="create-character-v3",
            method="POST",
            path="/create-character-v3",
            kind=RouteKind.BACKGROUND_JOB,
            params=(),
            result_id_field="background_job_id",
            poll_path="/background-jobs/{id}",
        )

        assert route.kind is RouteKind.BACKGROUND_JOB

    def test_a_route_carries_a_default_cost_estimate(self):
        assert self._synchronous().estimated_generations == 1.0

    def test_a_route_can_declare_a_pro_tier_estimate(self):
        assert self._synchronous(estimated_generations=30.0).estimated_generations == 30.0
