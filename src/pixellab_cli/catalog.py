"""The routes this tool exposes, as data.

One `Route` per PixelLab endpoint a command can reach. Written by hand from
`reference/pixellab-openapi.json`; `tests/test_catalog.py` holds every entry to that
document, so a parameter renamed upstream fails the suite rather than a paid call.

Not every endpoint PixelLab publishes is here. The ones that are missing are the
legacy families superseded by a route above them, and the surfaces this project does
not call at all — see `adr:0002-call-pixellab-rest-v2-directly`.

The estimates are from PixelLab's public pricing page, reviewed 2026-09-12, and they
are estimates: the `usage` the provider returns is what the ledger records. See
`docs/wiki/pages/pixellab-cost-model.md`.
"""

from __future__ import annotations

from pixellab_cli.routes import (
    BACKGROUND_REMOVAL,
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

BACKGROUND_JOBS_PATH = "/background-jobs/{id}"

# Style parameters travel together on most generation routes. Passing the tuple
# around beats repeating six lines twenty times, and it keeps one route from
# quietly acquiring a different set of allowed values than its neighbour.
STYLE_PARAMS = (
    Param("outline", ParamKind.STRING, choices=OUTLINE, help="Outline style."),
    Param("shading", ParamKind.STRING, choices=SHADING, help="Shading complexity."),
    Param("detail", ParamKind.STRING, choices=DETAIL, help="Level of detail."),
)
CAMERA_PARAMS = (
    Param("view", ParamKind.STRING, choices=VIEW, help="Camera view angle."),
    Param("direction", ParamKind.STRING, choices=DIRECTION, help="Subject direction."),
)
SEED = Param("seed", ParamKind.INTEGER, minimum=0, help="Seed for a repeatable generation.")


def _image(name: str, *, required: bool = False, max_side: int | None = None, help: str = ""):
    limit = SizeLimit(max_side=max_side) if max_side else None
    return Param(name, ParamKind.IMAGE, required=required, size=limit, help=help)


# --------------------------------------------------------------------------- images

CREATE_IMAGE_PIXFLUX = Route(
    name="create-image-pixflux",
    method="POST",
    path="/create-image-pixflux",
    kind=RouteKind.SYNCHRONOUS,
    summary="One pixel-art image, up to 400x400. The cheapest route to a single sprite.",
    estimated_generations=1.0,
    params=(
        Param("description", ParamKind.STRING, required=True, help="What to draw."),
        Param(
            "image_size",
            ParamKind.SIZE,
            required=True,
            size=SizeLimit(min_area=32 * 32, max_area=400 * 400),
            help="Output size.",
        ),
        *STYLE_PARAMS,
        *CAMERA_PARAMS,
        Param("text_guidance_scale", ParamKind.NUMBER, default=8.0),
        Param("isometric", ParamKind.BOOLEAN, default=False),
        Param("no_background", ParamKind.BOOLEAN, default=False),
        Param("background_removal_task", ParamKind.STRING, choices=BACKGROUND_REMOVAL),
        _image("init_image", help="Image to start from."),
        Param("init_image_strength", ParamKind.INTEGER, default=300),
        _image("color_image", help="An image whose colours become the forced palette."),
        SEED,
    ),
)

CREATE_IMAGE_PIXEN = Route(
    name="create-image-pixen",
    method="POST",
    path="/create-image-pixen",
    kind=RouteKind.SYNCHRONOUS,
    summary="One pixel-art image, up to 512x512, with sharper outline and detail control.",
    estimated_generations=1.0,
    params=(
        Param("description", ParamKind.STRING, required=True, help="What to draw."),
        Param(
            "image_size",
            ParamKind.SIZE,
            required=True,
            size=SizeLimit(min_side=16, max_area=512 * 512, divisible_by=4, square_below=32),
            help="Output size. Both sides divisible by four; square below 32.",
        ),
        Param("outline", ParamKind.STRING, choices=OUTLINE),
        Param("detail", ParamKind.STRING, choices=DETAIL, default="highly detailed"),
        *CAMERA_PARAMS,
        Param("no_background", ParamKind.BOOLEAN, default=False),
        Param("background_removal_task", ParamKind.STRING, choices=BACKGROUND_REMOVAL),
        Param("enhance_prompt", ParamKind.BOOLEAN, default=False, help="Costs ~0.05 extra."),
        SEED,
    ),
)

CREATE_IMAGE_BITFORGE = Route(
    name="create-image-bitforge",
    method="POST",
    path="/create-image-bitforge",
    kind=RouteKind.SYNCHRONOUS,
    summary="One pixel-art image up to 200x200, matching a style image. The only base "
    "route with a style slot.",
    estimated_generations=1.0,
    params=(
        Param("description", ParamKind.STRING, required=True, help="What to draw."),
        Param(
            "image_size",
            ParamKind.SIZE,
            required=True,
            size=SizeLimit(max_area=200 * 200),
            help="Output size.",
        ),
        Param("negative_description", ParamKind.STRING, default=""),
        *STYLE_PARAMS,
        *CAMERA_PARAMS,
        Param("text_guidance_scale", ParamKind.NUMBER, default=8.0),
        Param(
            "style_strength",
            ParamKind.INTEGER,
            minimum=0,
            maximum=100,
            default=0,
            help="How hard the style image binds. 50 is balanced.",
        ),
        Param("isometric", ParamKind.BOOLEAN, default=False),
        Param("oblique_projection", ParamKind.BOOLEAN, default=False),
        Param("no_background", ParamKind.BOOLEAN, default=False),
        Param("coverage_percentage", ParamKind.NUMBER),
        _image("init_image"),
        Param("init_image_strength", ParamKind.INTEGER, default=300),
        _image("style_image", help="The style to match."),
        _image("inpainting_image"),
        _image("mask_image", help="White is where the model may draw."),
        _image("color_image"),
        SEED,
    ),
)

IMAGE_TO_PIXELART_PRO = Route(
    name="image-to-pixelart-pro",
    method="POST",
    path="/image-to-pixelart-pro",
    kind=RouteKind.BACKGROUND_JOB,
    summary="Turn any image into pixel art, output size detected rather than given.",
    estimated_generations=20.0,
    result_id_field="background_job_id",
    poll_path=BACKGROUND_JOBS_PATH,
    params=(
        _image("image", required=True, help="The image to convert."),
        Param("description", ParamKind.STRING, help="Extra style instructions."),
        SEED,
    ),
)

# ----------------------------------------------------------------------- characters

CREATE_CHARACTER_V3 = Route(
    name="create-character-v3",
    method="POST",
    path="/create-character-v3",
    kind=RouteKind.BACKGROUND_JOB,
    summary="A character with eight rotations and a skeleton, from a description or a "
    "south-facing reference sprite.",
    estimated_generations=4.0,
    result_id_field="background_job_id",
    poll_path=BACKGROUND_JOBS_PATH,
    asset_id_field="character_id",
    params=(
        Param("description", ParamKind.STRING, required=True),
        _image("reference_image", max_side=256, help="A south-facing sprite to rotate."),
        Param("image_size", ParamKind.SIZE, size=SizeLimit(max_side=256)),
        Param("view", ParamKind.STRING, choices=VIEW, default="low top-down"),
        Param("template_id", ParamKind.STRING, default="mannequin", help="Skeleton body type."),
        Param("name", ParamKind.STRING, help="Display name."),
        Param("no_background", ParamKind.BOOLEAN, default=True),
        Param("outline", ParamKind.STRING, default="single color black outline"),
        Param("detail", ParamKind.STRING, default="medium detail"),
        Param("enhance_prompt", ParamKind.BOOLEAN, default=False),
        SEED,
    ),
)

GENERATE_8_ROTATIONS_V3 = Route(
    name="generate-8-rotations-v3",
    method="POST",
    path="/generate-8-rotations-v3",
    kind=RouteKind.BACKGROUND_JOB,
    summary="Eight directional views of a reference frame, without creating a character.",
    estimated_generations=3.0,
    result_id_field="background_job_id",
    poll_path=BACKGROUND_JOBS_PATH,
    params=(
        _image("first_frame", required=True, max_side=256, help="The frame to rotate."),
        Param("description", ParamKind.STRING, help="Improves rotation consistency."),
        Param("no_background", ParamKind.BOOLEAN),
        Param("seed", ParamKind.INTEGER, minimum=0, default=0),
    ),
)

CREATE_CHARACTER_ANIMATION = Route(
    name="characters-animations",
    method="POST",
    path="/characters/animations",
    kind=RouteKind.BACKGROUND_JOB,
    summary="Animate an existing character. One job per direction, so the cost is the "
    "tier times the number of directions.",
    estimated_generations=1.0,
    result_id_field="background_job_ids",
    poll_path=BACKGROUND_JOBS_PATH,
    params=(
        Param("character_id", ParamKind.STRING, required=True),
        Param("animation_name", ParamKind.STRING),
        Param("description", ParamKind.STRING),
        Param("action_description", ParamKind.STRING, help="Required unless a template is given."),
        Param("mode", ParamKind.STRING, choices=("template", "v3", "pro")),
        Param("template_animation_id", ParamKind.STRING, help="Required for template mode."),
        Param("frame_count", ParamKind.INTEGER, minimum=4, maximum=16, default=8),
        _image("custom_start_frame", max_side=256),
        _image("end_frame", max_side=256),
        Param("keep_first_frame", ParamKind.BOOLEAN, default=True),
        Param("text_guidance_scale", ParamKind.NUMBER, default=8.0),
        Param("directions", ParamKind.STRING_LIST, max_items=8),
        Param("isometric", ParamKind.BOOLEAN, default=False),
        _image("color_image"),
        Param("force_colors", ParamKind.BOOLEAN, default=False),
        Param("enhance_prompt", ParamKind.BOOLEAN, default=False),
        SEED,
    ),
)

ANIMATE_WITH_TEXT_V3 = Route(
    name="animate-with-text-v3",
    method="POST",
    path="/animate-with-text-v3",
    kind=RouteKind.BACKGROUND_JOB,
    summary="An animation from a loose first frame and an action, no character needed.",
    estimated_generations=1.0,
    result_id_field="background_job_id",
    poll_path=BACKGROUND_JOBS_PATH,
    params=(
        _image("first_frame", required=True, max_side=256),
        _image("last_frame", max_side=256, help="Guides where the motion ends."),
        Param("action", ParamKind.STRING, required=True, help="'walking', 'attacking'."),
        Param(
            "frame_count",
            ParamKind.INTEGER,
            minimum=4,
            maximum=16,
            default=8,
            help="Four to sixteen, and even.",
        ),
        Param("no_background", ParamKind.BOOLEAN),
        Param("drift_threshold", ParamKind.NUMBER, help="Colour de-flicker sensitivity."),
        Param("enhance_prompt", ParamKind.BOOLEAN, default=False),
        Param("seed", ParamKind.INTEGER, minimum=0, default=0),
    ),
)

# -------------------------------------------------------------------------- objects

CREATE_1_DIRECTION_OBJECT = Route(
    name="create-1-direction-object",
    method="POST",
    path="/create-1-direction-object",
    kind=RouteKind.RESOURCE,
    summary="A prop from one angle. Pro Tools pricing.",
    estimated_generations=30.0,
    result_id_field="object_id",
    poll_path="/objects/{id}",
    asset_id_field="object_id",
    params=(
        Param("description", ParamKind.STRING, required=True),
        Param("size", ParamKind.INTEGER, minimum=16, maximum=256, help="Square, defaults to 64."),
        Param("view", ParamKind.STRING, choices=("top-down", "sidescroller"), default="top-down"),
        Param("style_images", ParamKind.IMAGE_LIST, help="Style references, 256x256 each."),
        Param("item_descriptions", ParamKind.STRING_LIST),
    ),
)

CREATE_8_DIRECTION_OBJECT = Route(
    name="create-8-direction-object",
    method="POST",
    path="/create-8-direction-object",
    kind=RouteKind.RESOURCE,
    summary="A prop rendered from eight angles in one shot. Pro Tools pricing.",
    estimated_generations=30.0,
    result_id_field="object_id",
    poll_path="/objects/{id}",
    asset_id_field="object_id",
    params=(
        Param("description", ParamKind.STRING, required=True),
        Param("size", ParamKind.INTEGER, minimum=24, maximum=168),
        Param("view", ParamKind.STRING, choices=VIEW, default="low top-down"),
        _image("reference_image", help="Rotate this exact object. Excludes style_image and size."),
        _image("style_image", help="Match this style. Excludes reference_image and size."),
        Param("style_object_id", ParamKind.STRING),
    ),
)

CREATE_MAP_OBJECT = Route(
    name="map-objects",
    method="POST",
    path="/map-objects",
    kind=RouteKind.BACKGROUND_JOB,
    summary="A transparent prop for a game map, optionally style-matched to the map itself.",
    estimated_generations=1.0,
    result_id_field="background_job_id",
    poll_path=BACKGROUND_JOBS_PATH,
    asset_id_field="object_id",
    params=(
        Param("description", ParamKind.STRING, required=True),
        Param("image_size", ParamKind.SIZE, help="Defaults to 128x128."),
        Param("view", ParamKind.STRING, choices=VIEW, default="high top-down"),
        Param(
            "outline",
            ParamKind.STRING,
            choices=("single color outline", "selective outline", "lineless"),
            default="single color outline",
        ),
        Param(
            "shading",
            ParamKind.STRING,
            choices=("flat shading", "basic shading", "medium shading", "detailed shading"),
            default="medium shading",
        ),
        # This route spells the top level `high detail` where every other route
        # spells it `highly detailed`. It is not a typo here.
        Param(
            "detail",
            ParamKind.STRING,
            choices=("low detail", "medium detail", "high detail"),
            default="medium detail",
        ),
        Param("text_guidance_scale", ParamKind.NUMBER, default=8.0),
        _image("init_image"),
        Param("init_image_strength", ParamKind.INTEGER, default=300),
        _image("color_image"),
        _image("background_image", help="The map to blend into. Required when inpainting."),
        Param("inpainting", ParamKind.OBJECT),
        SEED,
    ),
)

# ---------------------------------------------------------------------------- tiles

CREATE_TILESET = Route(
    name="create-tileset",
    method="POST",
    path="/create-tileset",
    kind=RouteKind.RESOURCE,
    summary="A top-down Wang tileset: two terrains that connect seamlessly.",
    estimated_generations=3.0,
    result_id_field="tileset_id",
    poll_path="/tilesets/{id}",
    asset_id_field="tileset_id",
    params=(
        Param("lower_description", ParamKind.STRING, required=True, help="'grass', 'ocean'."),
        Param("upper_description", ParamKind.STRING, required=True, help="'sand', 'stone'."),
        Param("transition_description", ParamKind.STRING, default=""),
        Param("tile_size", ParamKind.SIZE, help="Defaults to 16x16."),
        Param("mode", ParamKind.STRING, choices=("standard", "pro"), default="standard"),
        Param(
            "shape_style",
            ParamKind.STRING,
            choices=("square", "round"),
            help="Standard mode only; rejected with mode='pro'.",
        ),
        Param("enhance", ParamKind.BOOLEAN, default=True),
        Param("spread_x", ParamKind.NUMBER, minimum=0.0, maximum=1.0, default=0.5),
        Param("slope_size", ParamKind.NUMBER, minimum=0.0, maximum=1.0, default=0.0),
        Param("raggedness", ParamKind.NUMBER, minimum=0.0, maximum=1.0, default=0.0),
        Param("text_guidance_scale", ParamKind.NUMBER, minimum=1.0, maximum=20.0, default=8.0),
        *STYLE_PARAMS,
        Param(
            "view",
            ParamKind.STRING,
            choices=("low top-down", "high top-down"),
            default="high top-down",
        ),
        Param("tile_strength", ParamKind.NUMBER, minimum=0.1, maximum=2.0, default=1.0),
        Param("tileset_adherence", ParamKind.NUMBER, minimum=0.0, maximum=500.0, default=100.0),
        Param(
            "tileset_adherence_freedom",
            ParamKind.NUMBER,
            minimum=0.0,
            maximum=900.0,
            default=500.0,
        ),
        Param("transition_size", ParamKind.NUMBER, minimum=0.0, maximum=1.0, default=0.0),
        Param("lower_base_tile_id", ParamKind.STRING),
        Param("upper_base_tile_id", ParamKind.STRING),
        _image("lower_reference_image"),
        _image("upper_reference_image"),
        _image("transition_reference_image"),
        _image("color_image"),
        SEED,
    ),
)

CREATE_TILESET_SIDESCROLLER = Route(
    name="create-tileset-sidescroller",
    method="POST",
    path="/create-tileset-sidescroller",
    kind=RouteKind.RESOURCE,
    summary="A platformer tileset: transparent floating platforms, side view, fixed.",
    estimated_generations=3.0,
    result_id_field="tileset_id",
    poll_path="/tilesets-sidescroller/{id}",
    asset_id_field="tileset_id",
    params=(
        Param("lower_description", ParamKind.STRING, required=True, help="'stone bricks'."),
        Param("transition_description", ParamKind.STRING, default="", help="'moss and vines'."),
        Param("tile_size", ParamKind.SIZE, help="Defaults to 16x16."),
        Param("text_guidance_scale", ParamKind.NUMBER, minimum=1.0, maximum=20.0, default=8.0),
        *STYLE_PARAMS,
        Param("tile_strength", ParamKind.NUMBER, minimum=0.1, maximum=2.0, default=1.0),
        Param("tileset_adherence", ParamKind.NUMBER, minimum=0.0, maximum=500.0, default=100.0),
        Param(
            "tileset_adherence_freedom",
            ParamKind.NUMBER,
            minimum=0.0,
            maximum=900.0,
            default=500.0,
        ),
        Param("transition_size", ParamKind.NUMBER, choices=None, minimum=0.0, maximum=1.0),
        Param("lower_base_tile_id", ParamKind.STRING),
        _image("lower_reference_image"),
        _image("transition_reference_image"),
        _image("color_image"),
        SEED,
    ),
)

CREATE_TILES_PRO = Route(
    name="create-tiles-pro",
    method="POST",
    path="/create-tiles-pro",
    kind=RouteKind.RESOURCE,
    summary="Tile variants, or a connectable road, terrain or building set. Pro Tools pricing.",
    estimated_generations=30.0,
    result_id_field="tile_id",
    poll_path="/tiles-pro/{id}",
    asset_id_field="tile_id",
    params=(
        Param(
            "description",
            ParamKind.STRING,
            required=True,
            help="Number the variants: '1). grass 2). stone'.",
        ),
        Param(
            "tile_type",
            ParamKind.STRING,
            choices=("hex", "hex_pointy", "isometric", "oblique", "octagon", "square_topdown"),
            default="isometric",
        ),
        Param("tile_size", ParamKind.INTEGER, minimum=16, maximum=128, default=32),
        Param("tile_height", ParamKind.INTEGER),
        Param(
            "tile_view",
            ParamKind.STRING,
            choices=("top-down", "high top-down", "low top-down", "side"),
            default="low top-down",
        ),
        Param("tile_view_angle", ParamKind.NUMBER, minimum=0.0, maximum=90.0),
        Param("tile_depth_ratio", ParamKind.NUMBER, minimum=0.0, maximum=1.0),
        Param("tile_flat_top_px", ParamKind.INTEGER, help="Isometric only: 2 classic, 4 modern."),
        Param("oblique_lean", ParamKind.NUMBER),
        Param(
            "outline_mode", ParamKind.STRING, choices=("outline", "segmentation"), default="outline"
        ),
        Param(
            "tile_feature",
            ParamKind.STRING,
            choices=("roads", "tileset", "building"),
            help="Makes a connectable set instead of independent tiles.",
        ),
        Param("building_wall_tiles", ParamKind.INTEGER, minimum=1, maximum=3),
        Param("building_layout", ParamKind.STRING, choices=("grid", "materials")),
        Param("building_wall_description", ParamKind.STRING),
        Param("building_wall_angle", ParamKind.NUMBER),
        Param("building_floor_description", ParamKind.STRING),
        Param("building_floor2_description", ParamKind.STRING),
        Param("style_images", ParamKind.IMAGE_LIST),
        Param("style_options", ParamKind.OBJECT),
        SEED,
    ),
)

CREATE_ISOMETRIC_TILE = Route(
    name="create-isometric-tile",
    method="POST",
    path="/create-isometric-tile",
    kind=RouteKind.RESOURCE,
    summary="One isometric ground tile, 16x16 to 64x64.",
    estimated_generations=1.0,
    result_id_field="tile_id",
    poll_path="/isometric-tiles/{id}",
    asset_id_field="tile_id",
    params=(
        Param("description", ParamKind.STRING, required=True),
        Param(
            "image_size",
            ParamKind.SIZE,
            required=True,
            size=SizeLimit(min_area=16 * 16, max_area=64 * 64),
        ),
        Param("text_guidance_scale", ParamKind.NUMBER, default=8.0),
        # This route has no `single color black outline`; the four-value set does
        # not apply here.
        Param(
            "outline",
            ParamKind.STRING,
            choices=("single color outline", "selective outline", "lineless"),
            default="lineless",
        ),
        Param("shading", ParamKind.STRING, choices=SHADING, default="basic shading"),
        Param("detail", ParamKind.STRING, choices=DETAIL, default="medium detail"),
        Param("isometric_tile_size", ParamKind.INTEGER, choices=None, default=16),
        Param(
            "isometric_tile_shape",
            ParamKind.STRING,
            choices=("thick tile", "thin tile", "block"),
            default="block",
        ),
        _image("init_image"),
        Param("init_image_strength", ParamKind.INTEGER, default=300),
        _image("color_image"),
        SEED,
    ),
)

# -------------------------------------------------------------------------- editing

EDIT_IMAGE_PIXEN = Route(
    name="edit-image-pixen",
    method="POST",
    path="/edit-image-pixen",
    kind=RouteKind.BACKGROUND_JOB,
    summary="Change one thing about a sprite. Pose, composition and pixel style survive.",
    estimated_generations=1.0,
    result_id_field="background_job_id",
    poll_path=BACKGROUND_JOBS_PATH,
    params=(
        _image("image", required=True, max_side=256, help="The sprite to edit."),
        Param("description", ParamKind.STRING, required=True, help="'give him a red cape'."),
        Param("width", ParamKind.INTEGER, minimum=16, maximum=256),
        Param("height", ParamKind.INTEGER, minimum=16, maximum=256),
        Param("no_background", ParamKind.BOOLEAN, default=True),
        SEED,
    ),
)

EDIT_IMAGES_V2 = Route(
    name="edit-images-v2",
    method="POST",
    path="/edit-images-v2",
    kind=RouteKind.BACKGROUND_JOB,
    summary="Edit up to sixteen images at once, by text or against a reference. Pro pricing.",
    estimated_generations=30.0,
    result_id_field="background_job_id",
    poll_path=BACKGROUND_JOBS_PATH,
    params=(
        Param(
            "method",
            ParamKind.STRING,
            choices=("edit_with_text", "edit_with_reference"),
            default="edit_with_text",
        ),
        Param("edit_images", ParamKind.IMAGE_LIST, required=True, max_items=16),
        Param("image_size", ParamKind.SIZE, required=True, size=SizeLimit(max_area=512 * 512)),
        Param("description", ParamKind.STRING, help="Required for edit_with_text."),
        Param("reference_image", ParamKind.OBJECT, help="Required for edit_with_reference."),
        Param("no_background", ParamKind.BOOLEAN, default=False),
        SEED,
    ),
)

INPAINT_V3 = Route(
    name="inpaint-v3",
    method="POST",
    path="/inpaint-v3",
    kind=RouteKind.BACKGROUND_JOB,
    summary="Redraw only the masked area. Pro pricing.",
    estimated_generations=30.0,
    result_id_field="background_job_id",
    poll_path=BACKGROUND_JOBS_PATH,
    params=(
        Param("description", ParamKind.STRING, required=True, help="What goes in the mask."),
        Param("inpainting_image", ParamKind.OBJECT, required=True),
        Param("mask_image", ParamKind.OBJECT, required=True, help="White is redrawn."),
        Param("no_background", ParamKind.BOOLEAN, default=False),
        Param("crop_to_mask", ParamKind.BOOLEAN, default=True),
        SEED,
    ),
)

# -------------------------------------------------------------------------- cleanup

REMOVE_BACKGROUND = Route(
    name="remove-background",
    method="POST",
    path="/remove-background",
    kind=RouteKind.SYNCHRONOUS,
    summary="A transparent PNG, up to 400x400.",
    estimated_generations=0.1,
    params=(
        _image("image", required=True),
        Param("image_size", ParamKind.SIZE, required=True, size=SizeLimit(max_area=400 * 400)),
        Param("background_removal_task", ParamKind.STRING, choices=BACKGROUND_REMOVAL),
        Param("text", ParamKind.STRING, help="Naming the foreground helps."),
        SEED,
    ),
)

UNZOOM = Route(
    name="unzoom",
    method="POST",
    path="/unzoom",
    kind=RouteKind.SYNCHRONOUS,
    summary="Recover the native grid from an upscaled sprite. Run it on anything from "
    "the internet before using it as a reference.",
    estimated_generations=0.1,
    params=(
        _image("image", required=True),
        Param(
            "quantize",
            ParamKind.INTEGER,
            minimum=-1,
            maximum=256,
            default=0,
            help="0 auto-detects a palette, -1 keeps every colour.",
        ),
    ),
)

CORRECT_PIXELART = Route(
    name="correct-pixelart",
    method="POST",
    path="/correct-pixelart",
    kind=RouteKind.SYNCHRONOUS,
    summary="Re-align nearly-on-grid art without resizing it.",
    estimated_generations=0.1,
    params=(
        Param("images", ParamKind.IMAGE_LIST, required=True, help="All the same size."),
        Param("strength", ParamKind.NUMBER, minimum=0.0, maximum=1.0, default=0.1),
    ),
)

REDUCE_COLORS = Route(
    name="reduce-colors",
    method="POST",
    path="/reduce-colors",
    kind=RouteKind.SYNCHRONOUS,
    summary="Quantize frames onto one shared palette. Passing a whole set at once is "
    "the point: they come back sharing a palette.",
    estimated_generations=0.1,
    params=(
        Param("images", ParamKind.IMAGE_LIST, required=True, help="All the same size."),
        Param("num_colors", ParamKind.INTEGER, minimum=2, maximum=256),
        _image("palette_image", help="Force an existing palette. Excludes num_colors."),
        Param("dithering", ParamKind.STRING, choices=("none", "2x2", "4x4", "8x8"), default="none"),
        Param("dithering_strength", ParamKind.NUMBER, default=5.0),
    ),
)

RESIZE = Route(
    name="resize",
    method="POST",
    path="/resize",
    kind=RouteKind.SYNCHRONOUS,
    summary="Resize while staying pixel art. At most a halving or a doubling per call.",
    estimated_generations=0.1,
    params=(
        Param("description", ParamKind.STRING, required=True),
        _image("reference_image", required=True),
        Param(
            "reference_image_size",
            ParamKind.SIZE,
            required=True,
            size=SizeLimit(min_area=16 * 16, max_area=200 * 200),
        ),
        Param(
            "target_size",
            ParamKind.SIZE,
            required=True,
            size=SizeLimit(min_area=16 * 16, max_area=200 * 200),
        ),
        *CAMERA_PARAMS,
        Param("isometric", ParamKind.BOOLEAN, default=False),
        Param("oblique_projection", ParamKind.BOOLEAN, default=False),
        Param("no_background", ParamKind.BOOLEAN, default=False),
        _image("color_image"),
        _image("init_image"),
        Param("init_image_strength", ParamKind.NUMBER, default=150.0),
        SEED,
    ),
)

# ------------------------------------------------------------- interface and people

CREATE_UI_ASSET = Route(
    name="create-ui-asset",
    method="POST",
    path="/create-ui-asset",
    kind=RouteKind.RESOURCE,
    summary="A shape-based pixel-art UI panel. Pro pricing.",
    estimated_generations=30.0,
    result_id_field="ui_asset_id",
    poll_path="/ui-assets/{id}",
    asset_id_field="ui_asset_id",
    params=(
        Param("description", ParamKind.STRING, required=True, help="'wooden RPG panel'."),
        Param("image_size", ParamKind.SIZE, size=SizeLimit(min_side=192, max_side=688)),
        Param("pieces", ParamKind.STRING_LIST, help="Shape template, validated server side."),
        Param("elements", ParamKind.STRING_LIST, help="Named elements, auto-positioned."),
        _image("style_image"),
        Param("color_palette", ParamKind.STRING, help="'brown and gold'."),
        Param("no_background", ParamKind.BOOLEAN, default=True),
        Param("name", ParamKind.STRING),
        Param("project_id", ParamKind.STRING),
        SEED,
    ),
)

GENERATE_FONT_PRO = Route(
    name="generate-font-pro",
    method="POST",
    path="/generate-font-pro",
    kind=RouteKind.BACKGROUND_JOB,
    summary="A pixel font: a glyph atlas and a TTF. Fixed 25 generations.",
    estimated_generations=25.0,
    result_id_field="background_job_id",
    poll_path="/generate-font-pro/{id}",
    params=(
        Param("description", ParamKind.STRING, required=True, help="'warm orange arcade font'."),
        Param("weight", ParamKind.STRING, required=True, choices=("Bold", "Regular")),
        Param("glyph_px", ParamKind.INTEGER, default=16, help="8, 16, 32 or 64."),
        Param("font_name", ParamKind.STRING),
        SEED,
    ),
)

PORTRAIT_CHARACTER_PRO = Route(
    name="portrait-character-pro",
    method="POST",
    path="/portrait-character-pro",
    kind=RouteKind.BACKGROUND_JOB,
    summary="A bust portrait from a character, or a character from a portrait. Pro pricing.",
    estimated_generations=30.0,
    result_id_field="background_job_id",
    poll_path="/portrait-character-pro/{id}",
    params=(
        _image("image", required=True),
        Param(
            "direction",
            ParamKind.STRING,
            choices=("portrait_to_character", "character_to_portrait"),
            default="portrait_to_character",
        ),
        Param("view", ParamKind.STRING, choices=VIEW, default="low top-down"),
        Param("result_size", ParamKind.INTEGER, default=64, help="16, 32, 48, 64, 128 or 160."),
        SEED,
    ),
)

# -------------------------------------------------------------------------- account

GET_BALANCE = Route(
    name="balance",
    method="GET",
    path="/balance",
    kind=RouteKind.SYNCHRONOUS,
    summary="Subscription generations remaining, and USD credits. Free.",
    estimated_generations=0.0,
    params=(),
)


ROUTES: tuple[Route, ...] = (
    CREATE_IMAGE_PIXFLUX,
    CREATE_IMAGE_PIXEN,
    CREATE_IMAGE_BITFORGE,
    IMAGE_TO_PIXELART_PRO,
    CREATE_CHARACTER_V3,
    GENERATE_8_ROTATIONS_V3,
    CREATE_CHARACTER_ANIMATION,
    ANIMATE_WITH_TEXT_V3,
    CREATE_1_DIRECTION_OBJECT,
    CREATE_8_DIRECTION_OBJECT,
    CREATE_MAP_OBJECT,
    CREATE_TILESET,
    CREATE_TILESET_SIDESCROLLER,
    CREATE_TILES_PRO,
    CREATE_ISOMETRIC_TILE,
    EDIT_IMAGE_PIXEN,
    EDIT_IMAGES_V2,
    INPAINT_V3,
    REMOVE_BACKGROUND,
    UNZOOM,
    CORRECT_PIXELART,
    REDUCE_COLORS,
    RESIZE,
    CREATE_UI_ASSET,
    GENERATE_FONT_PRO,
    PORTRAIT_CHARACTER_PRO,
    GET_BALANCE,
)

BY_NAME: dict[str, Route] = {route.name: route for route in ROUTES}


def route(name: str) -> Route:
    """Look a route up by name, or say what the names are."""
    try:
        return BY_NAME[name]
    except KeyError:
        known = ", ".join(sorted(BY_NAME))
        raise KeyError(f"no route named {name!r}. Known routes: {known}") from None
