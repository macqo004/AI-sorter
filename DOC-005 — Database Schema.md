# DOC-005 – Database Schema

**Project:** AI Image Collection Management System  
**Document:** DOC-005  
**Version:** 3.0  
**Status:** Design Specification

**Depends on:** DOC-001, DOC-002, DOC-003, DOC-008, DOC-009, DOC-010, DOC-012, DOC-013, DOC-014, DOC-301, DOC-302

---

# 1. Purpose

This document defines the logical database schema of the project.

The database is the shared persistence and communication layer between modules. Modules do not communicate directly with one another; persistent information exchanged between modules is exchanged through the database.

DOC-005 defines the logical entities, relationships, ownership rules and state represented by the database. SQL syntax, indexes, migrations and database-engine-specific optimisations are implementation concerns unless explicitly required by this logical model.

The database is expected to support collections of approximately 5,000,000 files and substantially larger collections without requiring the entire dataset to be held in memory.

---

# 2. Fundamental Identity Model

The project distinguishes between **binary-content identity** and **physical file location**.

```text
SHA512
  = identity of a binary file content

File
  = logical record identified by SHA512

File Location / Instance
  = one physical filesystem occurrence of that content
```

This distinction is required because two or more physical files may contain exactly the same binary content and therefore share the same SHA512 while existing at different paths.

`SHA512` is the logical identity of the binary content and the unique content key of the `File` entity.

A technical `file_id` may exist as an internal surrogate identifier. It must not replace SHA512 as the project's logical file identity.

Filename, extension, path and physical location do not define binary identity.

---

# 3. File and File Location

## 3.1 File

`File` represents one unique binary content identity.

Core logical fields:

| Field | Meaning |
|---|---|
| `sha512` | Logical identity of binary content; unique |
| `file_id` | Optional technical surrogate identifier |
| `first_seen` | First time this content identity entered the database |
| `last_seen` | Latest successful observation of at least one physical instance |
| `status` | Lifecycle state of the logical content record |

Typical logical states:

```text
ACTIVE
ARCHIVED
```

A `File` record is not tied to one physical path.

## 3.2 File Location / Instance

`FileLocation` represents one physical occurrence of a `File` on a filesystem.

Core logical fields:

| Field | Meaning |
|---|---|
| `location_id` | Unique technical identifier of this physical occurrence |
| `file_id` / `sha512` reference | Associated binary-content identity |
| `current_path` | Current full physical path |
| `filename` | Current filename |
| `extension` | Current extension |
| `size_bytes` | Current filesystem size |
| `modified_time` | Current filesystem modification timestamp |
| `first_seen` | First observation of this physical occurrence |
| `last_seen` | Latest successful filesystem verification |
| `state` | Current physical-instance state |
| `root_id` | Configured Collection Definition root, where applicable |

Typical location states:

```text
ACTIVE
MISSING
ARCHIVED
```

A physical move or rename changes the location record, not the `File` identity.

---

# 4. Why the Two-Level Model Is Required

Consider:

```text
D:\Anime\Genshin\Furina\0001\image.jpg
E:\Backup\image.jpg
```

If both files have:

```text
SHA512 = ABC...
```

they represent the same binary content but two physical occurrences.

The database therefore stores:

```text
File
  SHA512 = ABC...

FileLocation #1
  path = D:\Anime\...

FileLocation #2
  path = E:\Backup\...
```

This allows Duplicate Management to identify multiple physical copies without violating the rule that SHA512 identifies the content.

Duplicate Management decides how such occurrences are related and which one may be treated as the preferred/master occurrence. It does not redefine file identity.

---

# 5. File Identity Changes

A physical move or rename does not change SHA512.

A binary-content modification that produces a different SHA512 represents a different content identity.

Example:

```text
Before:
SHA512 = AAA

file contents modified

After:
SHA512 = BBB
```

The database must not silently change the identity of the existing `File(AAA)` record into `BBB`.

The old content may become `ARCHIVED` when no active physical instances remain. The new content receives its own `File(BBB)` identity.

A SHA512 calculation failure must never result in a fabricated placeholder identity.

The project does not design an ordinary workflow around SHA512 collisions. A collision is an integrity event and must be handled explicitly.

