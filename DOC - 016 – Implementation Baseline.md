# DOC - 016

# Implementation Baseline

**Project:** AI Image Collection Management System

**Document:** DOC - 016

**Version:** 1.0

**Status:** Design Specification

**Depends on:** DOC - 000, DOC - 001, DOC - 002, DOC - 003, DOC - 005, DOC - 006, DOC - 007, DOC - 008, DOC - 009, DOC - 010, DOC - 011, DOC - 012, DOC - 013, DOC - 014, DOC - 015

---

# 1. Purpose

This document defines the implementation baseline for the first working version of the AI Image Collection Management System.

The previous documentation set defines what the system is, what its modules are responsible for, how persistent state is represented and how files are handled. DOC - 016 defines how those architectural decisions are translated into a real desktop application.

This document is intentionally implementation-oriented. It establishes the minimum technical structure that must be present before the first production-oriented modules are implemented.

It does not replace the functional specifications of individual modules. A module remains responsible for its own behaviour according to its dedicated specification.

---

# 2. Implementation Goals

The initial application shall be:

* designed for Windows 10 and Windows 11, with Windows 11 as the primary target;
* implemented primarily in Python;
* fully usable offline;
* distributed as a portable, self-contained application package;
* based on one SQLite database per project;
* usable through a graphical user interface from the first functional release;
* modular, so that individual analysis modules can be executed independently;
* safe for very large collections;
* explicit about the difference between user-facing information and technical diagnostics;
* capable of continuing after per-file failures where the relevant operation is safe to continue;
* structured so that the GUI does not contain the application's business logic;
* maintainable without requiring the user to understand programming or database internals.

---

# 3. Target Runtime Environment

## 3.1 Operating System

The supported desktop operating systems are:

```text
Windows 10
Windows 11
```

Windows 11 is the primary development and test target.

Compatibility with substantially older Windows versions is not required by the initial implementation.

## 3.2 Python

Python is the primary implementation language.

The project shall use a pinned, explicitly supported Python runtime for development and packaging. The exact Python minor version is an implementation/build decision and shall be recorded in the repository's build configuration rather than assumed implicitly.

Third-party dependencies shall be explicitly pinned or constrained so that a reproducible application build can be produced.

## 3.3 Internet Connectivity

Permanent Internet access is not a runtime requirement.

The application shall be able to operate using:

* locally installed Python/runtime components;
* locally stored models;
* local configuration;
* local database files;
* local image files.

Any future online functionality must be explicitly designed as an optional feature and must not become a hidden dependency of existing offline workflows.

---

# 4. Application Distribution Model

The initial application shall use a portable/self-contained layout.

The user should be able to move the complete application directory to another supported Windows system without manually tracking a large number of application-specific locations.

The application may depend on normal Windows system components, but project-specific state should remain inside the application package or in explicitly configured external collection paths.

A typical runtime layout is:

```text
AI-Sorter/
├── AI-Sorter.exe
├── app/
├── config/
├── data/
│   └── project.db
├── logs/
├── cache/
├── models/
├── modules/
├── backups/
├── temp/
└── README.txt
```

The exact executable and internal Python packaging layout may differ, but the following principle is mandatory:

> Project-specific application state should be grouped in one portable application location rather than being scattered across unrelated system directories.

The collection itself remains outside the application package unless the user explicitly chooses a collection path inside it.

---

# 5. Runtime Directory Responsibilities

## 5.1 `data/`

Contains the active project database and, where appropriate, other durable local project data.

The default database is:

```text
project.db
```

One project uses one database.

## 5.2 `config/`

Contains application and project configuration that is not itself the SQLite database.

Configuration may include:

* GUI preferences;
* logging settings;
* execution defaults;
* model configuration;
* local runtime settings;
* portable installation settings.

Collection Definition information belongs to the Collection Definition architecture and may be persisted in the database and/or an explicitly defined portable configuration representation according to DOC - 301 and DOC - 302.

## 5.3 `models/`

Contains locally installed AI/ML models and their associated metadata.

Models are not stored inside the SQLite database.

A typical structure is:

