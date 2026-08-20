# DOC - 005 – Database Schema

**Project:** AI Image Collection Management System  
**Document:** DOC - 005  
**Version:** 4.0  
**Status:** Design Specification

**Depends on:** DOC - 001, DOC - 002, DOC - 003, DOC - 008, DOC - 009, DOC - 010, DOC - 012, DOC - 013, DOC - 014, DOC - 301, DOC - 302

---

# 1. Purpose

This document defines the logical database schema of the project.

The database is the shared persistence and communication layer between modules. Modules do not communicate directly with one another. Persistent information exchanged between modules is exchanged through the database.

DOC - 005 defines logical entities, relationships, ownership rules and persistent state. SQL syntax, indexes, migrations and engine-specific optimisations are implementation concerns unless explicitly required by this logical model.

The design targets approximately 5,000,000 logical file identities and potentially substantially more physical file locations because identical binary content may occur at multiple locations.

---

# 2. Fundamental Identity Model

The project distinguishes:

```text
SHA512
    = logical identity of binary content

File
    = one logical record for one SHA512 identity

FileLocation
    = one physical filesystem occurrence of that File
```

This distinction is mandatory.

If two physical files have the same verified SHA512, they are treated as physical occurrences of the same binary content. They are not two independent logical `File` identities.

This implements DOC - 012.

---

# 3. File Entity

`File` represents one unique binary-content identity.

Core logical fields:

| Field | Meaning |
|---|---|
| `sha512` | Logical identity of binary content; unique |
| `file_id` | Optional internal technical surrogate identifier |
| `first_seen` | First successful discovery of this content identity |
| `last_seen` | Latest successful observation of at least one physical occurrence |
| `status` | Current logical lifecycle state |

`sha512` is the logical unique key.

`file_id`, when used, exists for efficient relational references and is not the project's logical identity.

A File record is not tied to one physical path.

---

# 4. FileLocation Entity

`FileLocation` represents one physical occurrence of a File.

Core logical fields:

| Field | Meaning |
|---|---|
| `location_id` | Technical identifier of the physical occurrence |
| `file_id` / SHA512 reference | Associated File identity |
| `current_path` | Current physical path |
| `filename` | Current filename |
| `extension` | Current extension |
| `size_bytes` | Current physical size |
| `modified_time` | Current filesystem modification timestamp |
| `first_seen` | First observation of this occurrence |
| `last_seen` | Latest successful verification |
| `state` | Current location state |
| `root_id` | Configured Collection Definition root where applicable |

Typical states are:

```text
ACTIVE
MISSING
ARCHIVED
```

The implementation may use a different internal representation provided the logical distinctions remain available.

---

# 5. Multiple Physical Occurrences

The following is valid:

```text
File
SHA512 = ABC...

FileLocation #1
D:\Collection\image.jpg

FileLocation #2
E:\Backup\image.jpg
```

There is one logical File and two physical occurrences.

This is expected input to Duplicate Management.

A master/preferred physical location does not change File identity.

---

# 6. File Identity Changes

A rename or move without binary modification does not change SHA512.

A binary modification producing a different SHA512 creates a different logical File identity.

The database must never silently rewrite:

```text
File(AAAA)
```

to:

```text
File(BBBB)
```

Instead the new binary content is represented by `File(BBBB)`.

The old identity may be retained as `ARCHIVED` only when historical retention is deliberately required. It is not a mandatory state for every missing file.

---

# 7. File Lifecycle

The active identity lifecycle is primarily:

```text
new SHA512 discovered
        ↓
ACTIVE File
        ↓
physical occurrence(s) tracked by FileLocation
```

When an active file is verified as permanently absent from the managed collection, DOC - 403 governs removal of the obsolete active record.

A retained historical identity may instead be `ARCHIVED`.

An archived identity may be reactivated if the same unchanged SHA512 is discovered again and the historical identity has not been permanently removed.

---

# 8. Scanner Registration

Scanner owns filesystem discovery and registration.

Typical flow:

```text
filesystem
    ↓
Scanner
    ↓
calculate/verify SHA512
    ↓
lookup File by SHA512
    ↓
create or reactivate File if required
    ↓
create/update FileLocation
```

A newly discovered physical file must have a valid database identity before ordinary database-driven analysis modules process it.

Scanner is incremental. Successful file registrations must survive unrelated later failures.

---

# 9. Analysis Result Model

Analysis modules own and write their own result data.

The schema must support independent result sets without requiring one global pipeline state.

Examples include:

```text
BW / Color
Screenshot
Reaction
IRL
Cosplay
```

An analysis result logically belongs to:

```text
File
+ producing Module
+ feature/result context
```

A result should support, where applicable:

```text
result_id
file_id / SHA512
module_id
feature
value
confidence
created_at
```

A module must not overwrite another module's result merely because both analyse the same File.

---

# 10. Analysis Result Presence

