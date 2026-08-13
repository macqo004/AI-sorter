DOC-103
Screenshot Analysis Module

Project: AI Image Framework (working title)

Document: DOC-103

Module: Screenshot Analysis

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

The Screenshot Analysis module determines whether an image is likely to represent a screenshot.

The module enriches the database with screenshot-related observations.

The module performs no file operations and makes no sorting decisions.

2. Responsibilities

The module SHALL:

analyse images for screenshot characteristics;
analyse filenames for screenshot indicators;
detect visible user interface elements;
store screenshot-related observations;
assign a confidence value to each observation.

The module SHALL NOT:

move files;
rename files;
classify anime;
classify characters;
detect memes;
determine image quality;
modify observations created by other modules.
3. Scope

The module evaluates only evidence related to screenshots.

It does not determine:

which operating system produced the screenshot;
which game is shown;
which application is visible;
which anime is displayed.

These responsibilities belong to future specialised modules.

4. Input

The module reads:

Image
File
Scanner metadata
Current SHA-512

The module accesses the image only when visual analysis is required.

5. Output

The module produces Observations.

Initial feature set:

IsScreenshot

HasSystemUI

HasApplicationUI

HasGameHUD

FilenameSuggestsScreenshot

Each Observation shall contain:

ImageID
ModuleID
Feature
Value
Confidence
Timestamp
6. Definitions
Screenshot

An image that most likely represents a captured screen rather than artwork or a photograph.

System UI

Visual elements provided by an operating system.

Examples include:

Android status bar
iOS status bar
Windows taskbar
macOS Dock
Linux desktop panels
Application UI

Visual interface elements belonging to desktop or mobile applications.

Examples include:

browser toolbars;
Discord interface;
Reddit interface;
Pixiv interface;
file explorer windows.
Game HUD

Persistent interface elements visible during gameplay.

Typical examples:

minimap;
health bar;
mana or stamina bar;
quest tracker;
skill icons;
inventory shortcuts.
Filename Suggestion

A filename containing words commonly associated with screenshots.

Typical examples:

Screenshot

Screen

Capture

Snip

截圖

スクリーンショット

Filename evidence shall be treated only as supporting information.

It shall never be considered conclusive on its own.

7. Confidence

Every Observation shall include a confidence score.

Confidence expresses how strongly the available evidence supports the observation.

The calculation method is implementation-defined.

8. Processing Rules

The module analyses each unique SHA-512 only once.

If valid observations already exist for the current SHA-512, the image shall be skipped.

If the SHA changes, all observations produced by this module become obsolete and shall be recalculated.

9. Evidence Sources

The module may use multiple independent evidence sources.

Examples include:

filename analysis;
image analysis;
user interface detection;
HUD detection.

Each source contributes to the final confidence score.

The weighting of evidence is implementation-defined.

10. Database Access

The module reads:

Image
File
Module

The module writes:

Observation

The module does not modify Scanner data or observations created by other modules.

11. Threading

Parallel execution shall be supported.

The number of worker threads shall be configurable.

12. Error Handling

If an image cannot be analysed:

the error shall be logged;
processing continues;
no incomplete observation shall be written.
13. Logging

Each execution produces a summary log.

Example:

Screenshot Analysis

Started:
2026-07-18 11:00

Processed:
48,912

Skipped:
4,921,034

Errors:
5

Duration:
00:05:17

Detailed error information shall follow the summary.

14. Performance Requirements

The module shall prioritise computationally inexpensive evidence sources before performing more expensive image analysis.

Repeated analysis of identical SHA-512 values shall be avoided.

The implementation shall remain suitable for collections containing millions of images.

15. Interaction with Other Modules

The Screenshot Analysis module depends only on Scanner.

It is independent of:

Color Analysis
Meme Analysis
IRL Analysis
Universe Analysis

Future modules may consume its observations.

The module shall never invoke another module directly.

16. Design Philosophy

The module does not decide whether an image should be moved.

Its responsibility is limited to collecting evidence related to screenshots.

Decision-making belongs to later processing stages.

17. Future Extensions

Potential future capabilities include:

operating system identification;
game identification;
application identification;
UI element classification;
OCR-assisted interface detection;
screenshot origin estimation.

These features are intentionally excluded from Version 1.

18. Acceptance Criteria

The module shall be considered complete when it can:

identify likely screenshots;
detect common interface elements;
recognise filename-based screenshot hints;
write observations to the database;
skip previously analysed SHA-512 values;
recover gracefully from processing errors;
operate efficiently on multi-million image collections.
End of DOC-103