# DOC-103

# Screenshot Analysis Module

**Project:** AI Image Collection Management System

**Document:** DOC-103

**Module:** Screenshot Analysis

**Version:** 2.1

**Status:** Design Specification

**Depends on:**

DOC-005
DOC-007
DOC-008
DOC-010
DOC-011
DOC-012
DOC-014
DOC-205

---

# 1. Purpose

The Screenshot Analysis module determines whether an image contains characteristics consistent with a screenshot or captured screen content.

The module enriches the shared database with screenshot-related analysis results.

It does not move or rename files, create final collection directories, or make sorting decisions.

---

# 2. Module Responsibility

The module is responsible for analysing evidence associated with screenshot-like content, including:

* visible user-interface elements;
* game HUD elements;
* operating-system interface elements;
* application interface elements;
* filename indicators that may support screenshot detection;
* other screenshot-specific visual evidence defined by this module.

The module does not determine the semantic subject of the screenshot.

For example, identifying a screenshot does not by itself determine:

* which game is shown;
* which application produced it;
* which universe is represented;
* which character is shown;
* whether the image is a meme.

Those interpretations belong to other modules where applicable.

---

# 3. Module Independence

Screenshot Analysis is independently executable.

It requires a valid database file identity for the file being processed, but it does not require Scanner to be running at the same time or to have been executed immediately before it.

The module does not invoke other modules directly.

Persistent information produced by Screenshot Analysis is written to the shared database and may later be consumed by other modules.

For example:

```text
Scanner
    ↓
Database
    ↓
Screenshot Analysis
    ↓
Database
    ↓
IRL / Universe / other modules
```

The other modules do not need Screenshot Analysis to remain active.

---

# 4. Input

The module processes files that have a valid file identity in the database according to DOC-012.

Relevant input information may include:

```text
SHA512
current_path
filename
extension
width
height
```

The module may access the current filesystem file when image decoding or visual analysis is required.

A file may be processed only when the current binary state can be reliably associated with the database identity being analysed.

---

# 5. Output

Screenshot Analysis produces `Analysis Result` records as defined by DOC-005.

Initial result types may include:

```text
IS_SCREENSHOT
HAS_SYSTEM_UI
HAS_APPLICATION_UI
HAS_GAME_HUD
FILENAME_SUGGESTS_SCREENSHOT
```

Each result may include supporting metadata such as:

```text
file identity
module
feature
value
confidence where applicable
execution reference
analysis/model/rule metadata where useful for diagnostics
created_at
```

Such metadata is informational and is not an automatic stale-result mechanism. Module-result lifecycle and cleanup are governed by DOC-014 and DOC-205.

The logical ownership of these results belongs to Screenshot Analysis.

The module must not overwrite analysis results owned by other modules.

---

# 6. Definitions

## Screenshot

An image that contains evidence consistent with a captured display screen rather than purely rendered artwork or a conventional photograph.

The exact decision threshold is configurable or defined by the module implementation.

## System UI

Interface elements associated with an operating system.

Examples include:

```text
Android status bar
Windows taskbar
macOS Dock
Linux desktop panels
```

## Application UI

Interface elements belonging to an application.

Examples include:

```text
browser toolbars
Discord interface
Reddit interface
Pixiv interface
file explorer windows
```

The presence of application UI is evidence, not absolute proof that the entire image is a screenshot.

## Game HUD

Persistent or contextual game-interface elements visible during gameplay.

Examples include:

```text
minimap
health bar
mana/stamina bar
quest tracker
skill icons
inventory shortcuts
```

Game HUD evidence does not by itself identify the game or universe.

## Filename Screenshot Indicator

A filename containing terms commonly associated with screenshots or captures.

Examples include:

```text
Screenshot
Screen
Capture
Snip
截圖
スクリーンショット
```

Filename evidence is supporting evidence only and shall never be considered conclusive by itself.

---

# 7. Evidence Sources

The module may combine multiple evidence sources.

Examples:

```text
filename evidence
visual UI detection
system UI detection
application UI detection
game HUD detection
```

The implementation may assign different weights to individual sources.

The method used to combine evidence is implementation-specific, but the resulting confidence must reflect the module's actual assessment rather than merely counting detected indicators.

---

# 8. Confidence

Where the module provides an automatic confidence value, it shall represent the module's confidence in the corresponding result.

A confidence value does not constitute a user decision.

