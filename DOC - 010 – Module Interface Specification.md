# DOC - 010 – Module Interface Specification

**Project:** AI Image Collection Management System  
**Document:** DOC - 010  
**Version:** 3.0  
**Status:** Design Specification

**Depends on:** DOC - 003, DOC - 005, DOC - 007, DOC - 008, DOC - 011, DOC - 012, DOC - 013, DOC - 014

---

# 1. Purpose

This document defines the common interface contract for project modules.

It describes metadata, initialization, input/output, execution state, configuration access, logging, error handling and filesystem permissions.

It does not define an individual module's internal algorithm.

---

# 2. Module Independence

Modules are independently executable components.

Modules do not communicate directly with one another. Persistent information exchanged between modules is exchanged through the project database.

A module may use normal OS facilities, libraries, filesystem access and GPU resources for its own operation; these are not application-level module communication.

A module may run repeatedly without requiring other modules to be rerun.

---

# 3. Scanner Data Prerequisite

Scanner is the base data-ingestion module.

A newly added physical file normally requires a valid File/FileLocation record before ordinary database-driven modules process it.

This is a data prerequisite, not a runtime dependency on Scanner.

---

# 4. Required Module Metadata

Every module should expose:

```text
module_id
name
version
description
category
```

The representation is implementation-specific.

---

# 5. Initialization

A module shall perform the checks required for safe execution, which may include:

* loading/validating configuration;
* validating selected Collection Definition scope;
* checking required roots;
* opening/verifying database access;
* validating schema compatibility;
* preparing required model/resources.

A failed mandatory precondition prevents unsafe execution.

---

# 6. Input Contract

Each module specification shall define:

* accepted processing scope;
* required database state;
* configuration parameters;
* files/records it reads;
* module resources.

If a module depends on another module's data, the dependency is on persisted database state, not on another process.

---

# 7. Output Contract

Each module specification shall define outputs such as:

* module-owned database results;
* permitted filesystem changes;
* logs;
* reports;
* exported/support files;
* Review Queue cases where applicable.

No undocumented operational side effects are permitted.

---

# 8. Database Ownership

A module owns the persistent information it is responsible for producing.

It may read shared information owned by another component when that information is a documented input.

It must not silently overwrite:

* another module's results;
* File identity;
* Scanner-owned filesystem state without appropriate responsibility;
* protected user decisions.

DOC - 005 defines the logical database model.

---

# 9. File Identity

Modules shall use DOC - 012.

```text
SHA512
    = logical binary-content identity

FileLocation
    = physical occurrence
```

`file_id`, where used, is an internal technical database identifier.

Filename and path are never primary file identity.

---

# 10. Configuration

Module configuration is obtained through DOC - 008.

Modules must not hard-code physical paths or architectural meaning into directory names such as `TODO`, `AI`, `FINAL`, `Anime` or `Themes`.

Collection structure and access policies are obtained from the validated Collection Definition defined by DOC - 301 / DOC - 302 / DOC - 303.

---

# 11. Collection Scope

A module operating on a collection shall define which logical root roles it accepts, such as:

```text
TODO
AI
PRIMARY
THEME_FALLBACK
IMPORT_SOURCE
```

The physical paths come from Collection Definition.

---

# 12. Access Policy

Filesystem operations are subject to the Directory Access Policy defined by DOC - 302 and the module's own permissions.

The module interface should identify which filesystem operations it may perform, such as:

```text
READ
RENAME
MOVE
CREATE
DELETE
```

A module cannot infer permission from the directory name alone.

---

# 13. Execution State

The interface shall support a user-visible execution state such as:

```text
STARTING
RUNNING
COMPLETED
COMPLETED_WITH_WARNINGS
CANCELLED
FAILED
```

The UI must make the current state understandable without requiring technical logs.

---

# 14. Progress

A module should report meaningful progress using counts, percentage, current operation or an activity indicator.

A reliable percentage is not mandatory when total work cannot be measured accurately.

---

# 15. Cancellation

Long-running modules should support safe user cancellation where practical.

Cancellation shall preserve completed valid work and record the execution as cancelled rather than completed.

---

# 16. Logging

All modules follow DOC - 011.

Logs should identify:

* module/version;
* execution;
* significant operations;
* warnings/errors;
* completion/cancellation/failure;
* user intervention requirements.

---

# 17. Error Handling

Modules distinguish recoverable per-file errors from execution-blocking errors.

A failure in one module must not invalidate unrelated completed work.

Cases needing a user decision use Review Queue where applicable.

---

# 18. Resources and Parallelism

Modules may use available CPU, GPU and RAM resources efficiently within configured/system limits.

Parallel execution is permitted where it does not violate database or filesystem consistency.

Worker counts may be configurable.

---

# 19. Repeated Execution and Result Recalculation

Modules may be executed any number of times.

Existing valid results should be reused when appropriate.

The current project does not automatically invalidate all results when a model, algorithm or threshold changes.

When a user wants a complete recalculation using a changed module implementation, the user may:

```text
DOC - 205
Module Result Cleanup
        ↓
clear selected module result set
        ↓
run the module separately
```

A module may also define more specific incremental logic for its own operation, but it must not create a conflicting automatic global invalidation model.

---

# 20. Per-File Results

A module should persist a current result for every successfully processed file within its configured scope where the module is defined to produce a result.

The absence of a result does not automatically mean failure; it may indicate that no current result exists or that the module's own state model does not apply.

Where a module needs persistent distinctions such as `FAILED` or `SKIPPED`, it defines those states in its own specification.

---

# 21. Input/Output Documentation

Every module document shall state:

* database inputs;
* database outputs;
* filesystem reads;
* permitted filesystem writes;
* generated reports/files;
* user decisions required.

---

# 22. Dependency Declaration

Module specifications document data dependencies such as:

```text
Universe Analysis
    input: File + supporting analysis data
    output: Universe candidates

Character Analysis
    input: File + optional Universe results
    output: Character candidates
```

These dependencies do not create runtime module-to-module communication or mandatory execution order.

---

# 23. Reproducibility and Execution Version

Module version shall be available at execution level.

A module may additionally record model/rule identifiers at execution level when useful.

This information is for history, diagnostics and reproducibility. It is not a requirement to store model generations with every result row.

---

# 24. Extensibility

A new module should normally require only its implementation, interface metadata, configuration definition, inputs/outputs and documentation.

Existing modules need not change merely because an unrelated module is added.

Shared cross-module requirements belong in shared standards rather than being copied into every module.

---

# 25. Compliance

A module complies with DOC - 010 when applicable requirements provide:

* identifiable metadata;
* safe initialization;
* documented inputs/outputs;
* common configuration access;
* File Identity compliance;
* visible execution status;
* appropriate progress/cancellation;
* logging;
* error isolation;
* database ownership discipline;
* collection/access-policy compliance;
* independent execution;
* current-result persistence for successful in-scope processing.

---

# End of DOC - 010