```text
models/
├── irl/
├── screenshot/
├── universe/
├── character/
├── color/
└── future-modules/
```

A module may require one or more model files.

Each model package should have enough local metadata to determine:

* model identifier;
* model type;
* supported module;
* expected files;
* compatibility information where required;
* integrity information where practical.

A model is loaded only when the relevant module actually requires it.

The application shall not load every installed model into memory during startup merely because the files exist in `models/`.

## 5.4 `cache/`

Contains disposable runtime cache data.

Cache data must never be treated as the authoritative source for file identity, classification or user decisions.

Cache may be deleted and recreated without changing project correctness.

## 5.5 `logs/`

Contains persistent technical logs and, where useful, human-readable execution summaries.

The logging architecture follows DOC - 011.

## 5.6 `backups/`

May contain locally generated project backups or recovery packages created by the application.

Backups are not a substitute for an external backup strategy.

## 5.7 `temp/`

Contains temporary working files.

Temporary files must not be used as an alternative persistent inter-module communication mechanism.

The application should remove abandoned temporary files when safe and must tolerate stale temporary data from an interrupted previous run.

---

# 6. Project Model

The first implementation supports:

```text
1 project
    ↓
1 SQLite database
```

The GUI may later support selecting between multiple projects, but the initial architecture must not require a multi-project database design.

All modules operating inside a project use the same project database.

A project database is therefore the common persistent state layer for:

* file identities;
* physical locations;
* module results;
* classifications;
* user decisions;
* execution history;
* Review Queue state;
* Collection Definition state where persisted;
* relevant application history.

---

# 7. Application Layering

The implementation shall separate the user interface from business and module logic.

The baseline architecture is:

```text
┌──────────────────────────┐
│           GUI            │
│        PySide6           │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ Application / Services   │
│ orchestration of user    │
│ actions and workflows    │
└────────────┬─────────────┘
             │
      ┌──────┼──────┐
      ▼      ▼      ▼
   Scanner  IRL  Universe ...
      │      │      │
      └──────┼──────┘
             ▼
┌──────────────────────────┐
│      DB Access Layer     │
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│          SQLite          │
└──────────────────────────┘
```

The GUI is an interface to application services. It is not the owner of database queries, file moves, model inference or module-specific business rules.

---

# 8. GUI Technology

PySide6 is the baseline GUI framework.

The GUI shall be implemented as a normal desktop application rather than a browser-based interface or a wrapper around a command-line application.

The first GUI may be deliberately simple. It should prioritise correctness, visibility of state and safe operation over visual sophistication.

The architecture shall remain compatible with later addition of:

* richer navigation;
* progress views;
* Review Queue interfaces;
* file previews;
* module management;
* execution history;
* configuration editors;
* maintenance and recovery screens.

---

# 9. GUI Responsiveness

The GUI main thread must remain responsive while long-running operations are active.

Operations that may take significant time shall not execute directly inside GUI event handlers.

Examples include:

* filesystem scanning;
* SHA512 calculation;
* image decoding;
* model loading;
* AI inference;
* large database queries;
* duplicate analysis;
* large move/rename operations;
* cleanup operations affecting large result sets.

Such work shall be executed by background workers/services using an appropriate concurrency mechanism.

The GUI shall receive progress, status and error information through explicit application-level communication rather than directly polling implementation internals wherever practical.

---

# 10. GUI and Execution Architecture

The GUI shall not start another copy of the application to perform normal work.

The normal execution path is:

```text
User action
    ↓
GUI
    ↓
Application Service
    ↓
Module / Utility
    ↓
DB Access Layer / filesystem / model runtime
```

The project does not require a permanent CLI process behind the GUI.

A future CLI can be implemented as another front-end over the same application services:

```text
GUI ─────┐
         ├──→ Application Services
CLI ─────┘
```

The GUI and any future CLI therefore do not duplicate module logic.

This avoids unnecessary process creation, inter-process communication and duplicated resource usage.

---

# 11. Application Services

The Application/Services layer is responsible for translating user actions into safe project operations.

Examples include:

```text
ProjectService
ConfigurationService
ModuleService
ExecutionService
FileOperationService
ReviewService
MaintenanceService
RecoveryService
```