Module-specific thresholds may determine whether a result is considered strong enough for downstream processing, but Screenshot Analysis itself does not move or classify files based solely on its confidence.

---

# 9. Processing and Reprocessing

The module may avoid reprocessing a file when a valid current result already exists for the same binary identity and the current execution does not require a fresh calculation.

A change to the module implementation, model, analysis rules or configuration does not automatically clear results and does not automatically start a new analysis run.

When the user wants a complete recalculation using changed logic, the user shall use **DOC-205 – Module Result Cleanup Utility** to clear Screenshot Analysis results and then execute Screenshot Analysis again.

A different filesystem path does not invalidate an otherwise unchanged binary merely because the path changed.

If SHA512 changes, the result belongs to the previous binary identity and must not be reused for the new binary object.

---

# 10. Database Access

The module reads data required for its operation from the shared database and filesystem where appropriate.

It writes only data belonging to its documented responsibility, primarily `Analysis Result` and related execution information.

It does not modify Scanner-owned filesystem identity information except where a future shared standard explicitly permits it.

It does not modify user classifications or manual placement decisions.

---

# 11. Threading and Resource Usage

Parallel execution should be supported.

The number of workers should be configurable according to DOC-010 and the common configuration system.

The implementation should use available resources efficiently while respecting configured safety limits.

Expensive visual analysis should not require loading the complete collection into memory.

---

# 12. Processing Strategy

Where practical, inexpensive evidence sources should be evaluated before more expensive visual processing.

For example:

```text
filename / metadata evidence
        ↓
cheap visual checks
        ↓
detailed visual analysis when necessary
```

The implementation may use early-exit or staged analysis when this provides a meaningful performance benefit without reducing required accuracy.

---

# 13. Error Handling

If a file cannot be analysed safely:

* the failure shall be logged according to DOC-011;
* incomplete results shall not be published as valid analysis results;
* processing of unrelated files should continue when safe.

Typical recoverable problems include:

```text
unsupported image encoding
corrupted image
read failure
unexpected decoder error
```

---

# 14. Logging

Every execution shall create a Module Execution record and an execution log.

The summary should include, where applicable:

```text
processed
skipped
errors
execution duration
```

Detailed errors should identify the affected file where possible using its SHA512 and/or internal file identifier.

---

# 15. Interaction with Other Modules

Screenshot Analysis does not directly invoke or communicate with other modules.

Other modules may consume its results through the shared database.

Examples include:

```text
IRL Analysis
Reaction Image Analysis
AutoSort
Collection Consistency Checker
```

Such consumption does not create a runtime dependency on Screenshot Analysis.

A module may be executed multiple times while Screenshot Analysis is not executed, and vice versa, provided the required database data exists.

---

# 16. Sorting and Filesystem Operations

Screenshot Analysis shall not:

* move files;
* rename files;
* create or modify FINAL directory structures;
* create final destinations based on model output;
* modify user decisions.

The module may contribute evidence used by another module that performs such operations, but the responsibility for those operations remains with that module.

AI/transition workspace handling is likewise outside Screenshot Analysis unless explicitly assigned by a future module specification.

---

# 17. Performance Requirements

The module is intended for collections containing millions of files.

The implementation should:

* avoid unnecessary reprocessing;
* use staged/cheap evidence before expensive analysis where practical;
* process files independently so one failure does not stop the whole execution;
* avoid requiring the complete image collection in memory.

---

# 18. Future Extensions

Possible future extensions include:

* operating-system identification;
* game identification;
* application identification;
* UI element classification;
* OCR-assisted interface detection;
* screenshot-origin estimation.

These features may remain within this module if they remain part of the same logical responsibility, or may become separate modules if their scope becomes sufficiently independent to justify separation.

---

# 19. Acceptance Criteria

Screenshot Analysis is considered compliant when it can:

* process files with valid SHA512-based identities;
* detect screenshot-related evidence;
* record the defined initial analysis results in the shared database;
* include meaningful confidence information where applicable;
* reuse unchanged current results where appropriate;
* avoid automatic invalidation solely because the module/model/rules changed;
* support full recalculation through DOC-205 followed by a new module execution;
* respect SHA512 identity changes;
* continue after recoverable per-file errors;
* operate independently of other module processes;
* communicate persistent results through the shared database;
* perform no unauthorized filesystem sorting or classification operations.

---

# End of DOC-103
