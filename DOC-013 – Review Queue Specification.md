# DOC-013 – Review Queue Specification

**Project:** AI Image Collection Management System

**Document:** DOC-013

**Version:** 2.1

**Status:** Draft

---

# 1. Purpose

This document defines the common Review Queue mechanism used throughout the project.

The Review Queue is the system-wide mechanism for situations in which a module cannot safely make a decision automatically, or where a proposed correction requires explicit user judgement.

The Review Queue exists to protect the collection from incorrect or destructive automatic decisions.

It does not replace the user's decision. It provides the information and workflow needed for the user to make that decision.

---

# 2. Core Principle

The project follows the principle:

> **If the system is not sufficiently certain, it shall ask the user rather than guess.**

A module should create a Review Queue case when it cannot safely determine the correct result or when the applicable workflow requires explicit user approval.

The existence of a Review Queue case must not stop an otherwise independent module execution unless the module specification or user configuration explicitly requires execution to stop.

---

# 3. Review Queue as a Logical Mechanism

Review Queue is a logical project mechanism, not necessarily a single physical folder or interactive GUI queue.

A Review Queue case may be represented through:

* a database record;
* a text/report file containing paths or proposed actions;
* placement of a file into the configured transition/AI workspace;
* a future graphical review interface;
* another documented local representation appropriate to the case.

The database remains the authoritative source of review metadata whenever a case is tracked persistently.

There is no separate Migration Queue in the current architecture.

A proposed migration is simply one possible outcome of a Review Queue case.

---

# 4. When a Review Case Is Created

A module may create a Review Queue case when, for example:

* confidence is below the module's configured decision threshold;
* multiple valid interpretations remain;
* a proposed filename change is ambiguous;
* a classification appears inconsistent with the current location;
* a file in FINAL appears to be incorrectly classified;
* a destructive or potentially irreversible operation requires user approval;
* required information is missing or contradictory;
* the module detects a stale or otherwise unsafe proposed operation.

A module should not create a Review Queue case merely because it performed ordinary successful processing.

---

# 5. Review Item Identity

Each persistent Review Queue case shall have a unique review identifier.

Where a file is involved, the case should reference the current file identity using the project's File Identity Model.

Recommended information includes:

```text
review_id
file_id (if used)
SHA512
module_id
execution_id (if applicable)
classification context (if applicable)
created_at
current_path_at_creation
operation
reason
suggested_result
confidence
status
```

SHA512 and current file state are important for later validation because a user may resolve a case long after it was created.

---

# 6. Review Case Status

The logical review lifecycle shall support at least:

```text
OPEN
RESOLVED
DEFERRED
STALE
CANCELLED
```

`OPEN` means that user action is still required.

`RESOLVED` means that the user has made a decision and the corresponding workflow has completed successfully.

`DEFERRED` means that the user intentionally left the case for later processing.

`STALE` means that the proposed case can no longer safely be applied to the file state that existed when it was created and must be reconsidered or recreated.

`CANCELLED` means that the case is no longer applicable and should not be acted upon.

A module must not silently treat a stale case as a current instruction.

---

# 7. User Decisions

The review workflow shall support the following logical user decisions:

```text
ACCEPT
REJECT
MODIFY
DEFER
```

These decisions describe the user's choice; they are not themselves filesystem operations.

## ACCEPT

The user accepts the proposed result or destination.

## REJECT

The user rejects the proposed result and it must not be applied automatically.

## MODIFY

The user changes the proposed result, destination or other applicable parameter before applying it.

## DEFER

The user intentionally postpones the decision.

The physical user interface may represent these decisions differently, but their logical meaning shall remain distinguishable.

---

# 8. User Decision Has Priority

A user decision is authoritative over an automatic suggestion for the affected decision context.

When the user explicitly selects or modifies a destination, classification or other proposed result, the system shall treat the chosen result as the user's accepted correction.

Example:

