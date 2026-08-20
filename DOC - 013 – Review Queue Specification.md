# DOC-013 – Review Queue Specification

**Version:** 2.3

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

If a module's results are explicitly cleared through DOC-205 and that module is subsequently rerun, the module must still respect any protected user decision that applies to the resulting decision context.

---

# 10. AI / Transition Workspace Handling

The configured Transition/AI workspace may be used as the physical working area for Review Queue cases involving files that can safely leave their current processing location.

AI is allowed to develop a working directory structure that does not yet exist in FINAL.

When a module's configured confidence threshold is exceeded and its own specification permits automatic workspace organization, the module may create a new directory inside the AI/transition tree.

Example:

```text
AI
└── Ben 10
    └── image.jpg
```

The created AI directory is a working classification/proposal and does not become a FINAL collection merely because it exists.

The user may later move the resulting files or the complete AI directory into an existing FINAL destination after review.

The user may also decide that the AI classification is incorrect and move the file elsewhere.

---

# 11. FINAL Tree Destination Rules

FINAL is different from the AI/transition workspace.

AI and analysis modules must not create new final collection directories merely because a model or rule produces a new classification.

A final destination is valid for automatic placement only when the corresponding directory already exists and is represented by the Collection Definition.

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

but no corresponding FINAL destination exists in the Collection Definition, the system shall not create:

```text
FINAL/Anime/Ben 10
```

automatically.

The result may instead be stored as analysis information, organized inside AI, or presented for user review according to the relevant module specification.

FINAL structure is therefore user-defined. AI structure may be extended by qualifying automated workspace operations.

---

# 12. AI Directory Creation Rules

Automatic directory creation is permitted in the AI/transition workspace only when:

* the responsible module is explicitly allowed to create directories;
* the destination is inside the configured AI/transition root;
* the operation is consistent with the module's configured confidence threshold and classification rules;
* the creation does not modify FINAL.

A newly created AI directory does not need to exist in Collection Definition as a FINAL destination.

This permits workflows such as:

```text
AI detects a new universe
        ↓
confidence exceeds threshold
        ↓
AI/Ben 10/ is created
        ↓
files are organized there
        ↓
user reviews the result
        ↓
user may move the entire folder to an existing FINAL tree
```

The user remains the authority over the eventual FINAL structure.

---

# 13. Suggested Results Are Not Commands

A Review Queue suggestion is informational until the user resolves the case.

Suggestions may include:

```text
Suggested universe: Ben 10
Suggested character: Gwen Tennyson
Suggested destination: FINAL/Anime/Ben 10
Suggested filename: furina.jpg
```

A suggestion must never be treated as an automatic command merely because it has high confidence.

The exception is an explicitly specified and permitted **AI/transition workspace operation**. Such an operation may automatically create AI directories or organize files within AI without creating a FINAL directory or silently overriding a user decision.

---

# 14. Review of FINAL

FINAL contains user-accepted collection content but is not assumed to be permanently error-free.

If a module detects a probable classification or placement error inside FINAL, the module must not autonomously relocate the file solely on the basis of its analysis when user approval is required.

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

# 15. Review of Source, Transition and Other Files

For files in source/transition areas, the Review Queue may be represented by:

* a working location in the AI workspace;
* a report;
* database review metadata;
* another explicitly defined module workflow.

The implementation should use the least complex mechanism that safely provides the user with the required decision context.

---

# 16. Validation Before Applying a Decision

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

A user-selected destination that was already applied successfully is not subsequently considered stale merely because an automatic model proposes another destination. Manual decisions take precedence unless the user explicitly changes them.

---

# 17. Review Queue and Module Independence

Creating a Review Queue case does not create a runtime dependency on another module.

A module may create review cases and terminate.

Another module may later read the resulting database state and continue its own independent execution.

No review process or module needs to remain continuously active.

---

# 18. Review Queue and File Identity

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

# 19. Duplicate and Repeated Review Cases

A module should avoid creating unlimited duplicate Review Queue entries for the same unresolved condition when practical.

However, a new execution may legitimately create a new case when the underlying evidence or proposed action has materially changed.

Manual decisions are not to be treated as unresolved review cases simply because a later automatic analysis disagrees.

---

# 20. Review and Automatic Reprocessing

A deferred or unresolved review case may be reconsidered by a later module execution according to the relevant module's reprocessing policy.

A resolved manual decision must not be silently replaced by later automatic processing.

A rejected automatic suggestion must not automatically become an accepted result merely because the same module is run again.

Under the current architecture, changing a module, model, threshold set or analysis implementation does not itself trigger automatic reprocessing. When the user wants a complete recalculation of a module's stored results, the user explicitly uses DOC-205 to clear that module's results and then runs the module again.

Review Queue does not own or schedule reprocessing.

---

# 21. Logging

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

# 22. Export and Reporting

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

# 23. Lifetime and Cleanup

Review Queue cases should remain available until they are resolved, deferred, cancelled or otherwise invalidated according to their status.

Resolved and cancelled history may be retained for auditability and diagnostics.

Database Maintenance may define retention and cleanup rules.

The system must not silently delete an open or deferred review case merely because it is old.

---

# 24. Safety Principles

The Review Queue follows these principles:

* uncertain decisions should be sent to the user rather than guessed;
* suggestions are not commands;
* user decisions have priority over later automatic results for the affected classification or placement context;
* physical operations require validation before execution;
* AI may be automatically extended as a working area when the relevant module and threshold permit it;
* FINAL structure is user-defined and must not be extended automatically;
* Review Queue cases do not modify files by themselves;
* FINAL may be reviewed without being treated as infallible;
* migration is handled as a possible review outcome, not as a separate Migration Queue system;
* independent modules may continue operating without waiting for a review case to be resolved unless their own specification explicitly requires otherwise.

---

# 25. Relationship with Collection Definition

Review Queue does not define FINAL directory structure.

Collection Definition defines the existing configured FINAL destinations and the logical collection structure used by modules.

AI/transition directories created by an explicitly permitted module operation are working directories and do not require pre-existence in the FINAL Collection Definition.

Collection Definition and traversal behaviour are defined by DOC-301 and DOC-302.

---

# 26. Future Extensions

The current Review Queue can later support:

* graphical review interfaces;
* batch decisions;
* advanced filtering and search;
* module-specific review panels;
* richer review history;
* automatic revalidation of stale cases.

Such extensions must preserve user authority, file identity and the distinction between AI workspace expansion and FINAL structure.

---

# 27. Acceptance Criteria

The Review Queue is considered compliant when:

* uncertain or user-sensitive cases can be represented consistently;
* each persistent case has a unique identifier;
* the affected file can be identified using SHA512-based identity;
* user decisions support ACCEPT, REJECT, MODIFY and DEFER;
* suggestions are not executed automatically merely because they exist;
* explicitly permitted AI/transition workspace operations may create new AI directories when their configured threshold/rules are satisfied;
* FINAL directories are not created automatically by analysis modules;
* user-selected destinations become authoritative for the affected placement/classification context;
* manual corrections cannot be silently overwritten by later automatic processing;
* review cases can be represented in the AI/transition workspace where appropriate;
* stale decisions are detected before unsafe operations are applied;
* Review Queue does not require a separate Migration Queue;
* Review Queue activity is logged;
* review handling does not introduce runtime dependencies between otherwise independent modules.

---

# End of DOC-013
