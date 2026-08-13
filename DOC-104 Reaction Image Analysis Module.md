DOC-104
Reaction Image Analysis Module

Project: AI Image Framework (working title)

Document: DOC-104

Module: Reaction Image Analysis

Version: 1.0 Draft

Status: Draft

Depends on

DOC-001
DOC-002
DOC-003
DOC-004
DOC-005
DOC-006
DOC-101
1. Purpose

The Reaction Image Analysis module identifies images that are unlikely to be useful for artwork classification.

The module detects images commonly used as reactions, emojis or utility graphics.

Its purpose is to enrich the database with observations that may later be used by AutoSort or other decision-making components.

The module never moves, renames or deletes files.

2. Responsibilities

The module SHALL:

analyse images for reaction-image characteristics;
detect emojis and emotes;
detect small utility graphics;
detect images primarily intended for online communication;
write observations to the database;
assign confidence values.

The module SHALL NOT:

detect anime characters;
detect universes;
detect screenshots;
detect real-life photographs;
detect image quality;
modify filesystem contents.
3. Scope

The module analyses whether an image belongs to the category of reaction or utility graphics.

Typical examples include:

Discord emoji;
Twitch emotes;
reaction faces;
sticker-like graphics;
internet reaction images;
simplified expressive faces.

The module does not attempt to determine the origin or meaning of the reaction.

4. Input

The module reads:

Image
File
Scanner metadata
Current SHA-512

Image decoding is performed only when required.

5. Output

The module produces Observations.

Initial feature set:

IsReactionImage

IsEmoji

IsEmote

HasMinimalScene

HasSingleSubject

HasLargeTransparentArea

IsUtilityImage

Each Observation shall contain:

ImageID
ModuleID
Feature
Value
Confidence
Timestamp
6. Definitions
Reaction Image

An image primarily intended to express emotion, opinion or reaction during online communication.

Typical examples:

reaction memes;
expressive faces;
animated sticker frames;
internet reaction graphics.
Emoji

A small symbolic image intended to represent an emotion, object or concept.

Emote

A platform-specific reaction image used in online communities.

Examples include:

Discord
Twitch
YouTube
Slack
Utility Image

A non-illustrative image created primarily for communication rather than artistic presentation.

Minimal Scene

An image containing little or no environmental context.

Typically consists of:

single object;
single face;
isolated symbol;
transparent background.
7. Confidence

Every Observation shall include a confidence value.

Confidence represents the module's certainty.

The calculation method is implementation-defined.

8. Processing Rules

The module analyses each unique SHA-512 only once.

Existing observations for the current SHA-512 shall prevent unnecessary reprocessing.

If the SHA-512 changes, observations produced by this module become obsolete and shall be recalculated.

9. Database Access

The module reads:

Image
File
Module

The module writes:

Observation

The module never modifies Scanner data.

10. Performance Requirements

The module shall be suitable for collections containing millions of images.

Implementation shall prioritise computationally inexpensive methods before more expensive image analysis.

Repeated processing of identical SHA-512 values shall be avoided.

11. Threading

Parallel execution shall be supported.

The number of worker threads shall be configurable.

12. Error Handling

If analysis cannot be completed:

processing of other images shall continue;
the error shall be logged;
incomplete observations shall not be stored.
13. Logging

Each execution produces a summary log.

Example:

Reaction Analysis

Started:
2026-07-18 12:00

Processed:
24,318

Skipped:
4,945,210

Errors:
1

Duration:
00:02:04

Detailed errors shall follow the summary.

14. Performance Philosophy

The implementation shall prefer lightweight heuristics capable of identifying obvious reaction images with high confidence.

Complex semantic understanding is intentionally excluded from Version 1.

15. Interaction with Other Modules

The module depends only on Scanner.

It is completely independent of:

Color Analysis
Screenshot Analysis
IRL Analysis
Universe Analysis
Character Analysis

Other modules may consume its observations.

The module shall never invoke another module directly.

16. Design Philosophy

The purpose of this module is not to identify every possible meme.

Its goal is to remove obvious non-artwork images from later processing stages by providing reliable observations.

When uncertainty exists, the module should prefer leaving the image unclassified rather than producing a false positive.

17. Future Extensions

The following capabilities are intentionally excluded from Version 1:

meme template recognition;
OCR;
caption analysis;
internet meme classification;
social-media specific detection;
animated GIF analysis;
comic strip recognition.

These capabilities may be implemented by separate modules in future versions.

18. Acceptance Criteria

The module shall be considered complete when it can:

detect common reaction images;
detect emojis;
detect emotes;
detect simple utility graphics;
write observations to the database;
skip previously analysed SHA-512 values;
recover gracefully from processing errors;
process very large image collections efficiently.
End of DOC-104