```text
Automatic suggestion:
FINAL/Winx Club/image.jpg

User decision:
FINAL/Pokemon/image.jpg
```

The selected destination is authoritative. The system must not subsequently treat the location chosen by the user as an unresolved automatic classification merely because a later module disagrees with it.

A manual correction shall be recorded in the database as a user-originated decision and shall have higher priority than later automatic results for the same classification/placement context.

The user may explicitly change or remove the manual decision at a later time.

---

# 9. Manual Correction and Reprocessing

A manually corrected classification or placement must not be silently overwritten by later automatic processing.

The database should preserve at least:

* the previous automatic result;
* the user's final decision;
* the current accepted classification or placement;
* the relevant event/history information.

A later module execution may continue to produce new automatic observations, but it must not automatically replace a protected manual decision.

Manual protection is applied to the relevant classification or placement context rather than automatically disabling every unrelated analysis of the file.

---

# 10. AI / Transition Workspace Handling

The configured Transition/AI workspace may be used as the physical working area for Review Queue cases involving files that can safely leave their current processing location.

For a detected placement error in FINAL, the system may use an existing corresponding AI workspace, for example:

```text
FINAL/Anime/Winx Club/image.jpg
        ↓
AI/Ben 10/image.jpg
```

The AI location is a working proposal, not a final classification.

The user may then move the file to any appropriate existing FINAL destination or to an appropriate source/transition location according to the collection configuration.

If the user chooses a destination different from the automatic suggestion, that user-selected destination becomes the authoritative manual correction for the relevant placement/classification context.

---

# 11. Final Tree Destination Rules

AI and analysis modules must not create new final collection directories merely because a model or rule produces a new classification.

A final destination is valid for automatic placement only when the corresponding directory already exists and is defined in the Collection Definition.

Example:

```text
Collection Definition:
FINAL/Anime/Genshin Impact/Furina
```

is a valid destination.

If a model reports:

```text
New Universe: Ben 10
```

but no corresponding destination exists in the Collection Definition, the system shall not automatically create:

```text
FINAL/Anime/Ben 10
```

The result may instead remain in the database, be placed into the configured AI/transition workspace, or enter Review Queue according to the relevant module specification.

This rule also applies to newly proposed subdirectories inside existing final trees.

The AI system is not a directory-creation mechanism for FINAL.

---

# 12. Suggested Results Are Not Commands

A Review Queue suggestion is informational until the user resolves the case.

Examples include:

```text
Suggested universe: Ben 10
Suggested character: Gwen Tennyson
Suggested destination: FINAL/Anime/Ben 10
Suggested filename: furina.jpg
```

A suggestion must never be treated as an automatic command merely because it has high confidence.

---

# 13. Review of FINAL

FINAL contains user-accepted collection content but is not assumed to be permanently error-free.

If a module detects a probable classification error inside FINAL, the module must not autonomously relocate the file solely on the basis of its analysis when user approval is required.

The review representation may depend on the case.

For example, a module may produce a text report containing:

```text
Current path:
D:\Collection\Anime\Winx Club\image.jpg

Suggested destination:
D:\Collection\Anime\Ben 10\image.jpg

Reason:
Universe mismatch

Confidence:
99.7%
```

Alternatively, where the collection workflow allows the file to be safely moved out of FINAL for review, the file may be placed in the configured AI/transition workspace.

---

# 14. Validation Before Applying a Decision

A decision affecting a file should be validated against the current filesystem and database state before the physical operation is performed.

Where applicable, verify:

```text
review case is still valid
file still exists
SHA512 still matches
current path still matches expected state
file record still exists
requested destination is still permitted
```

If the state has changed materially, the case should become `STALE` rather than blindly applying the old instruction.

---

# 15. Review Queue and Module Independence

Creating a Review Queue case does not create a runtime dependency on another module.

A module may create review cases and terminate. Another module may later read the resulting database state and continue its own independent execution.

