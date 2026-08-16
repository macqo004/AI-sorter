# DOC-105

# IRL Analysis Module

**Project:** AI Image Collection Management System

**Document:** DOC-105

**Module:** IRL Analysis

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

The IRL Analysis module determines whether an image most likely represents real-world subject matter rather than artwork or a digitally created illustration.

The module provides analysis results for use by other modules. It does not decide where an image belongs and does not itself move, rename or delete files.

---

# 2. Responsibilities

The module shall:

* analyse images for visual characteristics associated with real-world imagery;
* distinguish likely photographic imagery from illustration where the available evidence supports that distinction;
* provide confidence information where meaningful;
* write its results to the shared database;
* preserve the distinction between automatic analysis and later user decisions.

The module shall not:

* identify anime characters or universes;
* perform cosplay analysis as its primary responsibility;
* move or rename files as part of analysis;
* modify folder structures;
* overwrite results owned by other modules;
* treat its result as a filesystem command.

---

# 3. Scope

The module evaluates whether an image is likely to represent the physical world.

Typical positive examples include:

```text
people
animals
vehicles
buildings
landscapes
food
products
interiors
outdoor photographs
```

Typical negative examples include:

```text
anime artwork
manga
fanart
CG illustrations
digital paintings
stylized game artwork
```

The module does not need to determine a detailed semantic category such as person, vehicle or landscape unless such a capability is explicitly added to this module in a future revision.

---

# 4. Input

The module reads the current database state for eligible files.

Required information includes:

```text
SHA512
current filesystem state
image format where available
image dimensions where available
```

The module may access the filesystem to decode the image or obtain information required for analysis.

A valid file identity in the database is required. The module does not require Scanner to be running and does not invoke Scanner or any other module directly.

---

# 5. Output

The module produces **Analysis Results** according to DOC-005.

Initial feature set may include:

```text
IS_IRL
LOOKS_PHOTOGRAPHIC
LOOKS_ILLUSTRATED
```

`NEEDS_MANUAL_REVIEW` should not be treated as an ordinary visual fact when it merely represents the module's uncertainty. Where practical, uncertainty should instead be represented through confidence and/or Review Queue according to DOC-013.

Each Analysis Result should identify at least:

```text
file identity / SHA512
module
module version
feature
value
confidence where applicable
timestamp
```

---

# 6. Definitions

## IRL

An image primarily representing people, objects or environments existing in the physical world.

The term describes the content category used by the project; it does not imply that the image must be a camera photograph.

## Photographic Appearance

Visual characteristics commonly associated with photographic capture, including but not limited to natural texture, lighting and perspective.

## Illustrated Appearance

Visual characteristics commonly associated with manually or digitally created artwork.

## Uncertainty

A condition in which the available evidence is insufficient to make a reliable automatic decision.

Uncertainty is a normal analysis outcome and is not itself an error.

---

# 7. Confidence

Where a classification-like result is produced, the module should provide a confidence value.

Confidence represents the strength of the available evidence, not a user decision.

The exact calculation method is implementation-defined.

Low confidence does not authorize the module to guess. Where a downstream action requires a decision, the relevant workflow shall use its configured threshold and Review Queue rules.

---

# 8. Processing Rules

The module may process the same file in multiple independent executions.

For a given binary identity and a given module/analysis version, an existing valid current result should normally be reused rather than recalculated unnecessarily.

A new execution may recalculate results when:

* the file has a different SHA512;
* the module version changed;
* the relevant analysis rule/model version changed;
* the existing result is invalid or superseded;
* the user or reprocessing workflow explicitly requests recalculation.

A path or filename change without a SHA512 change does not by itself invalidate the analysis result.

If SHA512 changes, results belonging to the previous binary identity remain associated with that previous identity and are not silently transferred to the new binary object.

---

# 9. Scan Scope

The module shall support configurable processing scope.

The scope may include, depending on configuration and module purpose:

```text
configured source roots
transition/AI workspace
selected final roots for validation
specific collection/root
user-selected subset
```

The module shall not hard-code directory names or assume that `TODO`, `AI` or `FINAL` have universal physical meanings.

Processing scope is configuration, while file eligibility is determined from current database and filesystem state.

---

# 10. Interaction with Other Modules

