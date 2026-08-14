# DOC-005

# Database Schema

**Project:** AI Image Collection Management System

**Document:** DOC-005

**Version:** 2.0

**Status:** Draft

**Depends on:**

DOC-001
DOC-002
DOC-003
DOC-010
DOC-012
DOC-013

---

# 1. Purpose

This document defines the logical database schema of the project.

It describes the persistent entities and relationships used by the framework to identify files, store filesystem state, record analysis results, preserve history and represent user decisions.

The database is the shared persistence and communication layer between modules.

This document defines the logical data model. It does not define SQL implementation details, indexes, migrations or SQLite-specific implementation choices unless required by the logical model.

---

# 2. Design Principles

The schema is designed around the lifecycle of a file known to the system.

The database must be able to answer questions such as:

* What file is this?
* What is its current SHA512?
* Where is it currently stored?
* What collection/root does its current path belong to?
* Which analyses have been performed?
* Which analysis result is currently valid?
* What did the user decide?
* Has the user manually corrected a classification?
* What operations have happened to the file?
* Which module produced a result?
* When was a module execution performed?

The schema must keep these responsibilities separate.

---

# 3. File Identity

File identity is defined by **DOC-012 – File Identity Model**.

The database therefore uses:

```text
file_id
SHA512
```

as the fundamental identity information.

`file_id` is the permanent internal database identifier.

SHA512 identifies the binary content represented by the record.

Filename, extension and path do not define file identity.

A rename or move updates filesystem information without creating a new file record.

If the binary content changes and produces a different SHA512, the changed content is treated as a new file according to DOC-012.

The previous record may become `ARCHIVED`.

DOC-005 does not redefine these identity rules.

---

# 4. Core Entities

The current logical model consists of the following entities:

```text
File
  │
  ├── Analysis Result
  │
  ├── Classification Result
  │
  ├── File Event
  │
  └── Tag Assignment

Module
  │
  └── Module Execution

Collection
  │
  └── Collection Root

Review Item
```

Not every entity is required to exist for every file.

Additional entities may be introduced when a new architectural requirement requires persistent data that does not belong to an existing entity.

---

# 5. Entity: File

## 5.1 Purpose

The File entity represents one file known to the framework.

It combines permanent identity information defined by DOC-012 with the current physical state required by the database.

## 5.2 Core fields

### file_id

Type:

```text
INTEGER
```

Properties:

* Primary Key
* Unique
* Never reused
* Immutable

### sha512

Type:

```text
TEXT
```

Expected representation:

```text
128 hexadecimal characters
```

Stores the SHA512 of the current binary content represented by the record.

The database must never invent a placeholder SHA512 when calculation fails.

### current_path

Type:

```text
TEXT
```

Stores the current physical path known to the framework.

### filename

Type:

```text
TEXT
```

Stores the current filename.

### extension

Type:

```text
TEXT
```

Stores the file extension where available.

Supported image extensions are defined by the Scanner specification rather than by the database schema.

### size_bytes

Type:

```text
INTEGER
```

Current file size.

### modified_time

Type:

```text
DATETIME
```

Filesystem modification timestamp used by the Scanner when deciding whether a file requires revalidation.

### width

Type:

```text
INTEGER
```

Image width in pixels when available.

### height

Type:

```text
INTEGER
```

Image height in pixels when available.

### first_seen

Type:

```text
DATETIME
```

Timestamp when the file record was first created.

### last_seen

Type:

```text
DATETIME
```

Timestamp of the latest successful filesystem verification.

### status

Logical lifecycle state.

Initial states include:

```text
ACTIVE
MISSING
ARCHIVED
DELETED
```

The exact lifecycle rules are governed by DOC-012 and database-maintenance specifications.

---

# 6. Entity: Analysis Result

## 6.1 Purpose

Analysis Result stores observations produced by analysis modules.

Examples include:

* monochrome / colour analysis;
* screenshot detection;
* reaction image detection;
* IRL detection;
* cosplay detection;
* image dimensions or derived visual properties;
* other objective or model-generated analysis results defined by analysis modules.

Analysis results must not be confused with user decisions.

## 6.2 Ownership

A module owns the results it produces.

A module must not silently overwrite results belonging to another module.

A new execution may supersede an earlier result produced by the same analysis component.

## 6.3 Core fields

### analysis_id

Primary key.

### file_id

Foreign key to `File.file_id`.

### module_id

Foreign key to `Module.module_id`.

### feature

Identifies what was analysed.

Examples:

```text
BW
SCREENSHOT
IRL
COSPLAY
REACTION
```

### value

Stores the resulting value in a representation appropriate to the feature.

The logical model does not require every feature to use the same semantic type. The implementation may use a normalized representation suitable for the selected database technology.

### confidence

Optional numeric confidence in the range:

```text
0.0 – 1.0
```

Confidence is applicable only where the producing module can meaningfully provide it.

### module_version

Version of the module that produced the result.

### created_at

