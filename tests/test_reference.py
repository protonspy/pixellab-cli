from pixellab_cli.reference import SchemaDrift, diff_paths, diff_schemas, fal_slug


def test_fal_slug_flattens_the_endpoint_id_into_a_filename():
    assert fal_slug("openai/gpt-image-2.5/sunburst/edit") == "openai-gpt-image-2.5-sunburst-edit"


def test_diff_paths_reports_an_added_route():
    vendored = {"paths": {"/create-image-pixflux": {"post": {}}}}
    live = {"paths": {"/create-image-pixflux": {"post": {}}, "/create-image-pixen": {"post": {}}}}

    drift = diff_paths(vendored, live)

    assert drift.added == ("/create-image-pixen",)
    assert drift.removed == ()
    assert drift.changed == ()


def test_diff_paths_reports_a_removed_route():
    vendored = {"paths": {"/rotate": {"post": {}}, "/resize": {"post": {}}}}
    live = {"paths": {"/resize": {"post": {}}}}

    assert diff_paths(vendored, live).removed == ("/rotate",)


def test_diff_paths_reports_a_route_whose_shape_moved():
    vendored = {"paths": {"/resize": {"post": {"summary": "Resize"}}}}
    live = {"paths": {"/resize": {"post": {"summary": "Resize pixel art image"}}}}

    assert diff_paths(vendored, live).changed == ("/resize",)


def test_diff_paths_on_a_missing_vendored_document_reports_every_route_as_added():
    live = {"paths": {"/balance": {"get": {}}}}

    assert diff_paths({}, live).added == ("/balance",)


def test_diff_schemas_compares_the_components_block():
    vendored = {"components": {"schemas": {"Outline": {"enum": ["lineless"]}}}}
    live = {"components": {"schemas": {"Outline": {"enum": ["lineless", "selective outline"]}}}}

    assert diff_schemas(vendored, live).changed == ("Outline",)


def test_identical_documents_do_not_drift():
    document = {"paths": {"/balance": {"get": {}}}, "components": {"schemas": {"A": {}}}}

    assert diff_paths(document, document).is_empty
    assert diff_schemas(document, document).is_empty


def test_summary_names_each_kind_of_change():
    drift = SchemaDrift(added=("a",), removed=("b", "c"), changed=("d",))

    assert drift.summary() == "1 added, 2 removed, 1 changed"


def test_summary_of_no_drift_says_so():
    assert SchemaDrift().summary() == "no drift"