These names are logical responsibilities, not mandatory class names.

A service may coordinate multiple lower-level components, but module-specific analysis logic remains in the relevant module.

---

# 12. Module Runtime

Modules are independent components as defined by DOC - 007 and DOC - 010.

A module is started explicitly by the user or by a documented application workflow.

Once started, the module may:

* read the database;
* read required filesystem state;
* read relevant existing analysis results;
* load its own required model(s);
* write its own results and execution state;
* create applicable Review Queue information;
* report progress and errors.

A module shall not directly invoke another analysis module.

Persistent inter-module information exchange occurs through the database.

---

# 13. Module Loading and Resource Management

Modules should be loaded lazily when practical.

The application should not initialise all modules and all models at startup simply because they are installed.

A module may remain loaded during a single execution or reuse already loaded resources during repeated executions within the same application process where this improves performance and is safe.

Examples:

```text
Application starts
    ↓
No AI model loaded

User starts IRL
    ↓
IRL module loads its model
    ↓
IRL processes files

User starts Screenshot
    ↓
Screenshot loads only what it requires
```

Resource ownership and release must remain explicit so that memory-heavy models can be unloaded when no longer needed.

---

# 14. Database Access Layer

All persistent database operations shall pass through the project's DB Access Layer defined by DOC - 009.

Modules should not embed arbitrary database connection management throughout their implementation.

The DB Access Layer shall provide controlled access to:

* File;
* FileLocation;
* Module;
* ModuleExecution;
* Analysis Results;
* Classification Results;
* Review Queue;
* User Decisions;
* File Events;
* Collection Definition state;
* relevant maintenance data.

The layer should also provide controlled transaction handling and error translation.

---

# 15. SQLite Runtime Rules

SQLite is the initial database engine.

The application shall use one project database connection strategy appropriate to its concurrency model.

Database access must account for:

* concurrent readers;
* background workers;
* write contention;
* transaction boundaries;
* database locking;
* interrupted operations;
* clean shutdown.

The application must not assume that a database write will always succeed immediately.

Recoverable locking conditions should be handled according to the application's retry and user-notification policy.

A database error must never be silently ignored.

---

# 16. Transaction Boundaries

The application shall use transactions where a group of related database changes must be atomic.

It shall not use one transaction for the entire processing of millions of files merely for convenience.

Operations should normally use safe units such as:

```text
one file
one safe batch
one logical user operation
```

The exact transaction scope belongs to the relevant module.

Successful work must survive unrelated later failures wherever the operation is designed to continue incrementally.

---

# 17. Scanner as First Implemented Module

The Scanner is the first complete production-oriented module to be implemented after the application baseline.

Its baseline flow is:

```text
Filesystem
    ↓
Scanner
    ↓
read file metadata
    ↓
calculate/verify SHA512
    ↓
lookup File by SHA512
    ↓
create/reactivate File as appropriate
    ↓
create/update FileLocation
    ↓
record execution state
```

A file must have a valid database identity before ordinary database-driven analysis modules process it.

The Scanner shall support incremental progress and must not lose successfully recorded files merely because a later file fails.

Detailed Scanner behaviour remains defined by DOC - 101.

---

# 18. File Operation Safety

Physical file operations are high-impact operations and shall be separated from pure analysis where practical.

The implementation shall distinguish at least:

```text
ANALYSIS
    read-only inspection

PROPOSAL
    suggested operation

APPROVED ACTION
    user-approved or explicitly authorised operation

EXECUTION
    physical filesystem change

VERIFICATION
    check resulting state
```

A module producing a classification must not be assumed to have permission to move or delete a file.

AutoSort and file-operation services shall enforce access policy from Collection Definition.

---

# 19. File Operation Atomicity and Recovery

Operations involving physical files shall be designed so that interrupted actions do not silently create inconsistent state.

Where a multi-step operation is required, the implementation should record sufficient execution state to determine what was attempted, what completed and what remains to be reconciled.

The application must not report a file operation as successful merely because the database was updated before the filesystem operation completed.

Database and filesystem changes shall be reconciled according to DOC - 402, DOC - 403 and DOC - 404.

