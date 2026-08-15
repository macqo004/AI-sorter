# DOC-010

# Module Interface Specification

**Project:** AI Image Collection Management System

**Document:** DOC-010

**Version:** 2.2

**Status:** Draft

**Depends on:**

DOC-003
DOC-005
DOC-007
DOC-008
DOC-011
DOC-012
DOC-013

---

# 1. Purpose

This document defines the common interface contract for project modules.

It specifies the information and behaviour that a module exposes to the surrounding application and to the user interface. It does not define the internal algorithm of a module.

DOC-007 defines the common module execution architecture. DOC-010 defines the common interface contract used by individual module specifications.

---

# 2. Module Independence

A module is an independently executable component with a clearly defined primary responsibility.

Modules do not communicate directly with one another. Persistent information exchanged between modules is exchanged through the project database.

The modules are intentionally not arranged into a mandatory global processing pipeline. One module may be executed many times before or after another module, and one module may be run without running other modules again.

For example, the following is valid:

```text
IRL Analysis × 5
Screenshot Analysis × 2
IRL Analysis × 1
```

The final IRL execution is an independent execution. It reads the current database state available to it and does not continue a process owned by Screenshot Analysis.

A module may benefit from information previously written by another module, but the producing module does not need to be running.

A module may use the filesystem, operating-system facilities, libraries, GPU resources and other resources required for its own work. These are not considered direct module-to-module communication.

---

# 3. Base Data-Ingestion Requirement

The **Scanner** is the base data-ingestion module.

A new file added to a configured processing/source root must first be discovered by Scanner and represented in the database before ordinary modules can process that file through the database-driven architecture.

Therefore:

```text
new filesystem file
        ↓
Scanner
        ↓
valid database file record
        ↓
other modules may process the file
```

This is a data-availability requirement, not a general module-ordering rule.

After a valid file record exists, other modules remain independent of Scanner and of one another. Scanner does not need to run immediately before another module execution.

A module that requires a file record must not invent a temporary file identity when the record does not exist.

---

# 4. Required Module Information

Every module should expose, at minimum:

```text
Module ID
Module Name
Module Version
Description
Category
```

The exact representation is implementation-specific.

An optional author or maintainer field may be provided but is not required for functional operation.

---

# 5. Initialization Contract

When a module starts, it shall perform the initialization checks required for safe execution.

Depending on the module, these may include:

* loading configuration;
* validating configuration;
* validating the selected collection or processing scope;
* checking required directories;
* checking database accessibility;
* checking database/schema compatibility;
* preparing required resources;
* determining the module version/rule/model version applicable to the run.

A module must fail clearly rather than start unsafe processing when a required precondition is not satisfied.

Modules may omit checks that are irrelevant to their operation.

---

# 6. Input Contract

Each module specification shall document its required inputs.

Inputs may include:

* project database state;
* configuration;
* collection definitions;
* filesystem content within the permitted scope;
* user-selected files or directories;
* module-specific resources.

A module must not require another module process to be running in order to obtain data from it.

Where a module depends on results produced by another module, that dependency is expressed as a database data requirement.

The presence of another module's result is therefore a property of database state, not a process-level dependency.

---

# 7. Output Contract

Each module specification shall document the outputs it may produce.

Outputs may include:

* database records owned by the module;
* updates to filesystem state when explicitly permitted;
* log entries;
* reports;
* exported data;
* generated support files.

A module must not silently create side effects outside its documented responsibility.

Modules shall write persistent information that may be useful to other modules to the shared database. Such information becomes available to other modules through the database without requiring direct communication between the modules.

---

# 8. Database Ownership and Shared Information

A module owns the analysis or operational data it is explicitly responsible for producing.

Examples:

```text
Scanner
    filesystem discovery and file-state synchronization

Universe Analysis
    universe analysis results

Character Analysis
    character analysis results

Theme Analysis
    theme analysis results

File Renamer
    permitted filename modifications
```

A module may create information intended for use by other modules. Other modules may read that information from the database, provided the relevant data contract is documented.

A module must not silently overwrite results owned by another module or user decisions.

The logical database model is defined by DOC-005.