Timestamp when the result was produced.

### superseded_at

Optional timestamp indicating that the result is no longer the current result for the same analysis context.

---

# 7. Entity: Classification Result

## 7.1 Purpose

Classification Result stores semantic interpretations of a file.

Examples include:

* universe;
* character;
* theme;
* set/group classification;
* other semantic classifications introduced by the project.

Classification is distinct from objective analysis.

## 7.2 Source

Each classification result must record its source.

Possible sources include:

```text
AI
USER
IMPORTED
```

The exact values may be extended when required.

## 7.3 Manual correction

A user correction must never be silently overwritten by a later automatic result.

The database must preserve enough information to distinguish at least:

```text
AUTOMATIC RESULT
MANUAL RESULT
```

A manual result has higher priority than an automatic result for the same classification context unless the user explicitly changes or removes that decision.

The detailed manual-override rules belong to DOC-013 and relevant analysis specifications.

## 7.4 Core fields

### classification_id

Primary key.

### file_id

Foreign key to `File.file_id`.

### classification_type

Examples:

```text
UNIVERSE
CHARACTER
THEME
SET
```

### value

The classification value.

### confidence

Optional confidence assigned by the producing module.

For user decisions, confidence may be null or may represent user-confirmed status rather than model probability.

### source

Identifies whether the result came from AI, the user or another accepted source.

### module_id

Optional for user-created results; identifies the producing module for automatic results.

### created_at

Timestamp when the result was created.

### is_current

Indicates whether the result is currently the active result for the classification context.

Historical results remain available.

---

# 8. Entity: Module

## 8.1 Purpose

Module identifies an executable project component.

Examples include:

```text
Scanner
Color Analysis
Screenshot Analysis
IRL Analysis
Universe Analysis
Character Analysis
Theme Analysis
File Renamer
Database Maintenance
```

## 8.2 Core fields

### module_id

Primary key.

### name

Unique module name.

### version

Current installed module version.

### enabled

Indicates whether the module is currently enabled according to project configuration.

### description

Optional human-readable description.

Module execution is user-initiated unless a future specification explicitly introduces another execution mechanism.

---

# 9. Entity: Module Execution

## 9.1 Purpose

Module Execution records one execution instance of a module.

It exists separately from Module because a module may execute many times.

## 9.2 Core fields

### execution_id

Primary key.

### module_id

Foreign key to `Module.module_id`.

### started_at

Execution start timestamp.

### finished_at

Execution completion timestamp, if completed.

### status

Examples:

```text
RUNNING
COMPLETED
CANCELLED
FAILED
```

### files_processed

Optional execution statistic.

### files_skipped

Optional execution statistic.

### files_failed

Optional execution statistic.

### notes

Optional execution information.

Execution history must remain independent from file history.

---

# 10. Entity: File Event

## 10.1 Purpose

File Event records important actions affecting a file.

Events provide historical traceability without requiring current-state fields to contain the entire history.

## 10.2 Examples

```text
SCANNED
MOVED
RENAMED
ANALYSIS_COMPLETED
CLASSIFICATION_CREATED
USER_CORRECTED
RETURNED_TO_TODO
MOVED_TO_AI
MOVED_TO_FINAL
DELETED
ARCHIVED
```

The final set of event types is not fixed by this document.

## 10.3 Core fields

### event_id

Primary key.

### file_id

Foreign key to `File.file_id`.

### module_id

Optional foreign key identifying the module responsible for the event.

Null may represent a direct user action.

### event_type

Identifies the event.

### timestamp

Event timestamp.

### description

Optional human-readable information.

### related_execution_id

Optional reference to the module execution that caused the event.

Events are historical records and should not be rewritten to represent a different past event.

---

# 11. Entity: Tag

Tags provide additional semantic information that is independent of the physical folder tree.

Examples include:

```text
Christmas
Halloween
School Uniform
Bikini
Beach
Night
Rain
```

An image may have multiple tags.

Tag membership should therefore use a many-to-many relationship:

```text
File
  ↓
FileTag
  ↓
Tag
```

Tags do not define the primary collection structure.

In particular, `Themes` in the user's final collection is not automatically equivalent to the Tag system.

---

# 12. Entity: Collection

Collection configuration is defined by DOC-301 and DOC-302.

The database may store the collection definition and its configured roots, but DOC-005 does not hard-code physical directory names such as `TODO`, `AI`, `Anime` or `Themes`.

A collection may contain roots with different roles and access policies.

The database must therefore be able to associate a known path with its configured collection/root context where required.

---

# 13. Entity: Collection Root

A Collection Root represents a configured filesystem root belonging to a Collection.

The logical model may contain information such as:

```text
root_id
collection_id
path
role
access_policy
enabled
recursive
```

Possible roles are configuration concepts and are not hard-coded directory names.

Examples include:

```text
SOURCE
TRANSITION
FINAL
```

The exact format is defined by DOC-302.

---

# 14. Entity: Review Item