The normal project model does not require a row for every possible File × Module combination.

Normally:

```text
result exists
    = current result is available

result absent
    = no current result is stored
```

Absence may mean that the module:

* has not processed the file;
* did not include the file in its scope;
* skipped the file;
* failed before producing a valid result;
* deliberately produces no result for that file.

Where a module needs to distinguish those conditions persistently, it may store an explicit status owned by that module. The system must not require millions of empty rows solely to represent `NOT_PROCESSED`.

---

# 11. Module Result Lifecycle

DOC - 014 defines result lifecycle policy.

The project does not require every analysis result to carry a model-generation identifier for invalidation.

A module may have:

```text
Module.version
ModuleExecution.module_version
```

for diagnostics and history.

Changing a module, model, threshold or algorithm does not automatically delete or invalidate stored results.

When the user wants a complete recalculation using the new implementation, the user uses DOC - 205 to clear the selected result set and then starts the module separately.

Unrelated module results remain intact.

---

# 12. Classification Result Model

Semantic classification is distinct from low-level analysis observations.

Examples include:

```text
PRIMARY TREE CLASS
UNIVERSE
CHARACTER
SPECIES
THEME
```

A classification result should support, where applicable:

```text
classification_id
file_id / SHA512
classification_type
value / target
confidence
source
module_id
created_at
is_current
```

Sources include:

```text
AUTOMATIC
USER
IMPORTED
```

Classification results are not the same thing as physical placement.

---

# 13. Manual Decisions

A user decision is persistent project information.

The database must distinguish:

```text
automatic result
user decision
current accepted result
```

A protected manual decision has priority over later automatic results for the same decision context until the user explicitly changes or removes it.

Manual decisions must not be erased by cleanup of an unrelated automatic result.

Detailed semantics belong to DOC - 013.

---

# 14. Review Queue

Review Queue is the common user-decision mechanism defined by DOC - 013.

A persistent Review Item may reference:

```text
review_id
file_id / SHA512
location_id where relevant
module_id
execution_id where relevant
reason
suggested_result
suggested_destination
confidence
status
created_at
resolved_at
```

The database must keep enough information to revalidate a Review Item before a physical operation is applied.

There is no separate Migration Queue or reconciliation queue in the current architecture.

---

# 15. User Decisions

Review decisions use the logical states defined by DOC - 013:

```text
ACCEPT
REJECT
MODIFY
DEFER
```

A decision may establish a manual classification or destination.

The database stores the decision; the authorised filesystem component performs the actual physical operation.

---

# 16. Module Entity

`Module` identifies an executable component.

Core logical information includes:

```text
module_id
name
version
enabled
description
```

`version` identifies the installed implementation for history and diagnostics. It is not a per-result generation mechanism.

---

# 17. ModuleExecution Entity

Each actual invocation of a module is represented by a `ModuleExecution` record.

Core logical information includes:

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

Typical logical execution states are:

```text
STARTING
RUNNING
COMPLETED
COMPLETED_WITH_WARNINGS
CANCELLED
FAILED
```

One module may have any number of executions independent of other modules.

---

# 18. File Events and History

Important historical events may be represented through immutable `FileEvent` records.

Examples include:

```text
SCANNED
DISCOVERED_LOCATION
LOCATION_CHANGED
RENAMED
MOVED
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
location_id where relevant
module_id where relevant
event_type
timestamp
related_execution_id
description
```

Events describe what happened. They do not replace current-state records.

The project does not require pure event sourcing.

---

# 19. Duplicate Management Data

DOC - 204 owns duplicate-management semantics.

The schema may represent a Duplicate Group using:

```text
duplicate_group_id
file_id / SHA512
preferred_location_id
status
source
```

The group is a management object over physical occurrences. It does not create another File identity.

A preferred/master location is an operational decision, not an identity change.

---

# 20. Set Data

DOC - 109 owns Set semantics.

A Set may have:

```text
set_id
parent context
physical path where applicable
status
created_at
updated_at
```

Membership may be represented through a relation such as:

```text
set_id
file_id / location_id
membership status
similarity/membership score where applicable
```

The exact physical SQL design is implementation-specific.

Set identity must not replace File identity.

---

# 21. Collection Definition Storage

Collection Definition is defined by DOC - 301 and DOC - 302.

The database may persist the active definition or the relevant validated representation.

Persisted information may include:

```text
root_id
path
role
enabled
access_policy
recursive/traversal settings
tree_id
node_id
parent relationship
classification-boundary information
```

The physical names `TODO`, `AI`, `Anime`, `Monster Girls`, `Western Animation` and `Themes` are not schema constants.

---

# 22. Tags

Tags are semantic metadata and are distinct from physical directory roles.

A typical model is:

```text
File
  ↓
FileTag
  ↓
Tag
```

A Theme tag is not automatically the same thing as a physical `THEME_FALLBACK` location.