---

# 20. Human-Readable Error Model

User-facing error communication is a formal application requirement.

The user must not be expected to understand Python exceptions, SQL syntax, stack traces or library-specific error codes in order to understand what happened.

A user-facing error should explain, as applicable:

1. what failed;
2. why it failed when the cause is known;
3. whether the user's files were changed;
4. what the user can do next;
5. where technical details are available.

Bad example:

```text
OperationalError: database is locked
```

Better example:

```text
The changes could not be saved because the project database is currently busy.
No image files were changed.
The application will retry automatically. If the problem continues, check the
technical log for details.
```

Another example:

```text
IRL analysis could not start because the required model was not found.
Check the models\irl folder and verify that the configured model is installed.
No files were modified.
```

---

# 21. Error Severity Levels

The application should distinguish at least:

```text
INFO
WARNING
ERROR
CRITICAL
```

## INFO

Normal successful or informative activity.

Example:

```text
Scanner completed. 1,245 new files were registered.
```

## WARNING

The operation completed partially or encountered a non-fatal issue.

Example:

```text
17 files could not be read. The remaining files were processed normally.
```

## ERROR

The requested operation could not be completed, but the rest of the application remains usable.

Example:

```text
IRL analysis could not start because its model is unavailable.
```

## CRITICAL

The application cannot safely continue the current operation or project state requires recovery.

Example:

```text
The project database could not be opened.
No file operation was started.
The application cannot continue until the database is restored or repaired.
```

---

# 22. Technical Diagnostics

Human-readable messages do not replace technical diagnostics.

Each significant error should have a technical record containing, where applicable:

```text
error_id
execution_id
module_id
operation
timestamp
exception type
technical message
stack trace
related file_id / SHA512
path where safe to record
```

Technical details should normally be available through:

```text
[ Show details ]
```

or an equivalent diagnostics view.

The complete technical record belongs in the log system according to DOC - 011.

---

# 23. Safety State in Error Messages

For operations involving files or the project database, error communication should state the known safety state whenever possible.

Examples:

```text
No image files were changed.
```

```text
3 files were moved successfully. 1 file could not be moved.
```

```text
The database update failed after the physical move. Reconciliation is required.
```

The application must not claim that files were unchanged when that fact has not been established.

---

# 24. Progress Reporting

Long-running operations shall provide meaningful progress information when a measurable unit of work exists.

Progress may include:

```text
processed
remaining
failed
skipped
current operation
elapsed time
estimated remaining time where reliable
```

For very large collections, progress must not require storing millions of individual GUI objects.

The GUI should display aggregate information and the current operation rather than rendering an item-level UI for every file.

---

# 25. Cancellation

Long-running modules and utilities should support user cancellation where technically safe.

Cancellation means:

```text
request stop
    ↓
finish current safe unit
    ↓
record cancellation
    ↓
leave already completed work intact
```

Cancellation must not be implemented as an unclean process termination unless there is no safer option.

The database and filesystem state after cancellation must remain recoverable through the relevant module and recovery procedures.

---

# 26. Logging Integration

Every substantial execution shall create an execution context suitable for correlation between:

* GUI messages;
* module execution records;
* database changes;
* technical logs;
* Review Queue actions;
* file operations.

The application should use a common execution identifier where practical.

The GUI should display useful summaries while technical details remain in logs.

Logging follows DOC - 011.

---

# 27. Configuration Handling

Configuration is loaded through the Configuration Manager defined by DOC - 008.

The application shall distinguish:

```text
application configuration
project configuration
Collection Definition
module configuration
runtime state
```

Configuration must be validated before a dependent operation begins.

An invalid configuration should produce a human-readable error explaining which setting is invalid and what is expected.

Configuration changes must not silently rewrite unrelated database state.

---

# 28. Collection Definition Integration

The application loads the Collection Definition according to DOC - 301, DOC - 302 and DOC - 303.

Before physical filesystem operations occur, the application shall know:

* relevant roots;
* logical roles;
* access policies;
* recursive/traversal rules;
* applicable collection boundaries.

Modules must not infer these rules from directory names.