Review Queue is defined by DOC-013.

The database may store Review Queue records when required by the implementation.

A Review Item identifies a case that requires a user decision.

It may reference:

```text
file_id
module_id
classification context
reason
suggested result
confidence
created_at
status
```

Review Queue does not constitute a second independent classification system.

There is no separate Migration Queue requirement in the current architecture.

A migration is a possible result of a review decision.

---

# 15. Relationships

The principal relationships are:

```text
Collection
   │
   └── Collection Root

File
   ├── Analysis Result
   ├── Classification Result
   ├── File Event
   ├── File Tag
   └── Review Item

Module
   ├── Module Execution
   ├── Analysis Result
   └── File Event
```

The schema must avoid unnecessary direct dependencies between unrelated analysis modules.

For example, Character Analysis should not require a database-level foreign key to Universe Analysis merely because character classification may use universe information.

Such dependencies belong to module specifications and execution logic.

---

# 16. Current State vs History

The database contains both current-state information and historical information.

Current-state fields provide efficient access to the state needed by normal modules.

Historical entities such as File Event and superseded analysis/classification results preserve previous states and decisions.

The project does not require pure event sourcing.

The database may use ordinary current-state records together with historical records where this provides a simpler and more practical design.

This avoids forcing every database operation to be reconstructed from an event stream.

---

# 17. Manual User Decisions

User decisions are first-class information.

When the user manually corrects a classification or moves a file as part of a correction workflow, the system should preserve:

* the previous automatic result;
* the user decision;
* the resulting current classification where applicable;
* the relevant file event.

A subsequent automatic module execution must not silently replace a protected manual decision.

The precise locking and reprocessing rules are defined by DOC-013 and future analysis/reprocessing specifications.

---

# 18. File Movement and Renaming

Moving a file does not create a new File identity.

Renaming a file does not create a new File identity.

The current path and filename are updated.

The operation should generate an appropriate File Event.

If the file's binary content changes, the SHA512 changes and the rules from DOC-012 apply.

Modules must not infer file identity from the path alone.

---

# 19. Database Ownership Rules

Each module owns the data it is explicitly responsible for producing.

A module may:

* read information required by its operation;
* create its own analysis results;
* supersede its own previous results according to its specification;
* create appropriate events;
* update filesystem state when explicitly authorized by its access policy and module specification.

A module must not silently overwrite another module's analysis results or user decisions.

Shared infrastructure entities such as Module and Collection configuration are maintained by the components responsible for those entities.

---

# 20. Failure Handling

Database operations must support failure isolation.

A failure while processing one file must not require rollback of successfully persisted information about unrelated files unless the operation explicitly requires transaction-level atomicity.

For example, if a scanner successfully identifies files A, B and C and fails while reading D, the successful records for A, B and C must not be lost merely because D failed.

The detailed transactional behaviour of individual modules is defined by their specifications.

---

# 21. Scalability

The initial target is approximately:

```text
5,000,000 files
```

The architecture should remain viable for substantially larger collections, potentially tens of millions of records.

The schema should therefore avoid:

* unnecessary duplication;
* one table per analysis module;
* one column per newly invented feature;
* storing large binary image data inside the primary metadata database unless explicitly justified;
* structures that require loading the entire collection into memory for ordinary operations.

Performance-critical indexes and SQLite-specific optimizations belong to the implementation/database-engineering documentation rather than this logical schema specification.

---

# 22. Extensibility

New analysis modules should normally be able to introduce new result types without redesigning the entire database.

However, extensibility must not be used as a reason to force every possible future concept into a generic key/value structure.

If a new feature requires strong relational semantics, large-scale querying or substantial new state, a dedicated entity or schema extension may be preferable.

Database migrations are therefore acceptable when they provide a meaningful architectural benefit.

The project should avoid both extremes:

```text
EVERYTHING = fixed columns
```

and:

```text
EVERYTHING = generic text/value records
```

The schema should use the simplest structure that remains maintainable and scalable.

---

# 23. Separation from Module Specifications

DOC-005 defines what persistent information exists.

It does not define:

* how Scanner discovers files;
* how an analysis module calculates its result;
* how a renamer chooses a new filename;
* how AutoSort selects a destination;
* how a user operates the GUI;
* how a specific database engine implements indexes or transactions.

Those responsibilities belong to the appropriate documents.

---

# 24. Summary

The database is the shared persistent knowledge layer of the framework.

Its fundamental responsibilities are:

```text
IDENTITY
    ↓
CURRENT FILE STATE
    ↓
ANALYSIS
    ↓
CLASSIFICATION
    ↓
USER DECISIONS
    ↓
HISTORY
    ↓
MODULE / COLLECTION OPERATIONS
```

The schema must remain understandable, maintainable and practical at the scale of millions of files.

The database records what the system knows and what happened. It does not determine the meaning of a directory name, perform image analysis or replace the specifications of individual modules.

---

# End of DOC-005