Theme metadata may remain valid after a file has been promoted into a primary collection tree.

---

# 23. Collection Root and Access Policy

A configured root may have a role defined by DOC - 302, for example:

```text
PRIMARY
THEME_FALLBACK
TODO
AI
IMPORT_SOURCE
```

It also has an access policy such as:

```text
PROTECTED
READ_ONLY
MODIFY
PLAYGROUND
```

The database stores configured values; consuming modules enforce the permitted operations.

---

# 24. Current State Versus History

Current-state records support normal operation.

History explains significant past actions and decisions.

The project uses a practical combination of current state plus selected historical events and superseded results. It does not require pure event sourcing.

---

# 25. Ownership Rules

Each module owns persistent data belonging to its documented responsibility.

A module may:

* read required shared information;
* create/update its own results;
* clear its own results through the documented cleanup mechanism;
* create its own execution records and applicable events.

A module must not silently:

* overwrite another module's result;
* delete another module's protected user decision;
* reinterpret another module's table as its own state;
* establish direct runtime communication with another module.

Shared infrastructure entities remain under the ownership rules of the architecture.

---

# 26. Transactions and Failure Isolation

The schema and implementation must support incremental progress.

Successful work on files A, B and C must not be discarded merely because file D fails later.

Transaction boundaries may be per file, per safe batch or another module-specific unit.

A giant transaction covering millions of files is not required merely to preserve logical consistency.

---

# 27. Integrity Rules

The implementation shall enforce or validate where practical:

* unique SHA512 in `File`;
* valid FileLocation → File references;
* valid Module references;
* valid ModuleExecution references;
* valid Collection Definition/root references;
* valid Review Queue references;
* valid lifecycle transitions where practical;
* no fabricated SHA512 identities;
* no active FileLocation without a valid File identity.

Multiple FileLocation records may legitimately reference one File.

Two logical File records must not normally share the same SHA512.

---

# 28. Recovery and Rebuild

DOC - 202 defines database maintenance.

DOC - 206 defines project import/export/recovery packages.

DOC - 404 defines post-incident recovery procedures.

A rebuild may produce different technical `file_id` values while preserving the same SHA512 identities.

Information such as current filesystem state may be reconstructed by Scanner. User decisions and selected history may not be reconstructable from the filesystem alone and therefore require explicit backup/import support when preservation is required.

---

# 29. Scalability

The logical schema targets at least:

```text
5,000,000 File identities
```

and potentially more FileLocation records because physical duplicates are possible.

The design should avoid:

* one table per file;
* one application object per entire collection;
* one mandatory result row for every File × Module combination;
* storing image binaries in normal database tables.

Indexes and batching should be used according to the database implementation.

---

# 30. Security and Data Integrity

Database operations must not allow an analysis module to modify protected user decisions or unrelated module-owned state merely because it has database access.

The implementation should validate:

```text
SHA512 format
foreign-key relationships
valid status values
valid module ownership
valid review references
```

Database corruption or integrity violations must be surfaced as errors rather than silently normalised.

---

# 31. Relationship with Shared Standards

```text
DOC - 012
    File identity and SHA512

DOC - 013
    Review Queue and manual decisions

DOC - 014
    Module result lifecycle and cleanup policy

DOC - 301 / 302
    Collection Definition

DOC - 109
    Set semantics

DOC - 204
    Duplicate management
```

DOC - 005 implements the persistent representation of these concepts without taking ownership of their full operational specifications.

---

# 32. Architectural Invariants

1. SHA512 uniquely identifies one logical binary-content identity.
2. Multiple physical occurrences of one SHA512 are represented by multiple FileLocation records, not multiple File identities.
3. Paths and filenames do not define File identity.
4. Binary changes producing a new SHA512 produce a new File identity.
5. Analysis results are independently owned by modules.
6. Absence of a result does not require a mandatory empty row for every possible module/file combination.
7. Model or algorithm changes do not automatically clear results.
8. User-directed cleanup is the mechanism for deliberate full recalculation.
9. Protected manual decisions are distinct from automatic results.
10. Modules exchange persistent information through the database rather than direct module-to-module communication.
11. Collection Definition is configuration, not per-file analysis state.
12. Physical files are not stored as normal database payloads.

---

# 33. Acceptance Criteria

DOC - 005 is compliant when:

* SHA512 is unique within the logical File entity;
* physical duplicate occurrences can be represented without duplicate logical identities;
* File and FileLocation have clear responsibilities;
* file moves/renames preserve identity;
* binary changes create new identities;
* analysis modules can store independent results;
* user decisions can be protected independently from automatic results;
* module executions are independently recorded;
* Review Queue references can be persisted and revalidated;
* Collection Definition state can be persisted without mixing it with file analysis;
* database cleanup can remove a selected module's results without deleting File identity;
* the model remains suitable for multi-million-file collections.

---

# End of DOC - 005
