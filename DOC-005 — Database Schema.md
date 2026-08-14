# DOC-005
# Database Schema

**Project:** AI Image Collection Management System  
**Document:** DOC-005  
**Version:** 2.1  
**Status:** Draft

**Depends on:** DOC-001, DOC-002, DOC-003, DOC-010, DOC-012, DOC-013

---

# 1. Purpose

This document defines the logical database schema of the project.

The database is the shared persistence and communication layer between modules. Modules do not communicate directly with one another; persistent information exchanged between modules is exchanged through the database.

This document defines the logical data model. SQL implementation details, indexes, migrations and database-engine-specific optimizations are implementation concerns unless explicitly required by the logical model.

---

# 2. File Identity

File identity is defined by **DOC-012 – File Identity Model**.

The primary logical identifier of a binary file is its **SHA512**.

SHA512 is the binary-content key of the file record and is expected to be unique.

A technical `file_id` may also exist as an internal database identifier for relationships and implementation purposes. It does not replace SHA512 as the logical identity of the file.

```text
SHA512
    ↓
logical binary-file identity

file_id
    ↓
internal database identifier
```

Filename, extension and path do not define identity.

Renaming or moving a file does not change its SHA512 identity.

If binary content changes and a different SHA512 is produced, the database must represent the new binary object as a new identity. The previous SHA512 record may become `ARCHIVED` according to DOC-012 and Database Maintenance rules.

The project does not design a normal workflow around SHA512 collisions. A collision is an integrity problem, not an ordinary lifecycle event.

The system must never invent a placeholder SHA512 when calculation fails.

---

# 3. Core Entities

```text
File
  ├── Analysis Result
  ├── Classification Result
  ├── File Event
  ├── Tag Assignment
  └── Review Item

Module
  └── Module Execution

Collection
  └── Collection Root
```

Not every entity is required for every file.

---

# 4. File

The File entity represents one binary file known to the framework.

Core logical fields:

| Field | Meaning |
|---|---|
| `sha512` | Logical identity of the binary content; unique |
| `file_id` | Internal technical identifier |
| `current_path` | Current physical path |
| `filename` | Current filename |
| `extension` | Current extension |
| `size_bytes` | Current file size |
| `modified_time` | Filesystem modification timestamp |
| `width` | Image width where available |
| `height` | Image height where available |
| `first_seen` | Record creation timestamp |
| `last_seen` | Latest successful filesystem verification |
| `status` | Current lifecycle state |

Typical lifecycle states are:

```text
ACTIVE
MISSING
ARCHIVED
DELETED
```

`file_id` may be implemented as a database primary key for technical convenience, but this does not alter the SHA512 identity model.

---

# 5. Analysis Result

Stores observations produced by analysis modules.

Examples:

```text
BW
SCREENSHOT
IRL
COSPLAY
REACTION
```

An analysis result belongs to a file and to the module that produced it.

Core fields:

```text
analysis_id
file_id
module_id
feature
value
confidence
module_version
created_at
superseded_at
```

A module owns the results it produces and must not silently overwrite another module's results.

---

# 6. Classification Result

Stores semantic interpretations such as:

```text
UNIVERSE
CHARACTER
THEME
SET
```

Each result records its source, for example:

```text
AI
USER
IMPORTED
```

Automatic and manual results must be distinguishable.

A manual user decision has priority over an automatic result for the same classification context unless the user explicitly changes or removes that decision.

Core fields include:

```text
classification_id
file_id
classification_type
value
confidence
source
module_id
created_at
is_current
```

Historical classification results may be retained.

---

# 7. Module

Identifies an executable project component.

Core fields:

```text
module_id
name
version
enabled
description
```

Module execution is user-initiated unless a future specification explicitly introduces another mechanism.

---

# 8. Module Execution

Records one execution instance of a module.

Core fields:

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

Typical states:

```text
STARTING
RUNNING
COMPLETED
CANCELLED
FAILED
```

Execution history is independent from file identity and file history.

---

# 9. File Event

Records important historical actions affecting a file.

Examples:

```text
SCANNED
MOVED
RENAMED
ANALYSIS_COMPLETED
CLASSIFICATION_CREATED
USER_CORRECTED
MOVED_TO_AI
MOVED_TO_FINAL
DELETED
ARCHIVED
```

Core fields:

```text
event_id
file_id
module_id
event_type
timestamp
description
related_execution_id
```

Events are historical records and should not be rewritten to represent another past event.

---

# 10. Tags

Tags provide semantic information independent of the physical folder tree.

Tag membership is many-to-many:

```text
File → FileTag → Tag
```

Tags do not define the primary collection structure. A user's `Themes` final tree is not automatically equivalent to the Tag system.

---

# 11. Collection and Collection Root

Collection configuration is defined by DOC-301 and DOC-302.

The database may store collection definitions and configured roots, including:

