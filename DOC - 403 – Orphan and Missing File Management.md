# DOC - 403 – Orphan and Missing File Management

**Project:** AI Image Collection Management System  
**Document:** DOC - 403  
**Version:** 2.0  
**Status:** Design Specification

**Depends on:** DOC - 005, DOC - 012, DOC - 101, DOC - 301, DOC - 302

---

# 1. Purpose

This document defines the handling of two deterministic filesystem/database conditions:

1. a registered physical file no longer exists in the managed filesystem;
2. a physical file exists in configured scan scope but has no current database identity.

The project deliberately uses a simple active-state policy:

```text
verified physical absence
    ↓
remove obsolete active database record/location

physical file without identity
    ↓
Scanner registers it
```

No permanent ordinary missing-file archive is required.

Historical records/events may be retained separately where explicitly needed.

---

# 2. Identity Model

The module follows DOC - 012 and DOC - 005:

```text
SHA512
    = logical binary-content identity

File
    = logical content record

FileLocation
    = physical occurrence
```

If the same SHA512 is found at another location, it is another FileLocation of the same File identity.

---

# 3. Scope

The reconciliation scope may include configured:

```text
TODO
AI
PRIMARY
THEME_FALLBACK
IMPORT_SOURCE
other configured source roots
```

The module must respect Collection Definition and access policy.

A directory is considered part of project scope only when configuration says so.

---

# 4. Verified Missing Physical File

A missing physical occurrence is a registered FileLocation whose expected physical object cannot be found after the relevant root has been successfully inspected.

Before treating a file as missing, the system must rule out temporary access problems.

The following are not proof of deletion:

```text
unavailable drive
network storage temporarily disconnected
permission denied
locked/inaccessible directory
interrupted scan
unreadable root
```

If the root itself cannot be reliably inspected, existing records remain unchanged and the run reports the root as unavailable.

---

# 5. Removal of Verified Missing Records

When physical absence has been confirmed, the obsolete active FileLocation shall be removed.

If no other active FileLocation remains for that File identity, the active File record is removed according to the current project policy.

Example:

```text
File SHA512 = ABC...

Location A = missing
Location B = active
```

Result:

```text
remove Location A
retain File ABC and Location B
```

If the File has no remaining active occurrence:

```text
remove obsolete active File record
```

A retained historical identity may be represented as ARCHIVED only when explicitly preserved by the project, not merely because a file went missing.

---

# 6. Historical Information

Removing an obsolete active File record does not require deleting every historical event related to that content.

Events such as:

```text
SCANNED
MOVED
RENAMED
DELETED
RECONCILED
```

may be retained according to the project's history/retention policy.

Historical information must not be mistaken for an active file record.

---

# 7. Physical File Without Database Identity

A physical file found in configured scan scope with no current File identity is an orphan only in the database sense.

The default action is registration, not rejection:

```text
physical file
    ↓
Scanner
    ↓
calculate SHA512
    ↓
lookup existing File
    ├── found → add/update FileLocation
    └── absent → create File + FileLocation
```

DOC - 403 does not implement a second independent hashing/registration system.

---

# 8. Existing SHA512 at Another Location

If a discovered physical file has a SHA512 already represented by an existing File:

```text
File ABC...
    ├── Location A
    └── Location B (newly discovered)
```

The new object is registered as another FileLocation of the same logical File identity.

It is not a second File identity.

Duplicate Management may subsequently analyse the physical duplication.

---

# 9. File Registration Data

Normal registration should establish information required by DOC - 005 / DOC - 012, including where applicable:

```text
SHA512
file_id if used
location_id
current_path
filename
extension
size
modified_time
first_seen
last_seen
root_id
state
```

Additional metadata may be populated by Scanner or later modules.

A failed SHA512 calculation must not create a valid identity.

---

# 10. File Moved from Previous Path

A file may have moved before the database path was updated.

If Scanner finds the same SHA512 at a new valid location, the existing File identity is retained and the physical location is reconciled.

The old FileLocation is removed or marked inactive according to the current location-state implementation after the new occurrence is verified.

This is a location change, not a new binary identity.

---

# 11. Interaction with Scanner

Scanner remains responsible for:

* filesystem traversal;
* SHA512 calculation;
* File identity lookup/create/reactivation;
* FileLocation discovery/update;
* execution logging.

DOC - 403 defines the desired reconciliation result and safety rules.

It must not create a parallel scanner implementation.

---

# 12. Interaction with Collection Definition

Collection Definition determines whether a physical location belongs to managed scope.

Registration of a physical file does not imply that its final semantic classification is correct.

For example:

```text
PRIMARY/Winx Club/image.jpg
```

may be registered even if later analysis suggests another universe.

Classification correction belongs to the analysis/Review Queue/AutoSort workflow.

---

# 13. Review Queue

Missing-file and orphan registration are normally deterministic and do not require Review Queue.

Review Queue may become involved later for:

* classification;
* placement;
* duplicate handling;
* ambiguous filesystem state.

---

# 14. Safety Rules

The module shall enforce:

1. Do not remove records because an entire root is temporarily inaccessible.
2. Confirm physical absence before removing a FileLocation or active File record.
3. Register real physical files rather than ignoring them.
4. Reuse existing SHA512 identity when a physical duplicate is found.
5. Never fabricate a SHA512.
6. Do not delete physical files as part of orphan/missing management.
7. Do not perform semantic classification.
8. Do not create FINAL structure.
9. Preserve protected user decisions.

---

# 15. Repeated Execution

The operation is designed to run repeatedly.

Example:

```text
Run 1
file absent but root unavailable
→ leave DB unchanged

Run 2
root reachable
file confirmed absent
→ remove obsolete active record

Run 3
same binary reappears
→ Scanner creates/reactivates the File identity
```

Repeated execution must be idempotent for already reconciled state.

---

# 16. Logging

Operations should be logged according to DOC - 011 and DOC - 007.

The summary should include:

```text
execution_id
roots inspected
physical files checked
verified missing locations removed
Files removed
new Files registered
new FileLocations registered
known-SHA512 occurrences reconciled
unavailable roots
errors
completion status
```

---

# 17. Relationship with Other Documents

```text
DOC - 005  Database Schema
DOC - 012  File Identity Model
DOC - 101  Scanner
DOC - 201  AutoSort
DOC - 202  Database Maintenance
DOC - 204  Duplicate Management
DOC - 402  Collection Integrity and Reconciliation
DOC - 404  Recovery and Rescan Procedures
```

Responsibility separation:

```text
DOC - 101 → discover and register
DOC - 403 → define verified orphan/missing outcomes
DOC - 204 → duplicate management
DOC - 402 → broader cross-source reconciliation
DOC - 404 → recovery procedures
```

---

# 18. Acceptance Criteria

DOC - 403 is compliant when it can:

* distinguish inaccessible roots from confirmed missing files;
* remove obsolete active FileLocation records after verified absence;
* remove an obsolete active File record when no active occurrence remains, according to project policy;
* preserve intentionally retained historical identities separately;
* register physical files without current database identity through Scanner;
* associate newly found physical copies with an existing SHA512 File identity;
* preserve SHA512 identity across moves and renames;
* operate safely on large collections;
* avoid classification, duplicate deletion and FINAL structure creation.

---

# End of DOC - 403
