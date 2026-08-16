# DOC-105A

# Cosplay Analysis Module

**Project:** AI Image Collection Management System

**Document:** DOC-105A

**Module:** Cosplay Analysis

**Version:** 2.0

**Status:** Draft

**Depends on:**

DOC-005
DOC-007
DOC-008
DOC-010
DOC-011
DOC-012
DOC-013

---

# 1. Purpose

The Cosplay Analysis module determines whether an image most likely depicts cosplay.

Cosplay is closely related to IRL analysis, but it is maintained as a separate module because it represents a distinct analytical problem with its own evidence, thresholds and downstream uses.

The module produces analysis results for use by other modules or later decision-making workflows.

It does not itself decide where an image belongs.

---

# 2. Relationship with IRL Analysis

Cosplay is a specialized subcategory of real-world imagery, but Cosplay Analysis is **not functionally dependent on IRL Analysis**.

The module may be run:

```text
IRL → Cosplay
```

when the user wants to limit work to likely real-world images.

It may also be run independently on:

```text
TODO
AI / Transition
FINAL validation scope
specific directories
user-selected subsets
```

The absence of an IRL result must not prevent Cosplay Analysis from running when the selected scope permits it.

The module may consume an existing IRL result as supporting evidence when this is documented by the implementation, but IRL Analysis does not need to be running and does not create a runtime dependency.

---

# 3. Responsibilities

The module shall:

* analyse images for cosplay characteristics;
* detect visual evidence consistent with intentional character-based costume presentation;
* provide confidence information where meaningful;
* write its results to the shared database;
* preserve the distinction between automatic analysis and user decisions.

The module shall not:

* identify the specific character as its primary responsibility;
* identify the universe or franchise as its primary responsibility;
* identify the photographer;
* move, rename or delete files as part of analysis;
* modify results owned by other modules;
* modify FINAL directory structure.

---

# 4. Scope

The module determines whether an image most likely represents cosplay.

Typical positive examples include:

```text
convention cosplay
studio cosplay
outdoor cosplay
event photography
staged character photography
```

Typical negative examples include:

```text
ordinary portraits
fashion photography
anime artwork
digital illustrations
game screenshots
ordinary costumes unrelated to fictional characters
```

The module is concerned with the **presence of cosplay**, not with proving the identity of the represented character.

---

# 5. Input

The module reads the current database state for eligible files.

Required information includes:

```text
SHA512
current filesystem state
image format where available
image dimensions where available
```

The module may access the corresponding image from the filesystem when visual analysis requires it.

It requires a valid file identity in the database.

It does not require Scanner to be running and never invokes Scanner or another module directly.

---

# 6. Output

The module produces **Analysis Results** as defined by DOC-005.

Initial feature set may include:

```text
IS_COSPLAY
LOOKS_LIKE_COSTUME
LOOKS_CHARACTER_INSPIRED
LOOKS_LIKE_CONVENTION
LOOKS_LIKE_STUDIO_COSPLAY
```

Not every feature must be populated for every file.

An Analysis Result should identify at least:

```text
file identity / SHA512
module
module version
feature
value
confidence where applicable
timestamp
```

A feature such as `LOOKS_LIKE_COSTUME` is supporting evidence. It is not by itself a final cosplay classification.

---

# 7. Definitions

## Cosplay

A real-world image depicting a person intentionally presenting an appearance associated with a fictional character, usually through clothing, accessories, makeup, props or styling.

Recognition of the specific character is outside the core responsibility of this module.

## Costume Evidence

Visual evidence indicating deliberate character-oriented clothing, accessories or styling.

## Character-Inspired Appearance

An appearance resembling a fictional character without sufficient evidence to establish full cosplay.

This is supporting evidence rather than a final classification.

## Convention Evidence

Visual or environmental evidence suggesting that the image was captured at an event where cosplay is commonly present.

The module does not need to identify the specific event.

## Studio Cosplay

Cosplay imagery likely produced in a controlled photographic environment.

Studio characteristics are supporting evidence and do not independently prove cosplay.

---

# 8. Confidence

Where the module produces a classification-like result, it should provide a confidence value.

Confidence represents the strength of the evidence that the image depicts cosplay.

It is not a user decision.

The exact calculation method is implementation-defined.

A low-confidence result should normally remain an analysis result rather than becoming an automatic placement decision.

Where the module cannot safely distinguish cosplay from ordinary photography, Review Queue may be used according to DOC-013.

