"""Hold the hand-written route table to the vendored schema.

The table carries judgment the schema does not have, which is why it is written
rather than generated. This is the price of that: every route, every parameter and
every enumerated value is checked against `reference/pixellab-openapi.json`, so a
parameter renamed upstream fails here instead of on a call somebody paid for.
"""

import json
import re
from pathlib import Path

import pytest

from pixellab_cli.catalog import BY_NAME, ROUTES, route
from pixellab_cli.routes import ParamKind, RouteKind

SPEC_PATH = Path(__file__).resolve().parents[1] / "reference" / "pixellab-openapi.json"
SPEC = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
SCHEMAS = SPEC["components"]["schemas"]


def resolve(schema: dict) -> dict:
    """Follow a `$ref` once, and collapse an `anyOf` to its non-null branch."""
    if "$ref" in schema:
        return SCHEMAS[schema["$ref"].split("/")[-1]]
    if "anyOf" in schema:
        branches = [branch for branch in schema["anyOf"] if branch.get("type") != "null"]
        if branches:
            return resolve(branches[0])
    return schema


def request_properties(path: str, method: str) -> tuple[dict, set[str]]:
    """The request body's properties and required set, for one operation."""
    operation = SPEC["paths"][path][method.lower()]
    body = operation.get("requestBody")
    if body is None:
        return {}, set()
    content = body["content"]
    schema = content.get("application/json", next(iter(content.values())))["schema"]
    resolved = resolve(schema)
    return resolved.get("properties", {}), set(resolved.get("required", []))


def string_enum(schema: dict) -> tuple[str, ...] | None:
    """The enumerated values of a parameter, when they are strings."""
    resolved = resolve(schema)
    values = resolved.get("enum")
    if values and all(isinstance(value, str) for value in values):
        return tuple(values)
    return None


ROUTE_IDS = [route_.name for route_ in ROUTES]


@pytest.mark.parametrize("subject", ROUTES, ids=ROUTE_IDS)
class TestAgainstTheVendoredSchema:
    def test_the_path_exists_with_the_method_the_route_declares(self, subject):
        assert subject.path in SPEC["paths"], f"{subject.name}: no such path"
        assert subject.method.lower() in SPEC["paths"][subject.path]

    def test_every_parameter_exists_on_the_endpoint(self, subject):
        properties, _ = request_properties(subject.path, subject.method)
        if not properties:
            pytest.skip("no request body")
        # A path parameter is declared like any other and then taken back out of the
        # body to build the URL, so it is not a property of the request and must not
        # be looked for among them.
        unknown = sorted(subject.param_names - set(properties) - set(subject.path_params))
        assert not unknown, f"{subject.name}: not on the endpoint: {unknown}"

    def test_every_path_parameter_is_one_the_path_names(self, subject):
        named = set(re.findall(r"{([^}]+)}", subject.path))
        assert set(subject.path_params) <= named, f"{subject.name}: not in the path"

    def test_every_required_parameter_of_the_endpoint_is_required_here(self, subject):
        properties, required = request_properties(subject.path, subject.method)
        if not properties:
            pytest.skip("no request body")
        missing = sorted(
            name
            for name in required
            if subject.param(name) is None or not subject.param(name).required
        )
        assert not missing, f"{subject.name}: required upstream, not here: {missing}"

    def test_nothing_is_required_here_that_the_endpoint_treats_as_optional(self, subject):
        properties, required = request_properties(subject.path, subject.method)
        if not properties:
            pytest.skip("no request body")
        over = sorted(
            param.name
            for param in subject.params
            if param.required and param.name in properties and param.name not in required
        )
        assert not over, f"{subject.name}: required here, optional upstream: {over}"

    def test_every_enumerated_value_matches_the_schema(self, subject):
        properties, _ = request_properties(subject.path, subject.method)
        if not properties:
            pytest.skip("no request body")
        for param in subject.params:
            if param.choices is None or param.name not in properties:
                continue
            upstream = string_enum(properties[param.name])
            if upstream is None:
                continue
            assert set(param.choices) == set(upstream), (
                f"{subject.name}.{param.name}: {sorted(param.choices)} is not {sorted(upstream)}"
            )

    def test_a_parameter_the_schema_enumerates_is_enumerated_here_too(self, subject):
        properties, _ = request_properties(subject.path, subject.method)
        if not properties:
            pytest.skip("no request body")
        unconstrained = sorted(
            param.name
            for param in subject.params
            if param.choices is None
            and param.kind is ParamKind.STRING
            and param.name in properties
            and string_enum(properties[param.name]) is not None
        )
        assert not unconstrained, (
            f"{subject.name}: the schema enumerates these and the table does not: {unconstrained}"
        )

    def test_a_default_declared_here_is_the_schema_s_default(self, subject):
        properties, _ = request_properties(subject.path, subject.method)
        if not properties:
            pytest.skip("no request body")
        for param in subject.params:
            if param.default is None or param.name not in properties:
                continue
            upstream = resolve(properties[param.name]).get("default")
            if upstream is None:
                upstream = properties[param.name].get("default")
            if upstream is None:
                continue
            assert param.default == upstream, f"{subject.name}.{param.name}"