---

# 29. Traversal and Scan Boundaries

All recursive filesystem operations must use an explicit traversal configuration.

A scanner or module must not assume that every nested directory under a root is an image classification level.

Traversal depth and boundary rules must support situations such as:

```text
Collection/
├── Anime/
│   └── Genshin Impact/
│       └── Furina/
│           └── 001/
│               └── image.jpg
```

where `001` is a physical Set directory and must not be interpreted as a character merely because it is nested deeply.

Traversal and classification boundaries are defined by Collection Definition and relevant module specifications.

---

# 30. Model Management

Models are local project assets.

The implementation shall provide a model management mechanism sufficient to:

* identify installed models;
* validate required model files before execution;
* load models lazily;
* release model resources when no longer needed;
* report missing or incompatible models clearly;
* avoid downloading models implicitly during normal offline execution.

Model metadata may include:

```text
model_id
module_id
name
version
path
format
integrity/check information
compatibility information
```

A model identifier may be used for diagnostics and execution history.

The project does not require model generation information to be stored with every analysis result merely to control result invalidation. DOC - 014 and DOC - 205 define that lifecycle.

---

# 31. Model Memory Management

Large models shall not be loaded unnecessarily.

The application should prefer:

```text
lazy loading
resource reuse during an active execution
explicit release when safe
```

For example, if IRL processes a large batch, the IRL model should normally remain loaded for that execution rather than being loaded and unloaded for every individual image.

The application should not keep every available model resident in memory merely because several modules are installed.

---

# 32. Concurrency Model

Concurrency shall be explicit and bounded.

The application should distinguish between:

```text
GUI thread
background application workers
module worker pools
I/O operations
model inference workers
```

The exact concurrency mechanism may use Python threads, processes or library-specific execution facilities according to the module's workload.

The GUI must remain responsive regardless of the chosen implementation.

Worker counts and resource limits shall be configurable where appropriate.

The implementation must not create an unbounded number of threads or processes from a collection size alone.

---

# 33. Memory Management for Large Collections

The application shall not assume that a collection can be loaded entirely into RAM.

Designs should use:

* batching;
* streaming iteration;
* bounded queues;
* incremental database queries;
* controlled image loading;
* explicit release of large buffers.

A module should process one file or a bounded batch at a time unless the algorithm specifically requires another strategy.

---

# 34. Testing Baseline

Automated tests shall exist before large-scale implementation of the modules begins.

At minimum the project should provide:

```text
unit tests
integration tests
database tests
filesystem operation tests
configuration tests
GUI/service integration smoke tests
```

The first tests should focus on the project foundation rather than AI accuracy.

---

# 35. Minimum Foundation Test Set

Before the Scanner is considered production-ready, the implementation should pass tests for at least:

1. application startup with a new project;
2. creation/opening of the SQLite database;
3. schema initialization;
4. loading and validation of Collection Definition;
5. human-readable handling of invalid configuration;
6. creation of a File from a valid SHA512;
7. creation of a FileLocation for that File;
8. two locations sharing one SHA512 resolving to one File;
9. rename/move without SHA512 change preserving File identity;
10. changed content producing a new SHA512 identity;
11. independent ModuleExecution records;
12. successful partial progress surviving a later per-file failure;
13. safe cancellation of a long-running operation;
14. technical error logging;
15. GUI remaining responsive during a background operation;
16. portable startup without hidden application-specific dependencies.

---

# 36. GUI Testing Requirements

GUI tests should focus on application behaviour rather than screenshot matching.

Important scenarios include:

* startup failure;
* database locked/busy state;
* missing model;
* invalid configuration;
* module running;
* module completed;
* module completed with warnings;
* module cancellation;
* Review Queue case creation;
* physical operation requiring user approval;
* recovery-required state.

The GUI must never present raw exception text as the only explanation of failure.

---

# 37. Build and Packaging

The application shall be packaged so that the user can run the desktop application without manually installing the project's Python dependencies.

The exact packaging tool is an implementation choice, but the build must produce a reproducible Windows artifact containing:

