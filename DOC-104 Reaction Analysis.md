# DOC-104

# Reaction Image Analysis Module

**Project:** AI Image Collection Management System

**Document:** DOC-104

**Module:** Reaction Image Analysis

**Version:** 2.0

**Status:** Draft

**Depends on:**

DOC-005
DOC-007
DOC-008
DOC-010
DOC-011
DOC-012

---

# 1. Purpose

The Reaction Image Analysis module identifies images that are primarily intended for reactions, communication, emotes, emojis or simple utility use rather than ordinary artwork classification.

The module produces analysis results for later modules. It does not itself decide whether an image should be removed, moved or excluded from the collection.

---

# 2. Responsibilities

The module shall:

* analyse images for reaction-image characteristics;
* detect emoji- or emote-like graphics where supported;
* detect simple utility graphics where supported;
* detect visual patterns strongly associated with reaction images;
* write its results to the shared database;
* provide confidence information where meaningful;
* preserve the distinction between automatic analysis and later user decisions.

The module shall not:

* identify anime characters or universes;
* perform screenshot classification as its primary responsibility;
* determine whether an image is an IRL photograph;
* move, rename or delete files as part of analysis;
* modify results owned by other modules;
* create or modify FINAL directory structures.

---

# 3. Scope

The module evaluates whether an image belongs to the broad category of reaction or utility graphics.

Typical examples include:

```text
reaction faces
Discord-style emoji
Twitch-style emotes
sticker-like graphics
simple expressive graphics
small utility graphics
internet reaction images
```

The module does not need to determine the original source platform or cultural meaning of a reaction image.

A result such as `IS_REACTION_IMAGE = TRUE` is an analysis result, not an instruction to remove or move the file.

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

The module requires a valid file identity in the database. It does not require Scanner to be running and does not invoke Scanner or any other module directly.

---

# 5. Output

The module produces **Analysis Results** as defined by DOC-005.

Initial feature set may include:

```text
IS_REACTION_IMAGE
IS_EMOJI
IS_EMOTE
HAS_MINIMAL_SCENE
HAS_SINGLE_SUBJECT
HAS_LARGE_TRANSPARENT_AREA
IS_UTILITY_IMAGE
```

Not every feature must be populated for every file. A feature is used only where the module has sufficient evidence to evaluate it.

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

---

# 6. Definitions

## Reaction Image

An image primarily intended to express emotion, opinion or reaction in a communication context.

Typical examples include expressive faces, reaction graphics and simple reaction memes.

## Emoji

A small symbolic graphic representing an emotion, object or concept.

## Emote

A platform or community-specific reaction graphic used as a communication element.

Examples may include Discord, Twitch, YouTube or Slack style emotes.

## Utility Image

A graphic primarily created for communication or practical use rather than ordinary artwork presentation.

## Minimal Scene

An image containing little environmental context, often consisting primarily of one object, face, symbol or isolated subject.

These characteristics are supporting evidence and do not by themselves define a reaction image.

---

# 7. Confidence

Where the module produces a classification-like result, it should provide a confidence value.

Confidence represents the strength of the module's evidence, not a user decision.

The exact calculation method is implementation-defined.

A high-confidence reaction classification does not authorize the module to move or delete the file.

---

# 8. Processing Rules

The module may process the same file in multiple independent executions.

For a given binary identity and a given module/analysis version, an existing valid current result should normally be reused rather than recalculated unnecessarily.

A new execution may recalculate results when:

* the file has a different SHA512;
* the module version changed;
* the relevant analysis rule/model version changed;
* the existing result is invalid or superseded;
* the user or reprocessing system explicitly requests recalculation.

A change of path or filename without a SHA512 change does not by itself invalidate the analysis result.

If the SHA512 changes, results belonging to the previous binary identity remain historical and do not become results for the new binary object.

---

# 9. Database Access

The module reads information required for analysis from the shared database and may read the corresponding image from the filesystem.

