# DOC - 007 – Module Execution and Architecture

**Project:** AI Image Collection Management System  
**Document:** DOC - 007  
**Version:** 3.0  
**Status:** Design Specification

**Depends on:** DOC - 003, DOC - 005, DOC - 008, DOC - 010, DOC - 011, DOC - 012, DOC - 013, DOC - 014

---

# 1. Purpose

This document defines the common execution model for project modules.

It describes independent execution, user control, execution state, failure isolation and persistent execution history.

It does not define individual module algorithms or the collection-definition format.

---

# 2. Module Definition

A module is an independent executable component with a defined responsibility.

A module may consume data produced by other modules, but it does not become responsible for their functions merely because it reads their outputs.

---

# 3. Module Independence and Communication

Modules do not communicate directly with one another at the application level.

Persistent information shared between modules is exchanged through the project database:

```text
Module A
    ↓
Database
    ↓
Module B
```

This does not prevent a module from using normal OS facilities, libraries, filesystem access, GPU resources or other technical resources required for its own operation.

A module normally terminates after its execution; permanently resident module processes are not required.

---

# 4. Scanner as Base Data Ingestion

Scanner is a special infrastructure module because it establishes database identity for newly discovered physical files.

The prerequisite is data availability, not process ordering:

```text
new physical file
        ↓
Scanner
        ↓
valid File / FileLocation state
        ↓
other modules may process it
```

Scanner does not need to remain running and does not need to execute immediately before another module.

A module requiring a File record must not invent a partial identity when one is absent.

---

# 5. User-Controlled Execution

Under the current architecture, the user selects:

* module;
* execution time;
* configured scope;
* execution frequency.

There is no mandatory global scheduler or pipeline.

---

# 6. Execution Order and Data Dependencies

There is no globally mandatory execution order among ordinary modules.

A module may require data produced by another module, but the dependency is on database state:

```text
required result exists in DB
    = dependency satisfied
```

The producing module does not need to be running.

The following is valid:

```text
IRL Analysis × 5
Screenshot Analysis × 2
IRL Analysis × 1
```

The second and sixth executions are independent invocations.

---

# 7. Shared Database

The database is the primary persistent and inter-module communication layer.

It may contain:

* File/FileLocation state;
* analysis results;
* classifications;
* ModuleExecution records;
* user decisions;
* Review Queue data;
* selected history;
* configuration-related state where defined by the architecture.

The logical schema is defined by DOC - 005.

---

# 8. Module Input and Output

Every module specification shall define:

* accepted scope;
* required database state;
* configuration;
* files/records inspected;
* data produced;
* filesystem operations permitted;
* error handling;
* Review Queue/user-decision needs.

Modules must not modify unrelated data.

---

# 9. Module Result State

A module execution processes a defined scope.

For successfully processed files, the module stores its current result according to its own specification.

The normal database model does not require a result row for every File × Module combination. Absence of a result means that no current result is stored unless the module explicitly defines another status model.

A module may use ModuleExecution history to determine whether a file was in scope, skipped or failed during a particular run.

---

# 10. ModuleExecution

Each actual invocation should have a corresponding execution record.

Typical information includes:

```text
execution_id
module_id
module_version
started_at
finished_at
status
files_examined
files_processed
files_skipped
files_failed
notes
```

Typical execution states:

```text
STARTING
RUNNING
COMPLETED
COMPLETED_WITH_WARNINGS
CANCELLED
FAILED
```

---

# 11. User Interface Feedback

A user-facing module should expose enough information to determine:

* whether execution started;
* whether it is running;
* whether it completed;
* whether it was cancelled;
* whether an error occurred.

Progress should be reported when it can be measured meaningfully.

---

# 12. Repeated Execution

A module may be executed repeatedly and independently.

It should avoid unnecessary work by reusing valid existing state where appropriate, but repeated execution remains under user control.

Reprocessing policy is defined by DOC - 014 and the individual module specifications.

The current project deliberately does **not** use automatic global model-version invalidation.

When the user wants a complete recalculation after a model/algorithm/rule change, the user may clear the selected module result set using DOC - 205 and then run that module separately.

Running or cleaning one module does not automatically run or clean another module.

---

# 13. Configuration Snapshot

Before execution, the module should load and validate a configuration snapshot according to DOC - 008.

By default the snapshot remains stable for the execution.

---

# 14. Concurrency

The project is primarily single-user.

A module must not assume that duplicate execution is impossible.

Where concurrent execution could create unsafe database or filesystem behaviour, the relevant module shall use appropriate protection such as a lock, active-execution check or explicit user confirmation.

---

# 15. Error Isolation

Failure of one module or one file must not unnecessarily invalidate unrelated completed work.

Successful results should be persisted incrementally where safe.

Per-file errors should be isolated wherever possible.

---

# 16. Cancellation

Long-running modules should support cancellation when this can be done safely.

Cancellation stops new work and preserves already completed valid results.

An execution cancelled by the user must not be recorded as successful completion.

---

# 17. Access and Filesystem Operations

Filesystem operations are subject to the configured Directory Access Policy defined by DOC - 302 and to the permissions specified by the module itself.

`TODO`, `AI`, `FINAL` and other names do not grant permissions by themselves.

---

# 18. Module Ownership

Each module owns the outputs belonging to its documented responsibility.

User decisions are user-owned state and must not be silently overwritten by module output.

---

# 19. Module Categories

Categories are organizational labels, not execution dependencies.

Possible categories include:

```text
Infrastructure
Analysis
Processing
Maintenance / Validation
```

---

# 20. Extensibility

Adding an unrelated module should normally not require modifying existing module logic.

A genuinely new cross-module mechanism should be added to the shared architecture once and then referenced by affected modules.

---

# 21. Reproducibility and History

ModuleExecution stores the installed module version used for a run.

Where useful, configuration and model/rule identifiers may also be recorded at execution level.

This information is for diagnostics and history. It is not a requirement to store a model-generation identifier with every result row.

---

# 22. Logging

Every module follows DOC - 011.

Execution start, completion/cancellation/failure, significant warnings and errors should be logged.

---

# 23. Relationship with Module Interface

```text
DOC - 007
    how modules execute within the system

DOC - 010
    common interface contract

Individual module document
    what the module actually does
```

---

# 24. Acceptance Criteria

DOC - 007 is correctly implemented when:

* newly discovered files become available after Scanner establishes File/FileLocation state;
* modules are independently executable;
* modules communicate persistent state through the database;
* no global runtime pipeline is required;
* repeated executions are valid;
* module execution state is visible and recorded;
* successful work survives unrelated failures;
* configuration is obtained through the common configuration system;
* filesystem operations obey configured access policy;
* module-version information may be recorded at execution level without forcing per-result generation management;
* DOC - 014 and DOC - 205 provide the user-controlled result-recalculation workflow.

---

# End of DOC - 007