* application runtime;
* required Python dependencies;
* PySide6 runtime;
* application code;
* required non-model assets;
* model files only when explicitly included in the distribution package.

Models may be distributed separately because of their size.

The build process shall be documented and reproducible from a clean development environment.

---

# 38. Development Versus Packaged Runtime

Development may run the application directly from Python source.

The packaged user version may run as a Windows executable.

Both modes must use the same application architecture.

The source tree must not contain behaviour that exists only because the program is running from source.

Runtime paths shall be resolved through an explicit path/configuration service rather than scattered relative-path assumptions.

---

# 39. Update and Versioning Strategy

The application shall distinguish at least:

```text
application version
module version
model version
schema/database version
```

These are different concepts.

Updating the application must not silently delete project data.

Database schema changes shall be handled by an explicit migration/bootstrap mechanism compatible with DOC - 005 and DOC - 206.

A module/model update does not automatically invalidate its previous results; deliberate full recalculation follows DOC - 014 and DOC - 205.

---

# 40. Database Schema Initialization and Migration

Starting a new project shall create the required SQLite schema.

Opening an existing project shall detect its database schema version before normal operation.

If a migration is required:

```text
open database
    ↓
read schema version
    ↓
validate compatibility
    ↓
perform explicit migration
    ↓
verify migration
    ↓
open normal application state
```

The application shall not silently reinterpret an old database as a new schema without validation.

Migration failures shall be reported clearly and must not leave the user with a misleading message that the project opened successfully.

---

# 41. Backup Before Risky Changes

Operations capable of changing the database schema or performing large-scale destructive or difficult-to-reverse changes should support an explicit backup point.

This may include:

* schema migrations;
* large result cleanup;
* bulk duplicate operations;
* large-scale AutoSort operations;
* recovery operations.

The exact backup/restore mechanism is defined by DOC - 206.

---

# 42. Security and Trust Boundaries

The application is offline-first, but local integrity and safe permissions remain important.

The application shall:

* avoid executing arbitrary content from image directories;
* treat model files as trusted application assets only after validation;
* avoid silently downloading executable components;
* avoid modifying paths outside configured project/collection boundaries;
* validate destinations before filesystem writes;
* avoid treating a filename or directory name as executable configuration logic.

The application should not require administrator privileges for normal operation unless Windows explicitly requires them for a user-selected location.

---

# 43. Path Handling

Filesystem paths shall be handled using platform-aware path APIs.

The implementation must not assume that Windows paths can safely be manipulated with string concatenation alone.

Path handling must account for:

* spaces;
* Unicode names;
* long paths where supported;
* differing case behaviour;
* network paths if explicitly configured;
* removable disks;
* unavailable roots.

The application shall store normalized path information according to the filesystem and database rules defined by the project.

---

# 44. Portable Mode and External Collections

The application package is portable, but the image collection may be on another drive.

A portable project therefore may look like:

```text
E:\AI-Sorter\
    AI-Sorter.exe
    data\project.db
    models\...

D:\ImageCollection\
    TODO\...
    AI\...
    FINAL\...
```

Moving the application package does not imply moving the collection.

Moving the collection or changing its drive/paths is handled through Collection Definition and reconciliation/recovery mechanisms.

---

# 45. Project Startup Sequence

The baseline startup sequence should be approximately:

```text
Start application
    ↓
resolve application paths
    ↓
load basic application configuration
    ↓
initialize logging
    ↓
open/create project context
    ↓
open/check database
    ↓
check schema version
    ↓
load/validate Collection Definition
    ↓
initialize GUI
    ↓
show project state
```

Heavy modules and large models should not be loaded during startup merely to make their functionality available.

Startup should remain practical even when the project contains millions of files.

---

# 46. Shutdown Sequence

The application should shut down in an orderly manner:

```text
request shutdown
    ↓
prevent new work from starting
    ↓
ask/handle active executions according to policy
    ↓
finish or cancel safe operations
    ↓
flush logs
    ↓
close module resources
    ↓
close database connections
    ↓
exit
```

A user must not be encouraged to kill the process as the normal way to stop an operation.

---

# 47. Recovery After Unexpected Termination

After a crash, forced process termination or power loss, the application should:

