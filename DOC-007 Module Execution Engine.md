# DOC-007

# Module Execution and Architecture

**Project:** AI Image Collection Management System

**Document:** DOC-007

**Version:** 2.2

**Status:** Draft

**Depends on:**

DOC-003
DOC-005
DOC-008
DOC-010
DOC-011
DOC-012

---

# 1. Purpose

This document defines the common execution model and architectural rules for project modules.

It describes how modules are started, how they operate independently, how execution state is exposed to the user, and how module execution is recorded.

This document does not define the internal algorithm of an individual module.

It also does not define the configuration format itself; that responsibility belongs to DOC-008 and, where applicable, collection configuration documentation.

---

# 2. Module Definition

A module is an independent executable component responsible for a clearly defined system function.

Examples include:

```text
Scanner
Color Analysis
Screenshot Analysis
Universe Analysis
Character Analysis
Theme Analysis
File Renamer
Database Maintenance
Collection Consistency Checker
```

A module may read information produced by other modules when that information is relevant to its own operation.

A module must not become responsible for another module's function merely because it consumes its output.

---

# 3. Module Independence and Communication

Each module is independently executable within the limits of its documented input requirements.

A module normally does not require another module process to remain running while it performs its work.

**Modules do not communicate directly with other modules.**

When one module produces information that may be useful to another module, that information is persisted in the shared database. The receiving module reads the current applicable information from the database when it runs.

The intended communication model is therefore:

```text
Module A
    ↓
Database
    ↓
Module B
```

and not:

```text
Module A ─────→ Module B
```

This restriction concerns application-level communication between project modules. It does not prevent a module from using normal operating-system facilities, libraries, filesystem access, GPU resources or other technical resources required for its own operation.

Modules normally terminate after completing the requested operation. The architecture does not require permanently resident module processes.

---

# 4. Scanner as the Base Data Ingestion Module

The **Scanner** is a special infrastructure module because it establishes the database representation of files discovered in configured filesystem roots.

A newly added file cannot be processed by ordinary analysis or processing modules until the Scanner has created or updated the corresponding file record in the database.

This makes Scanner a **data-ingestion prerequisite**, not a global execution prerequisite for all module relationships.

The following principle applies:

```text
new file in configured source/processing root
        ↓
Scanner
        ↓
file identity + filesystem state in database
        ↓
available to other modules
```

Once a file has a valid database record, other modules remain independent of Scanner and of one another. They may be run in any order, provided their own documented input requirements are satisfied.

Scanner does not need to run immediately before every other module execution.

If a file is not yet represented in the database, a module that requires a database file record must skip or report that file according to its own specification rather than inventing a partial file identity.

---

# 5. User-Controlled Execution

Modules are normally started by the user.

The current architecture does not require a global scheduler, automatic workflow engine or dependency resolver.

The user decides:

* which module to run;
* when to run it;
* which configured collection or scope to process;
* how often to run it.

A future component may introduce optional automation without changing the fundamental independence of modules, provided such functionality is explicitly specified.

---

# 6. Execution Order and Dependencies

There is no globally mandatory execution order among ordinary modules.

A module may have logical dependencies on data produced by another module.

For example, a useful operational sequence may be:

```text
Scanner
    ↓
Universe Analysis
    ↓
Character Analysis
```

but the system does not enforce this sequence.

A module dependency means that the required **data must exist in the database**, not that another module must have been executed immediately beforehand or that the other module process must still be running.

A module that requires particular input data must detect the absence or insufficiency of that data and handle the situation according to its own specification.

The resulting execution history may therefore look like:

```text
Day 1–10:
    IRL Analysis × 5

Later:
    Screenshot Analysis × 2

Later:
    IRL Analysis × 1
```

This is valid. The number and timing of executions of one module do not impose a schedule on another module.

---

# 7. Shared Database

The project database is the primary shared persistence and inter-module communication layer.

Modules exchange persistent analysis, classification and processing state through the database rather than through direct calls between module implementations or ad-hoc temporary files.

The database contains information such as:

* file identity and filesystem state;
* analysis results;
* classifications;
* module execution records;
* collection configuration where applicable;
* user decisions;
* review information;
* historical events.

The logical database model is defined by DOC-005.

A module may read information owned by another component when that information is part of the documented input to its operation.

A module may also write information to the database for use by later executions of itself or by other modules, provided that the module owns that information and the write is part of its documented responsibility.

---

# 8. Module Input and Output