```text
root_id
collection_id
path
role
access_policy
enabled
recursive
```

Roles are configuration concepts, not hard-coded directory names. Examples include `SOURCE`, `TRANSITION` and `FINAL`.

The database must not hard-code physical names such as `TODO`, `AI`, `Anime` or `Themes`.

---

# 12. Review Item

Review Queue is defined by DOC-013.

A Review Item may reference:

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

Review Queue is the common user-decision mechanism.

There is no separate Migration Queue requirement in the current architecture. Migration is one possible result of a Review Queue decision.

---

# 13. Relationships

```text
Collection
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

The schema should avoid unnecessary direct database dependencies between analysis modules. Logical dependencies are satisfied through documented database state.

For example, Character Analysis does not require a database-level foreign key to Universe Analysis merely because it may use universe information.

---

# 14. Current State and History

The database contains both current-state information and historical information.

Current-state fields support efficient normal operations. Historical entities and superseded results preserve previous states and decisions.

The project does not require pure event sourcing. Ordinary current-state records combined with appropriate history are preferred where they provide a simpler and more practical design.

---

# 15. Manual User Decisions

User decisions are first-class information.

When a user manually corrects a classification or performs a correction workflow, the system should preserve:

* the previous automatic result;
* the user decision;
* the resulting current classification where applicable;
* the relevant file event.

A subsequent automatic execution must not silently replace a protected manual decision.

Detailed override and reprocessing rules belong to DOC-013 and relevant analysis/reprocessing specifications.

---

# 16. File Movement, Renaming and Content Change

Moving or renaming a file does not change its SHA512 identity.

The current path and filename are updated and an appropriate File Event should be generated.

If binary content changes, the SHA512 changes. The database must then represent the new binary object rather than silently changing the identity of the previous SHA512 record.

Modules must not infer identity from path or filename alone.

---

# 17. Database Ownership Rules

Each module owns the data it is explicitly responsible for producing.

A module may read required information, create its own results, supersede its own results according to its specification and create appropriate events.

A module must not silently overwrite another module's results or user decisions.

Shared infrastructure entities such as Module and Collection configuration are maintained by their responsible components.

---

# 18. Failure Handling

A failure while processing one file must not unnecessarily roll back successfully persisted information about unrelated files.

For example, successful records for A, B and C must not be discarded merely because processing D failed.

Exact transaction boundaries are defined by individual module specifications.

---

# 19. Scalability

The initial target is approximately:

```text
5,000,000 files
```

The model should remain viable for substantially larger collections.

It should avoid unnecessary duplication, one table per analysis module, one column for every possible future feature, storing image binaries in the metadata database without justification, and operations requiring the entire collection in memory.

Performance-critical indexes and database-engine-specific optimizations belong to implementation documentation.

---

# 20. Extensibility

New analysis modules should normally be able to introduce new result types without redesigning the entire database.

However, not every future feature should be forced into a generic key/value model. Features requiring strong relational semantics may justify dedicated entities or schema extensions.

Database migrations are acceptable when they provide a meaningful architectural benefit.

---

# 21. Integrity Rules

The implementation must enforce or validate where practical:

* SHA512 uniqueness;
* valid foreign-key relationships;
* valid module references;
* valid collection/root references;
* valid review-item references;
* valid lifecycle transitions where practical;
* absence of fabricated SHA512 values.

Two active File records must not normally represent the same SHA512.

---

# 22. Security and Privacy

The database may contain local filesystem paths and information about the user's collection.

It is intended to operate locally and offline.

Normal operation must not require Internet connectivity.

Image binaries do not need to be stored in the metadata database merely to support collection management.

---

# 23. Relationship with Other Documents

```text
DOC-001  Overall project specification
DOC-002  Database and storage architecture
DOC-003  System architecture
DOC-005  Logical database schema
DOC-008  Configuration management
DOC-010  Module interface
DOC-012  File identity model
DOC-013  Review Queue
```

DOC-005 must not redefine rules owned by DOC-012, DOC-013 or DOC-008.

Where a conflict is discovered, the authoritative document must be updated rather than maintaining competing definitions.

---

# 24. Acceptance Criteria

The schema is architecturally acceptable when:

* SHA512 is the logical binary-content identifier;
* internal `file_id` does not replace SHA512 as file identity;
* rename and move do not alter file identity;
* a binary-content change produces a new SHA512 identity;
* analysis results are associated with the correct file and producing module;
* automatic and manual classifications can be distinguished;
* manual decisions cannot be silently overwritten;
* module executions are recorded independently from files;
* important history can be preserved;
* collection roots can be configured without hard-coded directory names;
* Review Queue is sufficient for user decisions without a separate Migration Queue;
* the schema can support approximately 5 million files without requiring the entire collection in memory;
* modules can exchange persistent information through the shared database without direct module-to-module communication.

---

# End of DOC-005
