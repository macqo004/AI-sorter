# DOC-013

# Review Queue Specification

**Project:** AI Image Collection Management System

**Document:** DOC-013

**Version:** 2.0

**Status:** Draft

**Depends on:**

DOC-003
DOC-005
DOC-007
DOC-010
DOC-011
DOC-012

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

Review Queue is a **logical project mechanism**, not necessarily a single physical folder or interactive GUI queue.

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

Example:

```text
AI/Ben 10/image.jpg
        ↓
ACCEPT
        ↓
FINAL/<approved destination>/image.jpg
```

The destination may be the suggested destination or another destination if the review workflow defines an explicit distinction between ACCEPT and MODIFY.

## REJECT

The user rejects the proposed result.

The file must not be automatically placed according to the rejected suggestion.

The module or workflow may leave the file in its current workspace or return it to an appropriate source/working area according to the relevant module specification.

A rejection is a user decision and should be preserved where future automatic processing could otherwise repeat the same action indefinitely.

## MODIFY

The user accepts the need for intervention but changes the suggested result, destination or other relevant parameter.

Example:

```text
AI/Ben 10/image.jpg
        ↓
MODIFY
        ↓
FINAL/Pokemon/image.jpg
```

The resulting user decision must be recorded so that later automatic processing does not silently undo it.

## DEFER

The user intentionally postpones the decision.

The file remains in its current review/workspace state and the case remains eligible for later user handling according to its lifecycle rules.

---

# 8. Manual Correction Has Priority

A user correction has higher priority than a later automatic result for the same classification context.

Example:

```text
Automatic:
Universe = Ben 10

User:
Universe = Pokemon
```

The later automatic execution must not silently change the active user decision back to `Ben 10`.

The database must retain the distinction between:

```text
AUTOMATIC
MANUAL
```

The protection applies to the relevant classification context, not necessarily to every possible analysis performed on the file.

For example, a user may manually correct the universe while allowing unrelated analysis such as colour or screenshot detection to continue.

Detailed database representation is defined by DOC-005.

---

# 9. AI / Transition Workspace Handling

The configured Transition/AI workspace may be used as the physical working area for Review Queue cases involving files that can safely leave their current processing location.

For a classification review, the system may create a directory representing the proposed classification.

Example:

```text
AI
└── Ben 10
    └── image.jpg
```

This directory indicates the system's current working proposal. It is not a final classification and does not imply that the user must accept `Ben 10`.

The user may subsequently place the file into any appropriate FINAL tree or return it to an appropriate TODO/source location according to the collection configuration.

The fact that a file was placed in `AI/Ben 10` does not prevent the user from deciding that the correct final destination is, for example, `FINAL/Pokemon`.

---

# 10. Final Tree Review Handling

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

The choice of representation must be defined by the relevant module and collection configuration.

---

# 11. Suggested Results Are Not Commands

A Review Queue suggestion is informational until the user resolves the case.

Examples include:

```text
Suggested universe: Ben 10
Suggested character: Gwen Tennyson
Suggested destination: FINAL/Anime/Ben 10
Suggested filename: furina.jpg
```

A suggestion must never be treated as an automatic command merely because it has high confidence.

The module may act automatically only where its own specification explicitly permits such an operation without user review.

---

# 12. Validation Before Applying a Decision

A decision affecting a file should be validated against the current filesystem and database state before the physical operation is performed.

At minimum, where applicable, the system should verify:

```text
review case is still valid
file still exists
SHA512 still matches
current path still matches expected state
file record still exists
requested destination is still permitted
```

If the state has changed materially, the case should become `STALE` rather than blindly applying the old instruction.

This prevents a delayed user decision from being applied to a different binary file or a different filesystem object.

---

# 13. Review Queue and Module Independence

Creating a Review Queue case does not create a runtime dependency on another module.

A module may create review cases and terminate.

Another module may later read the resulting database state and continue its own independent execution.

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

# 14. Review Queue and File Identity

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

The previous automatic analysis results remain associated with their original binary identity according to DOC-012.

---

# 15. Duplicate and Repeated Review Cases

A module should avoid creating unlimited duplicate Review Queue entries for the same unresolved condition when practical.

The implementation may recognize an equivalent open case using information such as:

```text
file identity
module
classification context
operation
current state
```

However, a new execution may legitimately create a new case when the underlying evidence or proposed action has materially changed.

The Review Queue must not become a permanent suppression mechanism that prevents useful re-evaluation.

---

# 16. Review and Automatic Reprocessing

A deferred or unresolved review case may be reconsidered by a later module execution according to the relevant module's reprocessing policy.

A resolved manual decision must not be silently replaced by later automatic processing.

A rejected automatic suggestion must not automatically become an accepted result merely because the same module is run again.

The exact rules for reopening or re-evaluating cases belong to the relevant module and future reprocessing architecture.

---

# 17. Logging

Creation, resolution, deferral, cancellation and staleness of Review Queue cases shall be logged according to DOC-011.

Logs should identify, where applicable:

* module;
* execution;
* review identifier;
* file SHA512;
* path;
* action or decision;
* reason.

Logs should provide a useful operational summary without duplicating the entire Review Queue record.

---

# 18. Export and Reporting

Review information may be exported for manual inspection.

Suitable formats include:

```text
TXT
CSV
JSON
```

The exact export format is implementation- or module-dependent.

For FINAL validation, a plain-text path report is explicitly permitted because it is simple, offline and easy for the user to inspect.

Exports are representations of Review Queue information and are not themselves the authoritative database record when a persistent Review Item exists.

---

# 19. Lifetime and Cleanup

Review Queue cases should remain available until they are resolved, deferred, cancelled or otherwise invalidated according to their status.

Resolved and cancelled history may be retained for auditability and future diagnostics.

The database-maintenance specification may define retention and cleanup rules.

The system must not silently delete an open or deferred review case merely because it is old.

---

# 20. Safety Principles

The Review Queue follows these principles:

* uncertain decisions should be sent to the user rather than guessed;
* suggestions are not commands;
* user decisions have priority over later automatic results for the affected classification context;
* physical operations require validation before execution;
* Review Queue cases do not modify files by themselves;
* FINAL may be reviewed without being treated as infallible;
* migration is handled as a possible review outcome, not as a separate Migration Queue system;
* independent modules may continue operating without waiting for a review case to be resolved unless their own specification explicitly requires otherwise.

---

# 21. Future Extensions

The current Review Queue can later support:

* graphical review interfaces;
* batch decisions;
* advanced filtering and search;
* module-specific review panels;
* richer review history;
* automatic revalidation of stale cases;
* integration with a future reprocessing manager.

These extensions must preserve the core principles of user control, offline operation and safe handling of uncertain decisions.

---

# 22. Acceptance Criteria

The Review Queue is considered compliant when:

* uncertain or user-sensitive cases can be represented consistently;
* each persistent case has a unique identifier;
* the affected file can be identified using SHA512-based identity;
* user decisions support ACCEPT, REJECT, MODIFY and DEFER;
* suggestions are not executed automatically merely because they exist;
* manual corrections cannot be silently overwritten by later automatic processing for the same classification context;
* review cases can be represented in the AI/transition workspace where appropriate;
* FINAL review can be represented without automatically modifying FINAL;
* stale decisions are detected before unsafe operations are applied;
* Review Queue does not require a separate Migration Queue;
* Review Queue activity is logged;
* review handling does not introduce runtime dependencies between otherwise independent modules.

---

# End of DOC-013