class TestTheTableItself:
    def test_every_route_name_is_unique(self):
        assert len(BY_NAME) == len(ROUTES)

    def test_a_route_is_found_by_name(self):
        assert route("unzoom").path == "/unzoom"

    def test_an_unknown_name_says_what_the_names_are(self):
        with pytest.raises(KeyError) as raised:
            route("make-me-a-sprite")

        assert "unzoom" in str(raised.value)

    def test_every_asynchronous_route_names_what_it_is_polled_by(self):
        for subject in ROUTES:
            if subject.kind is RouteKind.SYNCHRONOUS:
                continue
            assert subject.result_id_field and subject.poll_path, subject.name

    def test_every_poll_path_has_exactly_one_placeholder(self):
        for subject in ROUTES:
            if subject.poll_path is None:
                continue
            assert subject.poll_path.count("{id}") == 1, subject.name

    def test_the_cleanup_routes_are_cheaper_than_the_pro_routes(self):
        assert route("unzoom").estimated_generations < route("inpaint-v3").estimated_generations

    def test_checking_a_balance_is_free(self):
        assert route("balance").estimated_generations == 0.0


class TestTheFourDirectionCharacterRoute:
    """R1.7, R1.8: a route of its own, not v3 with a smaller number passed to it."""

    def test_it_is_reachable_by_the_name_pixellab_gives_it(self):
        assert route("create-character-with-4-directions").path == (
            "/create-character-with-4-directions"
        )

    def test_it_is_collected_the_way_v3_is(self):
        subject = route("create-character-with-4-directions")

        assert subject.kind is RouteKind.BACKGROUND_JOB
        assert subject.result_id_field == "background_job_id"
        assert subject.asset_id_field == "character_id"

    def test_a_frame_size_is_required_here_and_not_on_v3(self):
        assert route("create-character-with-4-directions").param("image_size").required
        assert not route("create-character-v3").param("image_size").required

    def test_it_carries_the_three_style_controls_v3_does_not_have_together(self):
        subject = route("create-character-with-4-directions")

        assert {"outline", "shading", "detail"} <= subject.param_names
        assert route("create-character-v3").param("shading") is None

    def test_it_takes_sprites_keyed_by_direction_rather_than_one_south_frame(self):
        subject = route("create-character-with-4-directions")

        assert subject.param("directions").kind is ParamKind.OBJECT
        assert subject.param("reference_image") is None

    def test_it_is_estimated_below_the_pro_routes(self):
        assert (
            route("create-character-with-4-directions").estimated_generations
            < route("create-character-state").estimated_generations
        )


class TestTheInterpolationRoute:
    """R2.26, R2.27: both ends required, no frame count, and Pro priced."""

    def test_both_ends_are_required(self):
        subject = route("interpolation-v2")

        assert subject.param("start_image").required
        assert subject.param("end_image").required

    def test_it_has_no_frame_count_to_route_by(self):
        assert route("interpolation-v2").param("frame_count") is None

    def test_each_end_has_to_match_the_output_size(self):
        subject = route("interpolation-v2")

        assert subject.param("start_image").matches_size == "image_size"
        assert subject.param("end_image").matches_size == "image_size"

    def test_it_reaches_less_far_than_the_animation_routes(self):
        assert route("interpolation-v2").param("start_image").size.max_side == 128
        assert route("animate-with-text-v3").param("first_frame").size.max_side == 256

    def test_it_is_priced_with_the_pro_routes(self):
        assert route("interpolation-v2").estimated_generations == (
            route("create-character-state").estimated_generations
        )
