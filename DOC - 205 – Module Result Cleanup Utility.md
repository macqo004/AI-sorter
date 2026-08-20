# DOC-205 – Module Result Cleanup Utility

**Project:** AI Image Collection Management System

**Document:** DOC-205

**Version:** 1.0

**Status:** Design Specification

**Related:** DOC-005, DOC-007, DOC-008, DOC-010, DOC-013, DOC-014

---

# 1. Purpose

Module Result Cleanup Utility is a small administrative utility used to remove stored analysis results belonging to a selected module or result set so that the module can subsequently analyse the collection again.

The utility implements the user-controlled cleanup policy defined by DOC-014.

It is not a reprocessing engine, scheduler, module orchestrator, or file-management component.

Its responsibility ends when the selected module results have been safely cleared from the database.

---

# 2. Core Principle

Changing a module, model, algorithm, threshold set, or implementation does not automatically clear existing results.

When the user wants a complete recalculation using the new implementation, the user explicitly runs this utility, selects the appropriate module result set, clears it, and then runs the module normally.

The utility must never initiate the subsequent analysis automatically unless a future specification explicitly adds such an option.

---

# 3. Scope

The utility operates on persisted module results in the project database.

It may clear:

```text
IRL results
Screenshot results
Universe results
Character results
Theme results
Set results
```

or another explicitly registered module result set.

It must not, by default, clear unrelated modules merely because they may consume information produced by the selected module.

---

# 4. User Workflow

The normal workflow is:

```text
Open Module Result Cleanup
        ↓
Select module/result set
        ↓
Display affected-result summary
        ↓
Display warning
        ↓
User confirms
        ↓
Clear selected results
        ↓
Report completion
        ↓
User runs the module separately
```

The cleanup operation is always explicitly user initiated.

---

# 5. Module Selection

The utility shall provide a list of registered modules/result sets that support cleanup.

The utility should identify the selected item using its stable module identifier rather than relying only on display names.

Example:

```text
Module: IRL Analysis
Module ID: irl_analysis
```

The display name may change without changing the logical module identity.

A module should not be selectable for cleanup until the system knows which database result set belongs to that module.

---

# 6. Affected Result Preview

Before confirmation, the utility should determine and present the scope of the cleanup.

The preview should include where practical:

```text
module
result type
number of affected files/results
number of historical/current records affected
```

Example:

```text
Module: IRL Analysis

Current results:
4,823,156

The cleanup will remove IRL analysis results only.
Physical files and file identity will not be affected.

[Cancel] [Clear Results]
```

For very large collections the preview must be implemented efficiently and must not require loading all affected rows into application memory.

---

# 7. Confirmation

Because cleanup can affect millions of records, it requires explicit user confirmation.

The confirmation should clearly state:

* which module is selected;
* approximately how many results will be affected;
* that physical files will not be deleted;
* that SHA512/file identity will not be deleted;
* that unrelated module results will remain untouched unless explicitly selected.

A cancelled confirmation performs no cleanup.

---

# 8. What Cleanup Removes

Cleanup removes the selected module's stored analysis result state according to the result model defined by DOC-005.

The intended result is equivalent to:

```text
selected module result
        ↓
NOT_PROCESSED
```

The exact physical database operation may be deletion, archival, status reset, or another implementation mechanism, provided that the observable logical state is correct and unrelated information is preserved.

The utility must follow the retention/history rules defined by the database schema. It must not invent a second history system.

---

# 9. What Cleanup Must Not Remove

Cleanup must not delete or modify solely because of the cleanup operation:

```text
File identity
SHA512
file_id
FileLocation
physical image files
unrelated module results
Collection Definition
configuration
Review Queue cases unrelated to the selected result set
protected manual decisions
```

A module result may be removed while the file itself remains fully known to the system.

---

# 10. SHA512 and File Identity

SHA512 is the identity of the binary content according to DOC-012 and DOC-005.

Module Result Cleanup does not recalculate or replace SHA512 merely because an analysis result is cleared.

Example:

```text
Before cleanup:

SHA512 = ABC...
IRL = FALSE
Universe = Genshin Impact

After IRL cleanup:

SHA512 = ABC...
IRL = NOT_PROCESSED
Universe = Genshin Impact
```

The same binary file remains the same file identity.

Where identical SHA512 values occur at multiple physical locations, those locations represent occurrences of the same binary content; cleanup applies to the stored result associated with that content/file identity according to the database model.

---

# 11. Manual Decisions

The utility must respect the distinction between an automatic module result and a user-originated decision.

Clearing an automatic result must not silently erase a protected manual decision recorded through Review Queue.

Example:

```text
Universe automatic result = Winx Club
User decision = Ben 10
```

Clearing the Universe analysis result does not authorize the system to forget the user's protected decision.

The module may need the automatic result to be recalculated later, while the manual decision remains authoritative according to DOC-013.