For example:

```text
IRL Analysis
    ↓
creates Review cases
    ↓
execution ends

Screenshot Analysis
    ↓
runs later
    ↓
reads current database state
```

No review process or module needs to remain continuously active.

---

# 16. Review Queue and File Identity

Review cases involving a file should reference its SHA512-based identity and, where used, the internal `file_id`.

A review case created for:

```text
SHA512 = AAAA
```

must not be silently applied to:

```text
SHA512 = BBBB
```

when the file content has changed.

---

# 17. Duplicate and Repeated Review Cases

A module should avoid creating unlimited duplicate Review Queue entries for the same unresolved condition when practical.

The implementation may recognize an equivalent open case using information such as:

```text
file identity
module
classification context
operation
current state
```

A new case is legitimate when the underlying evidence or proposed action has materially changed.

---

# 18. Review and Automatic Reprocessing

A deferred or unresolved review case may be reconsidered by a later module execution according to the relevant module's reprocessing policy.

A resolved manual decision must not be silently replaced by later automatic processing.

A rejected automatic suggestion must not automatically become an accepted result merely because the same module is run again.

---

# 19. Logging

Creation, resolution, deferral, cancellation and staleness of Review Queue cases shall be logged according to DOC-011.

Logs should identify, where applicable:

* module;
* execution;
* review identifier;
* file SHA512;
* path;
* action or decision;
* reason.

---

# 20. Export and Reporting

Review information may be exported for manual inspection.

Suitable formats include:

```text
TXT
CSV
JSON
```

For FINAL validation, a plain-text path report is explicitly permitted because it is simple, offline and easy for the user to inspect.

Exports are representations of Review Queue information and are not themselves the authoritative database record when a persistent Review Item exists.

---

# 21. Lifetime and Cleanup

Review Queue cases should remain available until they are resolved, deferred, cancelled or otherwise invalidated according to their status.

Resolved and cancelled history may be retained for diagnostics.

Database Maintenance may define retention and cleanup rules.

The system must not silently delete an open or deferred review case merely because it is old.

---

# 22. Safety Principles

The Review Queue follows these principles:

* uncertain decisions should be sent to the user rather than guessed;
* suggestions are not commands;
* user decisions have priority over later automatic results for the affected classification context;
* physical operations require validation before execution;
* Review Queue cases do not modify files by themselves;
* FINAL may be reviewed without being treated as infallible;
* migration is handled as a possible review outcome, not as a separate Migration Queue system;
* independent modules may continue operating without waiting for a review case to be resolved;
* final destinations are never invented by AI/analysis modules and must come from Collection Definition or explicit user action.

---

# 23. Relationship with Other Documents

```text
DOC-005  Database Schema
DOC-008  Configuration Manager
DOC-010  Module Interface Specification
DOC-011  Logging Standard
DOC-012  File Identity Model
DOC-301  Collection Definition Wizard
DOC-302  Collection Definition Format
```

DOC-013 defines the common review mechanism. Module-specific criteria for creating a review item remain in the relevant module specification.

---

# 24. Acceptance Criteria

The Review Queue is compliant when:

* uncertain or user-sensitive cases can be represented consistently;
* each persistent case has a unique identifier;
* the affected file can be identified using SHA512-based identity;
* user decisions support ACCEPT, REJECT, MODIFY and DEFER;
* suggestions are not executed automatically merely because they exist;
* manual corrections cannot be silently overwritten by later automatic processing for the same classification/placement context;
* review cases can be represented in the AI/transition workspace where appropriate;
* FINAL review can be represented without automatically modifying FINAL;
* stale decisions are detected before unsafe operations are applied;
* Review Queue does not require a separate Migration Queue;
* Review Queue activity is logged;
* review handling does not introduce runtime dependencies between otherwise independent modules;
* AI/analysis modules do not automatically create new final collection directories.

---

# End of DOC-013
