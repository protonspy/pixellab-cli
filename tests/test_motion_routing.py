"""Which animation route a frame count reaches.

Two routes animate a loose frame and they do not overlap where it matters:
`animate-with-text-v3` stops at sixteen frames, `animate-pixminimax` reaches forty
and is priced by generation time. Sending twenty frames to the first is a rejection;
sending eight to the second is paying a beta route for what the cheap one does.
"""

import pytest

from pixellab_cli import prompts
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


class TestALooseAnimationNeedsAMotionToo:
    """`pixellab-cli animate` has no enhancer on its path at all, so writing the
    motion out is the only way to have one."""

    def test_is_thin_catches_a_label(self):
        assert prompts.is_thin("walking")

    def test_is_thin_catches_the_tag_form(self):
        assert prompts.is_thin("walking,loop,south")

    def test_is_thin_catches_the_tag_form_with_spaces(self):
        """Four tags is four words, which is the count the word check lets through."""
        assert prompts.is_thin("walking, loop, south, once")

    def test_a_sentence_with_commas_in_it_is_not_a_tag_list(self):
        assert not prompts.is_thin(
            "a full walk cycle, legs alternating through a stride, arms swinging opposite"
        )

    def test_a_described_motion_is_not_thin(self):
        assert not prompts.is_thin("a full walk cycle, legs alternating, arms swinging opposite")

    def test_a_label_is_refused(self):
        with pytest.raises(ValidationError):
            prompts.check_the_motion_is_described("walking", enhance=False, terse=False)

    def test_terse_lets_it_through(self):
        prompts.check_the_motion_is_described("walking", enhance=False, terse=True)

    def test_no_action_at_all_is_somebody_else_s_error(self):
        prompts.check_the_motion_is_described(None, enhance=False, terse=False)

    def test_the_suggested_command_carries_no_caller_text(self):
        """An agent reads these messages and runs what they suggest, and `repr` quotes
        for Python rather than for a shell: an action holding both kinds of quote comes
        back out in a form bash re-opens, and whatever followed it runs."""
        hostile = 'it\'s "x"$(touch pwned)'

        with pytest.raises(ValidationError) as raised:
            prompts.check_the_motion_is_described(hostile, enhance=False, terse=False)

        # The command this offers, and only that: the action is still named in the
        # sentence around it, which is diagnosis and is how every other refusal here
        # reads.
        suggested = raised.value.message.split("`")[1]
        assert 'enrich -a "<the action>"' in suggested
        assert "touch pwned" not in suggested


class TestWhetherAPoseSuitsAMotion:
    """The word test behind the pose refusal, on its own."""

    def test_a_walk_pose_suits_a_walk(self):
        assert prompts.suits("mid-stride walking pose, legs apart", "a full walk cycle")

    def test_an_idle_pose_does_not_suit_an_attack(self):
        assert not prompts.suits("idle standing pose, arms at rest", "an overhead sword attack")

    def test_a_shared_body_part_is_not_a_match(self):
        """ "head bowed" and "blade raised behind the head" share a head and nothing
        else, and a pose is identified by its motion rather than by a limb."""
        assert not prompts.suits(
            "an overhead attack wind-up, blade raised behind the head",
            "crouching slowly onto one knee, head bowed",
        )

    def test_a_word_matches_across_its_endings(self):
        assert prompts.suits("an attack wind-up", "attacking with a sword")

    def test_a_word_that_merely_starts_the_same_is_not_a_match(self):
        """`attack` and `attach` share four letters and are not the same motion, which
        is why this compares whole words with their endings off rather than prefixes."""
        assert not prompts.suits("idle stance, cloak attached at the back", "attacking")

    def test_a_doubled_consonant_still_matches(self):
        """`run` is shorter than `running` is after any truncation, so the two never
        met while this took a fixed prefix."""
        assert prompts.suits("character mid-run, legs extended", "running")

    def test_a_silent_e_still_matches(self):
        assert prompts.suits("a long stride, weight forward", "striding forward")