---

# 9. Processing Rules

The module may be executed repeatedly and independently.

For a given binary identity and module/analysis version, an existing valid current result should normally be reused instead of recalculated unnecessarily.

Reprocessing may occur when:

* the file has a different SHA512;
* the module version changed;
* the relevant analysis rule/model version changed;
* the current result is invalid or superseded;
* the user or reprocessing system explicitly requests recalculation.

A rename or move without a SHA512 change does not by itself invalidate the analysis.

If the SHA512 changes, results belonging to the previous binary identity remain associated with that previous identity and must not be treated as results for the new binary object.

---

# 10. Database Access

The module reads information needed for analysis from the shared database and may read the corresponding image from the filesystem.

The module writes only data belonging to its documented responsibility, primarily Analysis Results and execution-related state.

It must not overwrite Scanner state, another module's analysis results or user decisions.

---

# 11. Performance Requirements

The module shall remain suitable for collections containing millions of images.

Implementation should use efficient inference appropriate for batch processing and should avoid expensive processing when reliable existing results can be reused.

The module should not require the entire collection to be loaded into memory.

---

# 12. Threading and Resource Usage

Parallel execution shall be supported.

The worker count shall be configurable according to the common module interface.

The module should use available system resources efficiently without exhausting configured limits.

Parallel execution must not create conflicting database or filesystem operations.

---

# 13. Error Handling

If analysis of an individual file cannot be completed:

* the error shall be logged according to DOC-011;
* processing of other eligible files should continue where safe;
* incomplete or invalid results shall not be published as valid Analysis Results.

Typical recoverable errors include:

```text
unsupported image encoding
corrupted image
filesystem read failure
insufficient access
unexpected decoding error
```

---

# 14. Logging

Each execution shall create a Module Execution record and summary log.

The summary should include, where applicable:

```text
started
finished
processed
skipped
errors
duration
```

Detailed errors should identify the affected file identity/path where safe.

---

# 15. Interaction with Other Modules

The module does not invoke other modules directly.

Its communication model is:

```text
Database
    ↓
Cosplay Analysis
    ↓
Database
```

Other modules may consume its Analysis Results later.

The module is executionally independent of:

```text
Color Analysis
Screenshot Analysis
Reaction Analysis
IRL Analysis
Universe Analysis
Character Analysis
```

IRL Analysis may be used as a practical pre-filter, but this is a workflow optimization rather than a dependency.

---

# 16. Design Philosophy

Cosplay Analysis is an information provider.

Its purpose is to provide useful evidence that a real-world image depicts cosplay while minimizing false positives.

The module should prefer uncertainty over an overconfident classification when evidence is ambiguous.

A cosplay result does not itself determine the final collection location.

---

# 17. Review Queue Integration

Where the module cannot determine cosplay status with sufficient confidence, it may create a Review Queue case according to DOC-013.

A Review Queue suggestion is not a filesystem command.

A user decision remains authoritative for the relevant decision context.

Manual correction of cosplay status must not be silently overwritten by later automatic processing for the same protected context.

---

# 18. FINAL and AI Handling

Cosplay Analysis does not decide physical placement.

If a later processing module uses cosplay results:

* automatic movement into FINAL is allowed only where the destination already exists in Collection Definition and the applicable module is authorized to perform the move;
* a new FINAL directory must not be created automatically by the analysis module;
* AI/transition workspaces may be extended with new working directories when an authorized processing workflow permits it and its configured confidence threshold is met.

---

# 19. Future Extensions

Possible future extensions include:

* improved costume evidence detection;
* prop detection;
* wig/hairpiece analysis;
* convention-context analysis;
* pose/context analysis;
* stronger distinction between cosplay and ordinary costume photography.

Character identification, universe identification and photographer identification may be handled by other modules.

Future extensions should remain inside this module when they are still part of the single logical responsibility of cosplay detection.

---

# 20. Acceptance Criteria

The module is considered compliant when it can:

* identify likely cosplay images;
* distinguish cosplay from ordinary photography with useful confidence;
* operate on user-selected scopes without requiring IRL Analysis to run first;
* write results using the Analysis Result model;
* associate results with the correct SHA512 binary identity;
* support independent repeated executions;
* continue after recoverable per-file failures;
* avoid modifying files as part of analysis;
* expose results to other modules through the shared database;
* preserve user decisions through Review Queue and manual override rules.

---

# End of DOC-105A
