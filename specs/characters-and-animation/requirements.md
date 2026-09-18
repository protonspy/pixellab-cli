---
autonomy: auto
ci: wait
branch: feat/interpolate-between-poses
delivery: in-progress
pr: 34
---

# Characters and animation — requirements

## Purpose

A character is the one asset in this tool with a life longer than a call. It gets an
identifier PixelLab keeps, eight rotations, a skeleton, and animations added to it
over time — so the commands here are as much about referring to something that
already exists as about making something new. Objects are the same shape with a
different endpoint family and no skeleton.

## R1 · Creating

- **R1.1** When asked for a character, the character commands shall create one from a description, or from a south-facing reference sprite when one is given, and shall write every rotation returned.
- **R1.2** The character commands shall report the character identifier PixelLab assigned, and shall record it in the manifest.
- **R1.3** The character commands shall name each rotation file after the direction it shows.
- **R1.4** When asked for an object, the character commands shall create one from a description, in one direction or in eight.
- **R1.5** (ADDED) When asked for a state of an existing character, the character commands shall apply a text edit to that character's rotations, shall write every rotation returned, and shall report the identifier of the new character and the group it shares with the character it came from.
- **R1.6** (ADDED) The character commands shall say that a character state is priced as a Pro Tools route before calling it.
- **R1.7** (ADDED) Where four rotations are asked for, the character commands shall create the character on the four-direction route and shall write south, east, north and west.
- **R1.8** (ADDED) Where four rotations are asked for, the character commands shall accept an outline style, a shading style and a detail level.
- **R1.9** (ADDED) Where four rotations are asked for, if a reference sprite is given whose dimensions differ from the frame size, then the character commands shall refuse the call and name both sizes, before spending anything.

## R2 · Animating

- **R2.1** (MODIFIED) When asked to animate a character, the character commands shall animate it by action description, or by named template where one is given, over the directions asked for.
- **R2.2** (MODIFIED) The character commands shall report, before the call, that an animation costs its tier once per direction, and shall estimate an animation driven by an action description at one generation per frame per direction.
- **R2.3** Where a named animation template is not in the catalogue the tool carries, the character commands shall warn that the catalogue is partial and send it anyway, and shall print the catalogue when the provider rejects it.
- **R2.4** When asked to animate a loose image rather than a character, the character commands shall use the route that takes a first frame, and shall write the frames in playback order.
- **R2.5** (ADDED) Where more frames are asked for than the default animation route accepts, the character commands shall use the long-form animation route, and shall say that the route is in beta and needs a subscription tier the account may not hold.
- **R2.6** (ADDED) If a frame count is given that the chosen animation route does not accept, then the character commands shall say so and name the counts that route accepts, before spending anything.
- **R2.7** (ADDED) Where the long-form animation route is used, the character commands shall report that it is priced by generation time rather than by a fixed tier, so that the estimate is a weaker claim than usual.
- **R2.8** (MODIFIED) The character commands shall animate an action from its description whether or not the character has a skeleton knowing a motion of that name.
- **R2.9** (MODIFIED) Where a named template is given, the character commands shall say that a template animates from the character's skeleton and that the provider does not currently return correct frames for it.
- **R2.10** (MODIFIED) While a dry run is asked for, the character commands shall report the estimate the real call would be charged.
- **R2.11** (MODIFIED) If the character named cannot be read, then the character commands shall say so before spending anything.

- **R2.12** (ADDED) Where a start pose is given, the character commands shall animate from that pose instead of from the character's rotation for the direction.
- **R2.13** (ADDED) Where a start pose names a character, the character commands shall take the pose from that character's rotation for the direction being animated.
- **R2.14** (ADDED) If a start pose names a character that has no rotation for a direction asked for, then the character commands shall refuse the call and name the directions that character does have, before spending anything.
- **R2.23** (ADDED) If a pose is given for more than one direction at once, then the character commands shall refuse the call and say that a posed animation carries one direction per call, before spending anything.
- **R2.15** (ADDED) Where an end pose is given as well, the character commands shall animate between the two poses and shall say that the animation interpolates rather than following the action alone.
- **R2.16** (ADDED) If a pose is given together with a named template, then the character commands shall refuse the call and say that a pose belongs to the described-action route, before spending anything.
- **R2.17** (ADDED) Where enrichment is asked for on an animation, the character commands shall have the provider expand the action description as part of that call.
- **R2.18** (ADDED) When asked to enrich an action description, the character commands shall send the pose and the action to the prompt enhancer and shall report the enriched description without animating anything.
- **R2.19** (ADDED) Where a pose to enrich from names a character, the character commands shall take the frame from that character's rotation for the direction asked for.
- **R2.20** (ADDED) Where an end pose is given to enrich from, the character commands shall ask the enhancer for the motion between the two poses.
- **R2.21** (ADDED) The character commands shall report what the prompt enhancer costs before calling it.
- **R2.22** (ADDED) If asked to enrich an action description with no pose, then the character commands shall refuse the call and say that the enhancer reads a frame, before spending anything.
- **R2.24** (ADDED) The character commands shall keep the frame an animation starts on as its first frame, unless asked to store only the frames generated.
- **R2.25** (ADDED) The character commands shall report, before the call, how many frames the animation will hold, counting the kept starting frame.

- **R2.26** (ADDED) When asked to interpolate between two images, the character commands shall generate the transition between them from a description of the motion, and shall write the frames returned in playback order.
- **R2.27** (ADDED) The character commands shall say that interpolating is priced as a Pro Tools route, and that the route decides how many frames it returns, before calling it.
- **R2.28** (ADDED) If the two images given to interpolate differ in size, then the character commands shall refuse the call and name both sizes, before spending anything.
- **R2.29** (ADDED) If an image given to interpolate is outside the size the interpolation route accepts, then the character commands shall refuse the call and name that route's limit, before spending anything.
- **R2.30** (ADDED) If a frame count is given for an interpolation, then the character commands shall refuse the call and say that the interpolation route decides its own frame count, before spending anything.

## R3 · Rotating

- **R3.1** When asked to rotate an image, the character commands shall generate eight directional views of it and write each one named after its direction.

## R4 · Referring to what exists

- **R4.1** The character commands shall list the characters and objects on the account.
- **R4.2** The character commands shall show one character's rotations, animations and settings.
- **R4.3** When asked for a spritesheet, the character commands shall download the sheet and its layout file and write both to the workspace.
- **R4.4** Where a command names an asset that does not exist, the character commands shall say so rather than reporting an empty result.

## Out of scope

- Deleting anything. This tool never removes a remote asset.
- Skeleton editing and skeleton-driven animation.
- Paperdolling and layered characters. A character state is a new character grouped with its source, not a layer composited over one.