---

# 12. Review Queue Interaction

Module Result Cleanup does not process Review Queue cases.

It may encounter result rows referenced by Review Queue metadata. Such cases must be handled according to DOC-013 rather than silently destroying the user-decision record.

A cleanup operation must not convert an open Review Queue case into an instruction, nor should it automatically resolve a case merely because its underlying automatic result was removed.

If the selected result is necessary to render a review case, the Review Queue layer must be able to distinguish the missing automatic result from the user decision and historical context.

---

# 13. Module Independence

Cleaning one module does not require running or cleaning another module.

Example:

```text
IRL       = processed
Screenshot = processed
Universe  = processed
Character = processed
```

The user may clear only IRL:

```text
IRL       = NOT_PROCESSED
Screenshot = processed
Universe  = processed
Character = processed
```

The utility must not automatically start Universe or Character analysis afterward.

Whether a later module can benefit from newly calculated results is determined by that module when it is independently executed.

---

# 14. Execution and Transactions

A cleanup operation is a database operation and must follow the database transaction/error-handling rules defined by DOC-005 and DOC-009.

The utility should use a safe method appropriate for the selected result set.

For a large cleanup, the implementation may process records in batches where necessary, provided that the user receives an accurate completion status.

The operation must not report complete success if only part of the requested cleanup was performed.

If a failure occurs, the utility shall report whether the cleanup is:

```text
COMPLETED
PARTIALLY_COMPLETED
FAILED
CANCELLED
```

Exact rollback behaviour depends on the database operation and must be documented in implementation details.

---

# 15. Large-Scale Collections

The project targets collections of approximately 5,000,000 files.

The utility must therefore avoid:

* loading all result rows into memory;
* creating one application object per affected record unnecessarily;
* requiring the filesystem to be scanned merely to determine the database cleanup scope;
* coupling cleanup to image processing.

The cleanup scope should be derived from database state whenever possible.

---

# 16. Logging

Every cleanup execution shall be logged according to DOC-011 and DOC-007 where applicable.

The log should include:

```text
execution_id
module_id
started_at
finished_at
requested result set
results found
results cleared
status
errors
```

The log must not imply that files were deleted when only database results were cleared.

---

# 17. No Automatic Reprocessing

The utility must not contain hidden logic such as:

```text
clear IRL
   ↓
automatically run IRL
```

or:

```text
clear Universe
   ↓
automatically run Character
```

The explicit separation is intentional.

Cleanup prepares the database for a future module execution; it does not perform that execution.

---

# 18. No Model-Version Management

The utility does not compare model versions or maintain multiple generations of module results.

The user decides when a module's existing results should be cleared.

A newer module implementation may provide a user-facing warning or documentation indicating that cleanup is recommended, but the utility itself does not maintain per-result model-generation history.

---

# 19. Relationship with Scanner

Scanner registration is independent from result cleanup.

The utility does not need to rescan the filesystem to clear module results.

After cleanup, already registered files remain registered and may be processed by the selected module during its next execution.

New files still require Scanner registration before normal module processing, according to DOC-101.

---

# 20. Relationship with Database Maintenance

Module Result Cleanup is a targeted administrative operation.

It is not a database rebuild, integrity check, vacuum operation, or backup procedure.

Database Maintenance remains responsible for maintenance tasks defined by DOC-202.

The cleanup utility may use database maintenance APIs or services where appropriate, but the user-facing purpose remains limited to clearing selected module results.

---

# 21. Configuration

The utility should use Configuration Manager for ordinary application settings such as:

```text
confirmation behaviour
logging location
UI preferences
batch-size limits where configurable
```

It must not duplicate module-result definitions already owned by the module registry/database architecture.

---

# 22. Safety Principles

The utility follows these rules:

1. Cleanup is explicitly requested by the user.
2. Cleanup is scoped to a selected module/result set.
3. Physical files are never deleted by cleanup.
4. SHA512/file identity is never removed merely because a result is cleared.
5. Unrelated module results remain untouched.
6. Protected manual decisions remain protected.
7. Review Queue cases are not silently resolved or destroyed.
8. Cleanup does not automatically run any analysis module.
9. Cleanup does not create or modify FINAL or AI directories.
10. Large cleanup operations must provide accurate completion/error reporting.

---

# 23. Acceptance Criteria

Module Result Cleanup Utility is compliant when it can:

* list supported module result sets;
* let the user select one result set explicitly;
* preview the affected scope;
* require confirmation;
* clear the selected module results without deleting physical files;
* preserve SHA512/file identity;
* preserve unrelated module results;
* preserve protected manual decisions;
* handle large result sets without requiring the full dataset in memory;
* report COMPLETED, PARTIALLY_COMPLETED, FAILED or CANCELLED accurately;
* log the cleanup operation;
* leave the subsequent module execution as a separate user action.

---

# End of DOC-205
