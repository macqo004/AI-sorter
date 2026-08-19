# DOC - 403 – Orphan and Missing File Management

**Project:** AI Image Collection Management System  
**Document:** DOC - 403  
**Version:** 1.0  
**Status:** Design Specification

---

# 1. Purpose

This document defines how the project handles two filesystem/database inconsistencies:

1. a database file record exists, but the corresponding physical file no longer exists;
2. a physical file exists in a configured scan location, but no corresponding database record exists.

The intended model is deliberately simple:

```text
DB record without physical file
        ↓
record is removed

Physical file without DB record
        ↓
file is registered in DB
```

The module does not invent a separate permanent orphan archive and does not keep ordinary missing-file records merely for historical retention.

---

# 2. Relationship with File Identity

File identity follows DOC - 012 and DOC - 005.

The logical identity of binary content is its SHA512.

A physical file is registered in the database only after the current filesystem object can be inspected sufficiently to establish its identity.

A missing filesystem object has no current physical instance to maintain.

---

# 3. Scope

The module operates on configured filesystem locations that are eligible for database reconciliation.

The scope may include, according to configuration and access policy:

```text
TODO
AI
FINAL
other configured source locations
```

The module must respect Directory Access Policy and must not assume that every directory on the machine belongs to the project.

---

# 4. Missing File Records

A missing file record exists when a database record points to a physical file that cannot be found at its current recorded location during reconciliation.

Before removal, the module should verify that the absence is real rather than caused by a temporary access problem.

Examples of conditions requiring retry or error reporting rather than immediate deletion include:

* filesystem unavailable;
* network or removable storage temporarily disconnected;
* insufficient permission to inspect the directory;
* path temporarily inaccessible;
* scan interrupted before the relevant location was examined.

A file should be considered missing only after the configured reconciliation procedure has established that the physical object is absent from the applicable scope.

---

# 5. Removal of Missing Records

When a file has been verified as physically absent, its obsolete database record is removed.

The default rule is:

```text
physical file permanently absent
        ↓
remove corresponding file record
```

Removing the record does not mean that a future file with the same SHA512 is forbidden from being registered again.

If the same binary content is later found again, Scanner may register it as a currently existing file according to normal scanning rules.

---

# 6. No Ordinary Missing Archive

The project does not maintain a permanent `MISSING` archive solely to preserve records for files that have disappeared from disk.

Historical events such as `SCANNED`, `MOVED`, `DELETED` or reconciliation actions may be retained according to the project's logging and history rules, but the obsolete active file record itself is removed when the physical absence has been verified.

This keeps the active database representative of files that actually exist in the managed collection.

---

# 7. Orphan Files

An orphan file is a physical file found inside a configured scanning scope for which no current database record exists.

The default action is registration, not rejection.

```text
physical file found
        ↓
SHA512 calculated
        ↓
create File record
        ↓
create physical FileLocation record
        ↓
file becomes available to normal module processing
```

The file is therefore not treated as a special permanent category merely because it was discovered without a previous database record.

---

# 8. Registration of a New Physical File

When an orphan file is discovered, registration should establish the information required by DOC - 005 and DOC - 012, including where applicable:

```text
SHA512
file identity
current physical path
filename
extension
size
filesystem modification time
first seen
current location/root
```

Additional metadata may be populated by Scanner or later modules according to their own specifications.

A failed SHA512 calculation must not create a fabricated or placeholder identity.

---

# 9. Existing SHA512 Found at Another Location

When a physical file is found and its SHA512 already exists in the database, the system shall treat the new filesystem object as another physical occurrence of the same logical content.

Example:

```text
DB:
SHA512 = ABC...
Location = A:\Collection\image.jpg

Scanner finds:
B:\Backup\image.jpg
SHA512 = ABC...
```

The result is not a second independent binary identity.

Instead:

```text
SHA512 ABC...
    ├── Location A
    └── Location B
```

This is an expected input to Duplicate Management and filesystem reconciliation.

The system does not design its normal workflow around the possibility that two genuinely different images will intentionally share the same SHA512. Such a case is treated as an integrity problem.

---

# 10. Interaction with Scanner

Scanner is responsible for discovering files and calculating their SHA512 according to DOC - 101 and DOC - 012.

Orphan File Management does not require a second independent hashing implementation.

A typical workflow is:

```text
Scanner
   ↓
filesystem discovery
   ↓
SHA512
   ↓
lookup in database
   ├── existing identity → update/reconcile location
   └── unknown identity  → create file record
```

This module defines the reconciliation outcome; Scanner remains responsible for the actual scanning operation.

---

# 11. Interaction with Collection Definition

Collection Definition determines whether a filesystem location is inside a configured project scope and what role that root has.