---

# 9. File Identity

Modules shall use the project's File Identity Model when referring to files.

SHA512 is the logical identifier of the binary content of a file. `file_id`, where used, is an internal technical database identifier.

Modules must not use filename or path as the primary identity of a file.

Renaming or moving a file does not change its SHA512 identity.

If the file's binary content changes and therefore its SHA512 changes, the module must treat the resulting binary object according to DOC-012 rather than silently continuing to treat it as the previous binary object.

---

# 10. Configuration

Configurable parameters shall be obtained from the project configuration system rather than hard-coded into the module.

Examples include:

* thresholds;
* worker-thread counts;
* processing limits;
* paths and roots;
* access policies;
* model settings;
* cache limits;
* reporting options.

Configuration ownership is defined by DOC-008 and applicable collection configuration documents.

A module must not infer functional meaning from a physical directory name such as `TODO`, `AI`, `FINAL`, `Anime` or `Themes`.

---

# 11. Collection Scope

When a module operates on a collection, the scope shall be obtained from the configured Collection Definition rather than hard-coded paths.

A module specification shall document which logical root roles it accepts, for example:

```text
SOURCE
TRANSITION
FINAL
```

and which operations it is allowed to perform within those roots.

The physical locations of the roots are defined by collection configuration.

---

# 12. Access Policy

Filesystem operations are subject to the configured Directory Access Policy and the module's own permitted operations.

The module interface must make clear which operations the module may request, such as:

```text
READ
RENAME
MOVE
CREATE
DELETE
```

The module must not assume that `FINAL` is inherently immutable. A final tree may contain historical classification errors and may require a controlled correction workflow.

At the same time, a module must not autonomously perform corrective changes merely because it believes a file is misplaced when the applicable workflow requires user review.

The detailed Directory Access Policy is defined by the project-wide access-policy specification.

---

# 13. Execution State

A module shall expose a user-visible execution state while running.

The logical state set includes:

```text
STARTING
RUNNING
COMPLETED
COMPLETED_WITH_WARNINGS
CANCELLED
FAILED
```

An implementation may use additional internal states.

The user interface must make the current state understandable without requiring inspection of technical logs.

---

# 14. Progress Reporting

A module should report progress when meaningful progress can be measured.

Possible information includes:

* percentage;
* processed item count;
* total item count when known;
* current operation;
* activity indicator.

When reliable percentage progress cannot be calculated, a useful activity indicator and current-operation status are sufficient.

---

# 15. Cancellation

A long-running module should support user cancellation when this can be implemented safely.

Cancellation should:

* stop new work where possible;
* preserve already completed valid work;
* leave the database and filesystem in a consistent state;
* record the execution as cancelled rather than completed.

A module may finish the current safe/atomic operation before terminating.

---

# 16. Logging

Every module shall log its execution according to DOC-011.

At minimum, logs should make it possible to determine:

* that execution started;
* what module/version was running;
* the significant operations performed;
* warnings and errors;
* whether execution completed, failed or was cancelled;
* whether user intervention is required.

Module-specific log details belong in the module specification.

---

# 17. Error Handling

A module shall distinguish between errors that can be handled locally and errors that prevent safe continuation.

Examples of recoverable conditions may include:

* unreadable individual image;
* unsupported file encountered during scanning;
* malformed optional metadata.

Examples of execution-blocking conditions may include:

* unavailable required database;
* incompatible schema;
* invalid required configuration;
* missing mandatory processing root.

An error in one module must not invalidate unrelated completed work performed by other modules.

Cases requiring a user decision should use the Review Queue mechanism where applicable.

---

# 18. Memory and Resource Usage

Modules may use available RAM and other local resources where this provides a meaningful performance benefit.

Resource usage should be adaptive rather than artificially restricted to a minimal footprint.

Modules must avoid exhausting system resources and should release memory/resources that are no longer useful.

Detailed resource limits may be configurable through DOC-008 or module-specific configuration.

---

# 19. Parallel Processing

A module may internally use multiple worker threads or processes where beneficial.

Parallelism is an implementation detail unless the module specification exposes it as a configuration option.

When exposed, worker counts should be configurable.