---

# 6. Scanner-Owned File Registration

Scanner is responsible for discovering physical files and establishing/updating their database representation.

A typical flow is:

```text
filesystem
    ↓
Scanner
    ↓
SHA512 calculation
    ↓
File identity lookup/create
    ↓
FileLocation lookup/create/update
```

A newly discovered physical file must exist in the database before other modules can reliably process it.

Scanner processing is incremental. Successful records shall not be rolled back merely because an unrelated file fails later in the same execution.

---

# 7. Analysis Result Model

Analysis modules write their own results into the database.

The database must support independent result sets rather than requiring one global pipeline state.

Examples include:

```text
BW / Color
Screenshot
Reaction
IRL
Cosplay
```

A result belongs to:

```text
File
  + producing Module
  + result category / feature
```

The logical schema may use dedicated tables or a shared result structure where appropriate; the mandatory semantic rule is that each module owns the results it produces.

A module must not overwrite another module's result set merely because both analyse the same file.

---

# 8. Analysis Result State

The project does not require a separate database row merely to represent `NOT_PROCESSED` for every file/module combination.

In the normal model:

```text
result exists
    = processed result is available

result absent
    = module has no current result for that file
```

A module may define additional explicit states where needed, for example:

```text
FAILED
SKIPPED
NOT_APPLICABLE
```

These states belong to the module's own result specification and must not be confused with the lifecycle of the `File` itself.

---

# 9. Module Result Lifecycle and Cleanup

The project follows DOC-014.

The database does **not** require each stored analysis result to contain a model-generation identifier merely to support reprocessing.

When a module changes substantially and the user wants to recalculate its results:

```text
user selects module
        ↓
Module Result Cleanup
        ↓
results belonging to that module are cleared
        ↓
module runs again
```

Cleanup is scoped to the selected module/result category and must not remove unrelated results, file identities or physical file records.

Changing a model, algorithm or module implementation does not automatically launch a global reprocessing operation.

The database may retain module execution history, but ordinary result storage does not need multiple generations of the same result solely for version tracking.

---

# 10. Classification Result Model

Semantic classification results are distinct from low-level analysis observations.

Examples:

```text
PRIMARY TREE CLASS
UNIVERSE
CHARACTER
SPECIES
THEME
```

`SET` is a special case: Set is both classification/organisation information and a physical directory concept. The exact Set relationship is defined by DOC-109.

A classification record shall distinguish its source:

```text
AUTOMATIC
USER
IMPORTED
```

It should also identify the producing module where applicable.

Core logical fields may include:

```text
classification_id
file_id
classification_type
value / target_id
confidence
source
module_id
created_at
is_current
```

Historical results may be retained where useful.

---

# 11. Manual Decisions and Protected Results

User decisions are first-class project information.

A user may manually correct a proposed classification or placement through Review Queue.

The database must preserve enough information to distinguish:

```text
automatic observation
user decision
current accepted result
```

A protected manual decision has priority over later automatic results for the same classification or placement context until the user explicitly changes or removes that decision.

Cleaning an unrelated module's result set must not delete a protected manual decision.

The detailed workflow is defined by DOC-013.

---

# 12. Review Queue

Review Queue is defined by DOC-013 and is the common user-decision mechanism.

A persistent review record may reference:

```text
review_id
file_id
SHA512
location_id, where relevant
module_id
execution_id
reason
suggested_result
suggested_destination
confidence
status
created_at
resolved_at
```

There is no separate Migration Queue requirement.

A move or placement correction is one possible outcome of a Review Queue decision.

A review record must remain tied to the relevant file identity and must be revalidated before applying a physical operation.

---

# 13. User Decision Model

The persistent Review Queue case supports the logical user decisions defined by DOC-013:

```text
ACCEPT
REJECT
MODIFY
DEFER
```

The database must preserve the resulting decision and, where applicable, the final user-selected destination or classification.

The physical filesystem operation is performed by the authorised execution mechanism, not by the database itself.

---

# 14. Module Entity

`Module` identifies an executable project component.

Core logical fields:

```text
module_id
name
version
enabled
description
```

The stored module version is useful for execution history, diagnostics and identifying the installed implementation. It is **not** a requirement to version every result row by model generation.