Each module specification should define:

* accepted input scope;
* required database state;
* configuration parameters;
* files or records it may inspect;
* data it produces;
* filesystem operations it may perform;
* error conditions;
* user decisions it may request.

A module should not modify data outside its documented responsibility.

For example, an analysis module may create or update its own analysis results but should not silently alter another analysis module's results or user decisions.

---

# 9. Module Results and Per-File Processing State

A module execution operates on a defined scope. For every file that is within that scope and successfully processed, the module should persist its result in the database according to its specification.

This means that the database can distinguish at least between:

```text
module has processed this file
module has not processed this file
module attempted this file but failed
module intentionally skipped this file
```

The absence of a module-specific result does not necessarily indicate an error. A file may have:

* been outside the module's configured scope;
* been added after the module's last execution;
* been skipped because of module rules;
* failed processing;
* not yet been processed by that module.

The exact representation of these states is module-specific, but the architecture must allow them to be distinguished where necessary.

A module result is associated with the file's database identity and the module execution that produced it.

---

# 10. Module Execution Record

Each actual module run should have a corresponding **Module Execution** record as defined by DOC-005.

The execution record may contain:

```text
execution_id
module_id
started_at
finished_at
status
files_processed
files_skipped
files_failed
notes
```

The exact physical schema is defined by the database implementation.

An execution record describes one invocation of a module. It does not represent a file and must not be used as a substitute for file identity.

---

# 11. Execution States

A module execution should expose at least the following logical states:

```text
STARTING
RUNNING
COMPLETED
CANCELLED
FAILED
```

The database execution record may use a subset or implementation-specific representation where appropriate, but the user interface should provide an understandable indication of the execution state.

A module may additionally report intermediate states such as pausing or finalizing if its operation benefits from them.

---

# 12. User Interface Feedback

Every module with a user-facing interface should provide visible confirmation that execution has started.

At minimum, the user should be able to determine:

* whether the module has started;
* whether it is currently running;
* whether it completed successfully;
* whether it was cancelled;
* whether an error occurred.

A progress indicator should be used when meaningful progress can be measured.

Where progress cannot be estimated reliably, an activity indicator and useful status information are sufficient.

The purpose is not merely cosmetic: visible execution state reduces the risk of the user accidentally launching the same operation repeatedly because the first invocation appears unresponsive.

---

# 13. Repeated Execution

A module may be executed repeatedly.

Repeated execution is not inherently an error.

The module must use the database state and its own specification to determine which records require work.

A module should avoid unnecessary reprocessing where the relevant analysis or state is already valid, but the decision to rerun a module remains under user control unless a future automation mechanism explicitly changes this rule.

Detailed reprocessing rules belong to the relevant module and future reprocessing architecture such as DOC-205.

Repeated execution of one module does not require or imply execution of any other module.

---

# 14. Concurrent Execution

The project is primarily designed for a single user.

The architecture does not require a complex global concurrency manager.

However, modules must not assume that duplicate execution is impossible.

Where simultaneous execution could corrupt data, duplicate work or produce unsafe filesystem operations, the relevant module must provide appropriate protection.

Such protection may include:

* refusing a second instance;
* detecting an active execution record;
* acquiring a local lock;
* requiring explicit user confirmation.

The mechanism should be proportional to the actual risk.

A module must not rely solely on the user remembering whether another instance is running.

---

# 15. Error Isolation

Failure of one module must not invalidate unrelated completed work.

A module should preserve successfully completed operations whenever safe to do so.

For example:

```text
File A → processed successfully
File B → processed successfully
File C → processing failed
```

The successful results for A and B should not be discarded merely because C failed.

The exact transaction boundaries are defined by the individual module and database specifications.

Errors must be logged according to DOC-011.

Cases requiring user intervention should use Review Queue where appropriate.

---

# 16. Cancellation

A user should be able to cancel a long-running module when the module can safely support cancellation.

Cancellation should stop new work and allow the module to leave already completed work in a valid state.

A cancellation must not be represented as a successful completion.

The execution record should distinguish at least between successful completion, cancellation and failure.

Modules that cannot safely stop immediately may finish their current atomic operation before terminating.

---

# 17. Configuration

Modules obtain configurable behaviour from the project configuration system rather than hard-coding collection-specific paths or assumptions.

Examples include:

```text
input root
recursive scanning
access policy
processing limits
confidence thresholds
enabled/disabled state
```