1. reopen the project safely;
2. detect unfinished executions where possible;
3. report incomplete operations clearly;
4. avoid assuming that an unfinished filesystem action succeeded;
5. use recorded state and reconciliation procedures to determine the actual result;
6. preserve already completed independent work.

DOC - 404 defines the higher-level recovery procedure.

---

# 48. No Hidden Background Work

The application shall not silently start expensive analysis or file movement merely because the GUI was opened.

The user should know when an operation begins and what it is doing.

Background maintenance may exist only when explicitly defined and must remain visible in application state.

This is particularly important because the collection may contain millions of files and AI models may consume substantial system resources.

---

# 49. User Control of Expensive Operations

Operations with substantial CPU, GPU, RAM or storage impact shall expose appropriate controls where relevant, such as:

* worker count;
* batch size;
* GPU enable/disable where supported;
* model selection;
* processing scope;
* cancellation;
* result cleanup confirmation.

The application must prefer predictable resource use over unbounded automatic scaling.

---

# 50. GUI Status Model

The GUI should present clear states for modules and utilities, such as:

```text
IDLE
STARTING
RUNNING
PAUSING
CANCELLING
COMPLETED
COMPLETED WITH WARNINGS
FAILED
CANCELLED
RECOVERY REQUIRED
```

The exact internal execution states are defined by DOC - 007 and DOC - 005.

The GUI may present a simplified representation, but it must not falsely report success when the underlying execution failed or requires recovery.

---

# 51. Human-Centred Diagnostics

The application should prefer messages that answer the user's practical questions:

```text
What happened?
Why?
Did it change my files?
What should I do now?
Where can I see the details?
```

A technical error should therefore be translated into an actionable message whenever the cause is sufficiently known.

Examples:

```text
The configured collection root cannot be accessed.
Check that the drive is connected and that the path still exists.
No files were modified.
```

```text
The requested destination is outside the configured collection.
The operation was blocked for safety.
No files were moved.
```

```text
The file changed while it was being processed.
Its SHA512 no longer matches the state used for this operation.
The operation was cancelled and the file was not overwritten.
```

---

# 52. Localization Readiness

User-facing messages should be kept separate from low-level implementation logic so that localization can be introduced later without rewriting core module code.

The initial implementation may use one primary user language, but the message architecture must not hard-code message text throughout business logic.

Technical logs may use stable technical terminology suitable for diagnostics.

---

# 53. Repository Structure

The source repository should distinguish documentation, application code, tests and build resources.

A possible structure is:

```text
AI-sorter/
├── docs/
├── src/
│   └── ai_sorter/
│       ├── app/
│       ├── config/
│       ├── core/
│       ├── db/
│       ├── gui/
│       ├── modules/
│       ├── services/
│       ├── filesystem/
│       ├── models/
│       └── utilities/
├── tests/
├── build/
├── tools/
├── models/                 # local development/runtime assets when used
├── pyproject.toml
├── README.md
└── ...
```

The exact source tree may evolve, but responsibilities should remain separated.

The runtime layout described earlier and the source repository layout are not required to be identical.

---

# 54. Code Ownership Boundaries

The implementation should follow ownership rules equivalent to the documentation architecture.

Examples:

```text
GUI
    presentation and user interaction

Services
    application workflows

Modules
    module-specific analysis

DB Access Layer
    persistence operations

Filesystem Layer
    safe physical filesystem operations

Model Runtime
    loading and lifecycle of model resources

Logging
    technical logging

Configuration
    configuration loading/validation
```

Cross-layer access should be intentional and limited.

A GUI widget should not calculate SHA512.

A module should not directly manipulate arbitrary GUI widgets.

A model implementation should not directly change the database.

---

# 55. First Implementation Milestone

Before implementing large-scale AI classification, the following foundation shall work end-to-end:

```text
Start application
    ↓
Create/open project
    ↓
Create SQLite database
    ↓
Load/validate Collection Definition
    ↓
Display project status in GUI
    ↓
Run Scanner
    ↓
Create File + FileLocation records
    ↓
Show scan progress
    ↓
Show human-readable warnings/errors
    ↓
Review technical log
```