A file found in a configured location may therefore be registered even when its final semantic classification is unknown.

Registration does not imply approval of the file's final placement.

For example:

```text
FINAL/Winx Club/image.jpg
```

may be registered because it physically exists there even if later analysis determines that the image is probably from another universe.

Classification consistency is handled by the appropriate analysis and Review Queue workflow.

---

# 12. Interaction with Review Queue

A missing-file reconciliation is normally not a Review Queue decision because the rule is deterministic once absence has been verified.

Likewise, finding a file without a database record does not normally require Review Queue approval. The file is simply registered.

Review Queue may become involved later when classification, placement, duplicate handling, or another non-deterministic decision requires the user's judgement.

---

# 13. Interaction with Duplicate Management

Orphan registration and duplicate handling are separate operations.

When the discovered file has a SHA512 already present in the database, the database must represent the additional physical occurrence rather than creating an unrelated binary identity.

Duplicate Management may then determine whether one occurrence should be treated as the preferred master or whether the occurrences require user review.

This module does not delete duplicate physical files.

---

# 14. Interaction with Collection Consistency Checker

DOC - 401 detects possible classification/location inconsistencies in FINAL.

DOC - 402 reconciles broader consistency between filesystem, database and Collection Definition.

DOC - 403 handles the narrower identity-existence problem:

```text
Does the physical file exist?
Does the database record exist?
```

It does not replace the broader checks performed by DOC - 401 or DOC - 402.

---

# 15. Safe Handling of Missing Locations

The system must distinguish a real missing file from a location that simply could not be inspected.

For example:

```text
Drive disconnected
        ≠
files deleted
```

Therefore a reconciliation run must not delete thousands of database records merely because an entire configured root was temporarily unavailable.

When a root cannot be inspected reliably, the run should report the root as unavailable and leave its existing file records unchanged until a successful scan can verify their absence.

---

# 16. State Transitions

The intended logical transitions are:

```text
Physical file exists + DB record exists
        ↓
normal state

Physical file absent + DB record exists
        ↓
verified missing
        ↓
remove file record

Physical file exists + DB record absent
        ↓
orphan discovered
        ↓
create file record

Physical file exists + same SHA512 already known
        ↓
add/reconcile physical location
```

The exact database operations are implementation details of DOC - 005 and the Scanner/reconciliation implementation.

---

# 17. Manual Deletion

If the user intentionally deletes a physical file, the next successful reconciliation should remove its obsolete database file record.

The system may preserve an historical event recording that the file was deleted, subject to the project's history and logging rules.

The historical event is not a substitute for an active file record.

---

# 18. File Moved Outside the Previous Path

A file may legitimately be moved without its old database path being immediately updated.

A subsequent successful scan may find the same SHA512 at a new location.

The system should reconcile the existing logical file identity with its new physical location rather than creating a second logical file identity.

If the old location is no longer valid and the new location is confirmed, the old location record may be removed while the new location is retained.

---

# 19. Processing of Newly Registered Files

After an orphan file is registered, its analysis state begins according to DOC - 014.

For example:

```text
new file
    ↓
Scanner registers identity
    ↓
IRL = NOT_PROCESSED
Screenshot = NOT_PROCESSED
Universe = NOT_PROCESSED
Character = NOT_PROCESSED
...
```

The registration process does not automatically require all analysis modules to run.

Modules remain independently executable.

---

# 20. Logging

Reconciliation operations should be logged according to DOC - 011.

Logs should identify, where applicable:

```text
execution_id
root/path inspected
files checked
missing records removed
new files registered
existing SHA512 occurrences reconciled
unavailable roots
errors
completion status
```

---

# 21. Safety Principles

The module follows these principles:

1. A missing file record is removed only after physical absence is verified.
2. Temporary inability to access a root must not be treated as mass deletion.
3. A physical file without a record is registered rather than ignored.
4. An existing SHA512 represents the same logical content even when found at multiple locations.
5. This module does not delete physical files.
6. This module does not automatically classify files.
7. This module does not create FINAL structure.
8. Duplicate selection remains the responsibility of Duplicate Management and user review where required.

---

# 22. Acceptance Criteria

DOC - 403 is compliant when it can:

* reliably identify database records whose physical files are absent;
* remove verified obsolete file records;
* avoid deleting records when an entire root is merely inaccessible;
* discover physical files that have no database record;
* register newly discovered files using their SHA512 identity;
* reconcile an already known SHA512 found at an additional location;
* cooperate with Scanner, Database Schema, Duplicate Management and Collection Definition;
* leave classification and user-decision logic to the appropriate modules;
* operate offline and on large collections.

---

# End of DOC - 403