---

# 15. Module Execution

`ModuleExecution` records one invocation of a module.

Core logical fields:

```text
execution_id
module_id
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
CANCELLED
FAILED
```

Module executions are independent.

An IRL execution does not require a Screenshot execution in the same run, and vice versa.

Execution history does not define module dependency order.

---

# 16. File Events and History

Important historical actions should be represented by immutable events or equivalent history records.

Examples:

```text
SCANNED
DISCOVERED_LOCATION
LOCATION_CHANGED
RENAMED
MOVED
ANALYSIS_COMPLETED
CLASSIFICATION_CREATED
USER_CORRECTED
MOVED_TO_AI
MOVED_TO_FINAL
ARCHIVED
DELETED
```

Core logical fields may include:

```text
event_id
file_id
location_id, where relevant
module_id, where relevant
event_type
timestamp
description
related_execution_id
```

Events describe what happened; they should not be rewritten to make a historical operation appear to be something else.

---

# 17. Duplicate Groups and Master Selection

Duplicate Management is defined by DOC-204.

The schema must allow the database to represent multiple physical `FileLocation` records associated with one `File`/SHA512.

A duplicate-management layer may store, for example:

```text
duplicate_group_id
file_id / sha512
preferred_location_id
status
source
```

The database must not require creation of separate `File` identities for binary-identical copies.

The designation of a `master` or preferred occurrence is a management decision and does not change the SHA512 identity.

---

# 18. Set Representation

Set Detection is defined by DOC-109.

A Set is primarily a physical directory grouping visually similar images.

Where Set metadata is stored in the database, it may include:

```text
set_id
parent collection/location context
physical path, where applicable
status
```

A file may belong to a Set through its active `FileLocation` or through an explicit Set-membership relation, depending on implementation.

The database must not force Set identity to replace file identity.

---

# 19. Collection Definition Storage

Collection Definition is defined by DOC-301 and DOC-302.

The database may store the currently active definition or its relevant persisted representation.

At minimum, persisted configuration may include:

```text
root_id
path
role
enabled
access_policy
recursive / traversal settings
collection tree identity
node identity
parent relationship
classification boundary information
```

The physical names `TODO`, `AI`, `Anime`, `Monster Girls`, `Western Animation`, `Themes` are not schema-level constants.

The role of a root is configuration, not a hard-coded path name.

---

# 20. Collection Root and Access Policy

A configured root may have one of the roles defined by DOC-302, for example:

```text
PRIMARY
THEME_FALLBACK
TODO
AI
IMPORT_SOURCE
```

A root also carries its configured access policy, for example:

```text
PROTECTED
READ_ONLY
MODIFY
PLAYGROUND
```

The database stores the configured value; the consuming module remains responsible for enforcing the permitted operations.

---

# 21. Tags

Tags are semantic metadata and are distinct from the physical folder tree.

The usual relationship is:

```text
File
  ↓
FileTag
  ↓
Tag
```

A Theme used as a physical fallback destination is not automatically the same thing as a Theme tag.

A file may retain theme metadata after it has been moved from the Theme fallback into a primary collection tree.

---

# 22. Current State Versus History

The database contains both current-state information and historical information.

Current-state records are used for normal module operation.

Historical records preserve important past actions, decisions and previous results where required.

The project does not require pure event sourcing.

A practical combination of current state plus selected immutable history is preferred.

---

# 23. Ownership Rules

Each module owns the data it explicitly produces.

A module may:

* read required shared information;
* create its own analysis or classification results;
* supersede or clear its own results according to its specification;
* create appropriate execution and file events.

A module must not silently:

* overwrite another module's result;
* delete another module's protected user decision;
* reinterpret another module's table as its own state;
* establish direct runtime communication with another module.

Shared infrastructure entities are maintained by their responsible components.

---

# 24. Transaction and Failure Model

The logical database model must support partial, incremental progress.

Successful processing of files A, B and C must not be discarded solely because processing file D later fails.

Transaction boundaries may therefore be defined per file, per batch or according to another safe module-specific unit.

The exact transaction strategy is an implementation concern, but a module must not require a single global transaction covering millions of files merely to preserve logical consistency.

---

# 25. Integrity Rules