The module writes only data belonging to its documented analysis responsibility, primarily Analysis Results and execution-related state.

It must not overwrite Scanner state, another module's analysis results or user decisions.

---

# 10. Performance Requirements

The module shall remain suitable for collections containing millions of images.

Implementation should prefer inexpensive and reliable evidence before more expensive visual analysis where practical.

Repeated processing of a binary identity with an already valid current result should be avoided unless reprocessing is required.

The module should not require the entire collection to be loaded into memory.

---

# 11. Threading and Resource Usage

Parallel execution shall be supported.

The worker count shall be configurable according to the common module interface.

The module should use available resources efficiently without exhausting configured system limits.

Parallel processing must not produce conflicting database or filesystem operations.

---

# 12. Error Handling

If a file cannot be analysed:

* the error shall be logged according to DOC-011;
* processing of other files should continue where safe;
* incomplete or invalid Analysis Results shall not be published as valid results.

Typical recoverable errors include:

```text
unsupported image encoding
corrupted image
filesystem read failure
insufficient access
unexpected decoding error
```

---

# 13. Logging

Each execution shall create a Module Execution record and a summary log.

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

# 14. Interaction with Other Modules

The module does not invoke other modules.

Its communication model is:

```text
Database
    ↓
Reaction Analysis
    ↓
Database
```

Other modules may later read its Analysis Results from the database.

The module is independent from Color Analysis, Screenshot Analysis, IRL Analysis, Universe Analysis and Character Analysis at execution level.

Another module may use Reaction Analysis results as input without requiring Reaction Analysis to be running.

---

# 15. Design Philosophy

The module is an information provider.

Its primary objective is to provide useful evidence about reaction/utility graphics while minimizing false positives.

When evidence is weak or ambiguous, the module should prefer an uncertain or negative analysis result over an overconfident classification.

Where a decision has material consequences for the collection, later processing should use Review Queue according to DOC-013 rather than treating an analysis result as an automatic command.

---

# 16. Scope Boundaries

The following are intentionally outside the core responsibility of Version 2.0:

* full meme-template recognition;
* OCR-based caption interpretation;
* internet-platform provenance detection;
* detailed semantic interpretation of reaction meaning;
* complete animated media understanding;
* broad social-media classification.

Such functionality may be added later if it remains logically part of reaction/utility analysis; otherwise it may be assigned to a separate module.

---

# 17. Relationship with Color and Screenshot Analysis

Reaction Analysis may independently use information produced by other analysis modules when such information is useful and documented as an input.

For example, a future implementation may use Color Analysis results as supporting evidence.

This does not create a runtime dependency. The producing module does not need to be running.

The relevant data is consumed from the database.

---

# 18. FINAL and AI Handling

Reaction Analysis does not decide where files belong.

If a later processing module uses Reaction Analysis results to move or regroup files:

* FINAL destinations must come from the configured Collection Definition or explicit user action;
* AI/transition workspaces may be extended with new working folders when the relevant module is authorized and its configured confidence threshold is met;
* no analysis result by itself creates a new FINAL directory.

---

# 19. Future Extensions

Possible future extensions include:

* better emote detection;
* platform-specific recognition;
* animated reaction analysis;
* meme-template assistance;
* OCR-assisted reaction detection;
* improved small-graphic classification.

Extensions should remain within the module's logical responsibility unless they introduce a genuinely independent function.

---

# 20. Acceptance Criteria

The module is considered compliant when it can:

* identify common reaction and utility image characteristics;
* write results using the current Analysis Result model;
* associate results with the correct SHA512 binary identity;
* reuse valid existing results where appropriate;
* support independent repeated executions;
* continue after recoverable per-file failures;
* avoid modifying files as part of analysis;
* provide useful confidence information where applicable;
* operate on very large collections;
* expose results to other modules through the shared database rather than direct module-to-module communication.

---

# End of DOC-104
