# DOC-104

# Reaction Image Analysis Module

**Project:** AI Image Collection Management System

**Document:** DOC-104

**Module:** Reaction Image Analysis

**Version:** 2.1

**Status:** Design Specification

**Depends on:** DOC-005, DOC-007, DOC-008, DOC-010, DOC-011, DOC-012, DOC-014, DOC-205

---

# 1. Purpose

The Reaction Image Analysis module identifies images that are primarily intended for reactions, communication, emotes, emojis or simple utility use rather than ordinary artwork classification.

The module produces analysis results for later modules. It does not itself decide whether an image should be removed, moved or excluded from the collection.

# 2. Responsibilities

The module shall analyse reaction/utility characteristics, provide confidence where meaningful, write its own results to the shared database and preserve the distinction between automatic analysis and later user decisions.

The module shall not identify anime characters or universes, perform IRL or screenshot classification as its primary responsibility, move/rename/delete files, modify other modules' results, or create/modify FINAL structure.

# 3. Scope

Typical examples include reaction faces, emoji/emote graphics, sticker-like graphics, simple expressive graphics, small utility graphics and internet reaction images.

`IS_REACTION_IMAGE = TRUE` is an analysis result, not an instruction to remove or move the file.

# 4. Input

Required information includes SHA512, current filesystem state, image format where available and image dimensions where available. The module may access the filesystem to decode the image.

A valid file identity in the database is required. Scanner does not need to be running and the module invokes no other module.

# 5. Output

Initial features may include:

```text
IS_REACTION_IMAGE
IS_EMOJI
IS_EMOTE
HAS_MINIMAL_SCENE
HAS_SINGLE_SUBJECT
HAS_LARGE_TRANSPARENT_AREA
IS_UTILITY_IMAGE
```

Results may include file identity, module, feature, value, confidence and execution/diagnostic metadata. Diagnostic version information is informational and is not used to automatically invalidate results.

# 6. Definitions

## Reaction Image
An image primarily intended to express emotion, opinion or reaction in a communication context.

## Emoji
A small symbolic graphic representing an emotion, object or concept.

## Emote
A platform or community-specific reaction graphic used as a communication element.

## Utility Image
A graphic primarily created for communication or practical use rather than ordinary artwork presentation.

## Minimal Scene
An image containing little environmental context, often consisting primarily of one object, face, symbol or isolated subject.

# 7. Confidence

Where the module produces classification-like results, confidence represents the strength of its evidence. A high-confidence result does not authorize filesystem modification.

# 8. Processing Rules

The module may process the same file in multiple independent executions.

Existing valid results may be reused for the same binary identity when no explicit recalculation is requested.

A change to module implementation, model, analysis rules or configuration does **not** automatically clear results and does not automatically trigger reprocessing.

When the user wants complete recalculation using changed logic, the user shall use **DOC-205 – Module Result Cleanup Utility** to clear Reaction Analysis results and then run the module again.

A change of path or filename without a SHA512 change does not by itself invalidate the result. A changed SHA512 creates a new binary identity whose result must be calculated independently.

# 9. Database Access

The module reads the shared database and corresponding files and writes only Reaction Analysis results and execution-related state. It must not overwrite Scanner state, unrelated results or user decisions.

# 10. Performance Requirements

The module shall remain suitable for collections containing millions of images. It should use inexpensive evidence before expensive analysis where practical, avoid unnecessary work and avoid requiring the entire collection in memory.

# 11. Threading and Resource Usage

Parallel execution shall be supported where practical. Worker counts and applicable limits are configurable.

# 12. Error Handling

Per-file failures shall be logged and should not stop unrelated work where safe. Incomplete results shall not be stored as valid current results.

# 13. Logging

Each execution shall create a Module Execution record and summary log according to DOC-007 and DOC-011.

# 14. Interaction with Other Modules

The module does not invoke other modules. Other modules consume its results from the database and do not require it to be running.

# 15. Design Philosophy

The module is an information provider. Weak or ambiguous evidence should not be converted into an unjustifiably confident classification. Material downstream decisions use Review Queue rather than treating analysis as an automatic command.

# 16. Scope Boundaries

The initial version does not require full meme-template recognition, OCR-based caption interpretation, platform provenance detection or complete animated-media understanding.

# 17. Relationship with Color and Screenshot Analysis

The module may consume documented results from other modules through the database. Such use does not create a runtime dependency.

# 18. FINAL and AI Handling

Reaction Analysis does not decide physical placement. FINAL destinations come from Collection Definition or explicit user action. AI workspaces may be extended only by the responsible authorized workflow. No analysis result alone creates a FINAL directory.

# 19. Future Extensions

Possible extensions include better emote detection, platform-specific recognition, animated reaction analysis, meme-template assistance and OCR-assisted reaction detection.

# 20. Acceptance Criteria

The module is compliant when it can identify reaction/utility characteristics, store them under the correct SHA512 identity, reuse valid results, avoid automatic invalidation after model/rule changes, support full recalculation through DOC-205 followed by a new module execution, operate independently, continue after recoverable failures and expose results through the shared database.

---

# End of DOC-104