This milestone is the first acceptance point for the implementation phase.

---

# 56. Second Implementation Milestone

After the foundation is stable:

```text
Module Execution Engine
    ↓
minimal test module
    ↓
independent module execution
    ↓
ModuleExecution records
    ↓
progress/cancellation
    ↓
cleanup utility
    ↓
Review Queue integration
```

Only after this milestone should expensive recognition modules become the primary implementation focus.

---

# 57. Third Implementation Milestone

The first real analysis modules can then be implemented in a controlled order, beginning with lower-risk modules and progressively introducing AI-heavy modules.

The planned sequence should preserve the project's independent-module architecture and should not turn the application into an implicit mandatory pipeline.

---

# 58. Acceptance Criteria

The implementation baseline is considered satisfied when:

* the application targets Windows 10/11 and is primarily developed for Windows 11;
* Python is the primary implementation language;
* the runtime is offline-capable;
* one project uses one SQLite database;
* the application is portable/self-contained;
* project-specific runtime state is grouped in one application location;
* GUI is available from the first functional release;
* PySide6 is used as the baseline GUI framework;
* GUI actions invoke application services rather than a hidden CLI process;
* long-running work does not block the GUI thread;
* modules remain independently executable;
* inter-module persistent communication occurs through the database;
* models are stored outside the database and loaded lazily;
* large models are reused during an execution where practical and released when safe;
* technical errors are logged;
* user-facing errors are human-readable and actionable;
* significant failures report the known safety state of files and project data;
* the project can be built and packaged reproducibly;
* database schema versioning is explicit;
* recovery after interruption does not depend on pretending an unfinished operation succeeded;
* tests cover the foundation before large-scale AI implementation begins.

---

# 59. Relationship with Existing Documentation

DOC - 016 does not replace existing specifications.

It translates them into implementation boundaries:

```text
DOC - 003
    System architecture
        ↓
DOC - 016
    implementation structure

DOC - 005
    database schema
        ↓
DOC - 016
    DB runtime/bootstrap/access

DOC - 007
    execution engine
        ↓
DOC - 016
    application/module runtime integration

DOC - 008
    configuration
        ↓
DOC - 016
    configuration loading and portable storage

DOC - 009
    DB access
        ↓
DOC - 016
    application DB layer

DOC - 010
    module interface
        ↓
DOC - 016
    module runtime contract

DOC - 011
    logging
        ↓
DOC - 016
    diagnostics and execution correlation

DOC - 012
    file identity
        ↓
DOC - 016
    Scanner/database integration

DOC - 013
    Review Queue
        ↓
DOC - 016
    GUI/service integration

DOC - 014
    result lifecycle
        ↓
DOC - 016
    cleanup/reprocessing implementation boundary
```

The individual module specifications remain authoritative for module-specific behaviour.

---

# 60. Non-Goals

DOC - 016 does not define:

* AI model accuracy;
* the exact implementation of every analysis algorithm;
* detailed SQL migrations for every future schema change;
* visual design of the final GUI;
* exact machine-learning frameworks for every module;
* online/cloud services;
* automatic unattended global reprocessing;
* a separate CLI application behind the GUI.

These remain implementation-specific or are defined by other documents.

---

# 61. Core Implementation Principles

The implementation shall follow these principles:

1. **Correctness before visual polish.**
2. **GUI is an interface, not the application core.**
3. **Long-running work never blocks the GUI thread.**
4. **One project uses one SQLite database.**
5. **Application state remains portable and grouped together.**
6. **Models are local assets and are loaded only when needed.**
7. **Modules remain independent.**
8. **Database access is centralized through the DB Access Layer.**
9. **Filesystem operations are controlled and verifiable.**
10. **Human-readable errors are mandatory.**
11. **Technical diagnostics remain available in logs.**
12. **Expensive operations are visible and user-controlled.**
13. **Per-file failures do not unnecessarily destroy successful work.**
14. **Recovery is designed into operations rather than added after failure.**
15. **The implementation follows the documented architecture instead of recreating an undocumented architecture in code.**

---

# 62. End of DOC - 016