IRL Analysis does not invoke other modules.

Its communication model is:

```text
Database
    ↓
IRL Analysis
    ↓
Database
```

Other modules may later read its Analysis Results.

The module is execution-independent from Color Analysis, Screenshot Analysis, Reaction Analysis, Cosplay Analysis, Universe Analysis and Character Analysis.

For example, the following sequence is valid:

```text
IRL Analysis × 5
Screenshot Analysis × 2
IRL Analysis × 1
```

The module may also consume documented database results from other modules when useful, without creating a runtime dependency on those modules.

---

# 11. Database Access

The module reads information required for analysis from the shared database and may read corresponding image files.

The module writes only data belonging to its documented responsibility, primarily Analysis Results and execution-related state.

It must not overwrite Scanner state, unrelated analysis results or user decisions.

---

# 12. Performance and Resource Usage

The module shall be suitable for collections containing millions of images.

Implementation should favour efficient inference suitable for large datasets.

Expensive visual analysis should be avoided when a cheaper valid path can establish the required result.

The module should use available CPU, GPU and memory resources efficiently within configured system limits and must not require the entire collection to be held in memory.

---

# 13. Threading

Parallel execution shall be supported.

Worker count shall be configurable through the common module configuration/interface.

The module must maintain database consistency when multiple workers operate concurrently.

---

# 14. Error Handling

If an image cannot be analysed:

* the error shall be logged according to DOC-011;
* processing of other files should continue where safe;
* incomplete or invalid Analysis Results shall not be published as valid results.

Typical recoverable failures include:

```text
corrupted image
unsupported encoding
temporary filesystem read failure
insufficient access
unexpected decoding/model error
```

Uncertainty in the classification itself is not treated as a processing error.

---

# 15. Logging

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

Detailed errors should identify the affected file identity/path where safe to do so.

---

# 16. Design Philosophy

IRL Analysis is an information-provider module.

Its purpose is to produce useful evidence while minimizing false-positive classifications.

When evidence is insufficient, the module should prefer uncertainty over an unjustified positive or negative classification.

The module does not decide whether an image should be removed, moved to AI, moved to FINAL or otherwise changed.

Those decisions belong to processing/user workflows that consume the analysis result.

---

# 17. Relationship with Other Analysis

IRL Analysis may independently consume documented results from other analysis modules when these results improve its own analysis.

For example, Color Analysis or Screenshot Analysis may provide supporting evidence.

Such consumption occurs through the shared database and does not mean that the producing module must be executed immediately beforehand or remain running.

No analysis module may directly invoke another module merely to obtain a result.

---

# 18. Review Queue and User Decisions

If IRL Analysis produces a result whose uncertainty requires explicit user intervention for a later action, the downstream workflow may create a Review Queue item according to DOC-013.

An analysis result does not itself constitute a user decision.

A later user correction has higher priority than a later automatic IRL result for the same decision context.

IRL Analysis must not modify or undo a user-selected filesystem destination merely because its later model output differs.

---

# 19. FINAL and AI Handling

IRL Analysis does not manage final directory structures.

If later processing uses the result to organize files:

* existing FINAL destinations must come from Collection Definition or explicit user action;
* AI/transition workspaces may receive new working directories when the responsible processing module is authorized to create them and its configured confidence threshold is met;
* IRL Analysis itself does not create FINAL directories.

---

# 20. Future Extensions

Possible future extensions include:

* improved photographic/illustration discrimination;
* specialized scene recognition;
* source-specific photography detection;
* additional confidence calibration;
* improved handling of mixed photographic/illustrated content.

Features that constitute a genuinely independent analysis responsibility should be documented as separate modules rather than added indiscriminately to IRL Analysis.

---

# 21. Acceptance Criteria

The module is considered compliant when it can:

* distinguish likely real-world imagery from artwork with documented confidence;
* produce results using the current Analysis Result model;
* associate results with the correct SHA512 binary identity;
* reuse valid results when appropriate;
* support independent repeated executions;
* support configurable processing scope;
* continue after recoverable per-file errors;
* operate efficiently on very large collections;
* communicate with other modules only through documented shared database state;
* avoid modifying files or final directory structures as part of analysis.

---

# End of DOC-105