The implementation must enforce or validate where practical:

* SHA512 uniqueness in `File`;
* valid references between `File` and `FileLocation`;
* valid module references;
* valid execution references;
* valid Collection Definition/root references;
* valid Review Queue references;
* valid lifecycle transitions where practical;
* absence of fabricated SHA512 values;
* no orphaned active `FileLocation` without a valid `File` identity.

Multiple `FileLocation` rows may legitimately reference one `File`/SHA512.

Two different `File` identities must not normally use the same SHA512.

---

# 26. Rebuild and Recovery Considerations

Database Maintenance is defined by DOC-202.

The schema must distinguish data that can be rebuilt from the filesystem from data that exists only as project history or user decision.

Typically rebuildable information includes:

```text
FileLocation state
current file metadata
current SHA512 observations
```

Potentially non-rebuildable or historically important information includes:

```text
user decisions
review history
module execution history
historical classification results
manual correction history
```

A rebuild procedure must therefore not assume that every database row is equivalent to a fresh filesystem scan.

---

# 27. Scalability

The schema targets at least:

```text
5,000,000 logical File identities
```

and may need to support substantially more physical `FileLocation` records because duplicates can create multiple physical occurrences of the same content.

The design should avoid:

* one table per file;
* one table per execution;
* one column for every future analysis feature;
* storing image binaries in the metadata database without justification;
* operations requiring the entire collection in memory;
* unnecessary duplication of large textual paths or analysis payloads.

Indexes and database-engine-specific optimisations are implementation concerns.

---

# 28. Extensibility

New modules should normally be able to add their own result structures without redesigning the entire database.

A new module should not be required to modify core `File` identity merely to introduce a new analysis feature.

A dedicated table or relational entity is appropriate when a feature has strong relational semantics or needs efficient querying.

A generic key/value structure is not mandatory for all future features.

Schema migrations are acceptable when they provide a clear architectural benefit.

---

# 29. Offline Operation

The database is intended for local/offline project operation.

Normal database access and module execution must not require an Internet connection.

No project database table is intended to be an online service or cloud dependency.

---

# 30. Relationship with Other Documents

```text
DOC-001  Project Specification
DOC-002  Database Architecture
DOC-003  System Architecture
DOC-005  Database Schema
DOC-008  Configuration Manager
DOC-009  Database Access Layer
DOC-010  Module Interface Specification
DOC-011  Logging Standard
DOC-012  File Identity Model
DOC-013  Review Queue
DOC-014  Module Result Lifecycle and Cleanup
DOC-109  Set Detection and Grouping
DOC-201  AutoSort
DOC-202  Database Maintenance
DOC-204  Duplicate Management
DOC-301  Collection Definition Wizard
DOC-302  Collection Definition Format
```

DOC-005 defines database structure.

DOC-012 defines file identity semantics.

DOC-013 defines Review Queue semantics.

DOC-014 defines module-result lifecycle and cleanup semantics.

DOC-302 defines Collection Definition field meaning.

DOC-005 should not silently redefine those contracts; when a conflict is discovered, the authoritative document must be updated deliberately.

---

# 31. Acceptance Criteria

The schema is architecturally acceptable when:

* SHA512 uniquely identifies binary content;
* `File` is separated from physical `FileLocation` so duplicate physical copies can coexist under one content identity;
* `file_id` is treated only as a technical identifier;
* moves and renames preserve SHA512 identity;
* a binary-content change produces a new content identity;
* Scanner can register new physical instances incrementally;
* analysis results are owned by their producing modules;
* modules can be executed independently and repeatedly;
* module-result cleanup can remove one module's results without deleting file identity or unrelated results;
* automatic and manual classification results are distinguishable;
* protected manual decisions survive unrelated result cleanup;
* Review Queue is the common user-decision mechanism;
* Collection Definition can be represented without hard-coded physical directory names;
* duplicate management can operate on multiple physical occurrences of identical SHA512 content;
* Set information does not replace file identity;
* important history can be preserved;
* partial module execution can be persisted safely;
* the schema can support approximately 5 million logical files and potentially more physical locations;
* modules can exchange persistent state through the shared database without direct module-to-module communication.

---

# End of DOC-005