Parallel execution must not violate database or filesystem consistency rules.

---

# 20. Repeated Execution and Reprocessing

Modules may be executed repeatedly and independently of other modules.

The number and timing of executions of one module do not determine when another module may execute.

For example:

```text
IRL Analysis × 5
Screenshot Analysis × 2
IRL Analysis × 1
```

is a valid execution history. The later IRL run reads the current database state and may use information previously written by Screenshot Analysis, without requiring Screenshot Analysis to run again or remain active.

A module must not assume that it runs only once.

Where possible, it should use existing database state to avoid unnecessary work.

The decision to rerun remains under user control under the current architecture.

Detailed reprocessing rules, including analysis-version invalidation, belong to the relevant module specification and future reprocessing architecture.

---

# 21. Per-File Module Results

When a module is executed while a file is within that module's configured processing scope, the module should create or update the database result applicable to that file, provided the file is successfully processed.

This allows the database to represent module coverage on a per-file basis.

For example, a file may have:

```text
IRL Analysis        → result present
Screenshot Analysis → result present
Universe Analysis   → result absent
```

The absence of a result for a particular module does not by itself mean that the module failed. The file may not have been in that module's scope when it last ran, the module may not yet have been run for that file, or the file may have been skipped or failed according to the module's rules.

Each module is responsible for defining how its own result state is represented and how later executions determine whether processing is required.

---

# 22. Input/Output Documentation

Each module document shall clearly define:

* what it reads from the database;
* what it writes to the database;
* what files it may inspect;
* what filesystem operations it may perform;
* what reports it produces;
* what generated files it may create;
* what user decisions it may require.

There must be no undocumented operational side effects.

---

# 23. Module Interface vs Module Specification

DOC-010 defines common requirements that apply to modules generally.

An individual module document defines the module-specific behaviour.

For example:

```text
DOC-010
    Module must report execution state.

DOC-101
    Scanner reports scan progress by discovered file count.
```

The module specification may strengthen or narrow a generic rule when necessary, provided the exception is explicitly documented and does not contradict a higher-level safety or architectural requirement.

---

# 24. Dependency Declaration

Each module shall document its meaningful data dependencies.

Example:

```text
Scanner
    Input: filesystem
    Output: file state / SHA512

Universe Analysis
    Input: files + relevant analysis data
    Output: universe classification

Character Analysis
    Input: files + relevant universe information
    Output: character classification
```

These dependencies describe data requirements only.

They do not create direct module-to-module process dependencies or enforce global execution order.

---

# 25. Module Categories

Categories are organizational labels and do not define execution dependencies.

Examples include:

```text
Infrastructure
Analysis
Processing
Maintenance / Validation
```

Future categories may be introduced when useful.

---

# 26. Extensibility

Adding a new module should normally require:

* implementing the module;
* defining its interface metadata;
* defining configuration requirements;
* documenting inputs and outputs;
* registering it with the application where required.

Existing modules should not require modification merely because an unrelated module was added.

This does not prevent updates to shared standards when a genuinely new architectural requirement affects multiple modules.

---

# 27. Interface Compliance

A module is compliant with DOC-010 when its specification and implementation provide, as applicable:

* identifiable module metadata;
* safe initialization and validation;
* documented inputs and outputs;
* access to configuration through the common configuration system;
* conformance to the File Identity Model;
* visible execution status;
* appropriate progress information;
* cancellation handling where supported;
* logging according to DOC-011;
* isolation of module errors;
* respect for database ownership and user decisions;
* operation within the configured collection scope and access policy;
* independent execution without requiring another module process to run;
* per-file persistence of its applicable results when files within its scope are successfully processed.

Not every module needs every optional feature. The module's own specification determines which interface elements are applicable.

---

# 28. Relationship with Other Documents

```text
DOC-003  System Architecture
DOC-005  Database Schema
DOC-007  Module Execution and Architecture
DOC-008  Configuration Manager
DOC-011  Logging Standard
DOC-012  File Identity Model
DOC-013  Review Queue
```

DOC-010 must not redefine the detailed rules owned by those documents.

---

# End of DOC-010