Configuration ownership is defined by DOC-008 and collection configuration documents.

A module should not infer architectural meaning from directory names such as `TODO`, `AI`, `FINAL`, `Anime` or `Themes`.

---

# 18. Access and Filesystem Operations

A module may inspect or modify files only within the scope permitted by its configuration and the applicable Directory Access Policy.

The fact that a directory is considered part of a final collection does not by itself make it permanently immutable.

For example, a consistency or classification workflow may identify a wrongly placed file in a final tree. The normal correction mechanism may move the file into an appropriate workspace for user review rather than silently modifying the final collection.

The detailed access policy is defined by the project-wide Directory Access Policy specification.

---

# 19. Module Ownership

Each module has a defined responsibility and owns the outputs that belong to that responsibility.

Ownership means that the module is responsible for maintaining the validity of its own results; it does not mean that the module may arbitrarily modify the rest of the database.

Examples:

```text
Scanner
    filesystem discovery and synchronization state

Universe Analysis
    universe analysis results

Character Analysis
    character analysis results

File Renamer
    permitted filename changes

Database Maintenance
    maintenance operations defined by its specification
```

User decisions remain user-owned information and must not be silently overwritten by module output.

---

# 20. Module Categories

Module categories are organizational labels, not execution dependencies.

They may include:

### Infrastructure

Examples:

```text
Scanner
Configuration Manager
Collection Definition Wizard
```

### Processing

Examples:

```text
AutoSort
File Renamer
```

### Analysis

Examples:

```text
Color Analysis
Screenshot Analysis
Reaction Image Analysis
IRL Analysis
Cosplay Analysis
Universe Analysis
Character Analysis
Theme Analysis
Set Detection and Grouping
```

### Maintenance / Validation

Examples:

```text
Database Maintenance
Collection Consistency Checker
```

Categories may be changed or extended without changing the execution model.

---

# 21. Extensibility

Adding a module should normally require:

* implementing the module;
* defining its interface and configuration requirements;
* registering it where required by the application;
* defining any new persistent data required by its specification;
* documenting its behaviour.

Existing modules should not need modification merely because an unrelated module was added.

This principle does not prohibit changes to shared standards when a genuinely new architectural requirement affects multiple modules.

For example, a new module may reveal the need for a new shared logging or database concept. In such a case, the shared standard should be updated rather than duplicating the concept in every module.

---

# 22. Reproducibility

Where practical, a module should produce results that can be explained and reproduced from:

* its version;
* relevant configuration;
* input data;
* database state;
* applicable model or rule version.

Perfect bit-for-bit reproducibility is not required for inherently probabilistic AI models unless a specific module requires it.

Execution records should contain enough information to identify which module version performed the operation.

---

# 23. Logging

Every module must produce logs according to DOC-011.

At minimum, logging should allow the user to determine:

* what operation was started;
* when it started;
* what happened during execution;
* whether execution completed, failed or was cancelled;
* which significant errors occurred;
* whether user intervention is required.

Module-specific logging requirements belong to the module's own specification.

---

# 24. Relationship with Module Interface

DOC-007 defines the common execution architecture.

DOC-010 defines the common module interface contract.

The distinction is:

```text
DOC-007
    How modules operate within the system

DOC-010
    What interface a module exposes
```

Individual module documents define what each module actually does.

DOC-007 must not duplicate the detailed interface fields defined by DOC-010.

---

# 25. Relationship with Configuration Manager

DOC-008 defines configuration management.

DOC-007 establishes that modules obtain configurable behaviour through the configuration system and do not hard-code collection-specific paths or roles.

The execution engine itself does not become the owner of collection definitions merely because it consumes their configuration.

---

# 26. Acceptance Criteria

The module architecture is considered correctly implemented when:

* the Scanner can establish database file records for newly discovered files;
* ordinary modules can use those database records without requiring the Scanner process to remain running;
* modules can be executed independently of one another;
* the user controls execution under the current architecture;
* modules do not require another module process to remain active;
* modules do not communicate directly with other modules;
* persistent inter-module information is exchanged through the shared database;
* repeated executions of one module do not require repeated executions of another module;
* execution state is visible to the user;
* executions are recorded appropriately;
* failures do not unnecessarily invalidate unrelated completed work;
* user decisions are not silently overwritten;
* configuration is not replaced by hard-coded collection paths or roles;
* adding an unrelated module does not require unnecessary modification of existing modules.

---

# End of DOC-007
