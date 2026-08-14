# DOC-012 – File Identity Model

## 1. Purpose

This document defines how image files are uniquely identified within the project.

Its purpose is to establish a deterministic and consistent model for tracking files throughout their lifecycle, regardless of their physical location within the managed collection.

The rules defined in this document shall be used by all modules interacting with the database.

---

# 2. Design Philosophy

The project manages **files**, not folders.

Folders, filenames and directory structures may change over time.

The binary content of a file is the primary identity of that file within the project.

The project's logical file key is the SHA512 hash of the binary content.

An internal `file_id` may be used as a technical database surrogate for efficient foreign-key relationships, but it is not an alternative file identity. It belongs to the database record representing a particular SHA512 value.

---

# 3. File Identity

Each database record represents one specific binary version of one image.

The primary logical identifier is:

```text
SHA512
```

SHA512 identifies the exact binary content represented by the record.

The project assumes that identical SHA512 values represent identical binary content. Accidental SHA512 collisions are considered outside the normal operating model for the intended collection size.

`file_id` is an internal database identifier. It may be referenced by other tables, but it does not replace SHA512 as the identity of the file content.

The important distinction is:

```text
SHA512
    = logical identity of the binary file content

file_id
    = internal database reference to the corresponding record
```

---

# 4. SHA512 as Primary File Key

SHA512 shall be unique among active file records.

The database should treat SHA512 as the primary logical key for identifying a binary file version.

If the same binary file is encountered again under another filename or path, its SHA512 remains unchanged and the existing record is reused.

If SHA512 changes, the system is no longer dealing with the same binary file version.

The database record representing the previous SHA512 must therefore not simply have its SHA512 field overwritten while retaining the old file identity.

Instead:

```text
old SHA512
    ↓
old file record
    ↓
ARCHIVED / historical state

new SHA512
    ↓
new file record
    ↓
ACTIVE
```

The new binary content receives a new internal `file_id` if `file_id` is used by the implementation.

This preserves the identity and history of both binary versions.

---

# 5. Active Record Detection

During scanning or filesystem synchronization the Scanner shall:

1. calculate SHA512;
2. search for an active record with the same SHA512.

If such a record exists:

* update its current path if necessary;
* update file metadata if necessary;
* refresh its `last_seen` timestamp;
* retain the same SHA512;
* retain the same internal `file_id`, where one is used.

No new file record shall be created merely because the filename or directory changed.

---

# 6. New Record Creation

If no active record exists with the calculated SHA512:

* a new file record shall be created;
* a new internal `file_id` shall be assigned if the implementation uses one;
* SHA512 shall be stored as the logical file key;
* status shall be set to `ACTIVE`.

This applies regardless of filename or directory.

---

# 7. Filename Changes

Changing a filename does **not** change file identity.

Example:

```text
/TODO/furina (1).jpg
```

to:

```text
/TODO/furina.jpg
```

Since SHA512 remains unchanged:

* SHA512 remains the same;
* the same file record remains active;
* only filesystem information such as `current_path` and `filename` is updated.

---

# 8. File Relocation

Moving a file between supported directories does **not** change file identity.

Only filesystem state is updated.

Examples include:

```text
TODO → AI
AI → FINAL
FINAL → AI
AI → TODO
```

provided the binary content remains unchanged.

---

# 9. Binary Modification

If the binary contents of a file change, its SHA512 changes.

Examples include:

* brightness adjustment;
* contrast modification;
* colour correction;
* resizing;
* recompression;
* metadata removal that changes file bytes;
* image editing.

In this situation the modified file shall be treated as a **new binary file version**.

The previous SHA512 record is not overwritten with the new SHA512.

A new record shall be created for the new SHA512.

The previous record may become `ARCHIVED` according to its actual filesystem state and the rules of the Scanner and Database Maintenance modules.

---

# 10. Duplicate Binary Files

If two filesystem entries contain identical binary content, they have the same SHA512 and therefore represent the same logical file content.

The database must not create separate logical file identities merely because the files have different:

* filenames;
* directories;
* collection roots;
* capitalization;
* copy/duplicate suffixes.

The filesystem may temporarily contain multiple physical references to the same binary content. Handling of such duplicates is a separate operational concern and does not change the SHA512-based identity model.

---

# 11. Archived Records

A previously active record may become:

```text
ARCHIVED
```

when the corresponding binary file is no longer present in the managed filesystem according to the applicable scanner rules, or when a modified binary version replaces it.

Archived records:

* retain their original SHA512;
* retain their original `file_id`, if one was assigned;
* retain their historical identity;
* must not have their SHA512 overwritten with the SHA512 of another binary file.

Archived records may later be removed by Database Maintenance according to its retention rules.

---

# 12. Record Lifecycle

Typical lifecycle for one binary version:

```text
SHA512 A
   ↓
ACTIVE
   ↓
file removed or replaced
   ↓
ARCHIVED
```

If the file is modified:

```text
SHA512 A
   ↓
ARCHIVED

SHA512 B
   ↓
new ACTIVE record
```

The two SHA512 values represent two different binary file versions.

---

# 13. Supported Path Changes

The following operations update an existing record without changing file identity:

* filename change;
* folder change;
* AutoSort relocation;
* Renamer execution;
* user-approved migration/correction.

The condition is that the binary content remains unchanged and therefore SHA512 remains unchanged.

---

# 14. Unsupported Identity Changes

The following operations create a new binary file identity:

* image editing;
* recompression;
* pixel modifications;
* binary modifications;
* replacement with another image;
* any other operation that changes SHA512.

The decisive criterion is the resulting SHA512.

---

# 15. Record Metadata

Every active file record shall contain at minimum:

* SHA512;
* current path;
* width;
* height;
* file size;
* database creation timestamp;
* last_seen timestamp;
* status.

An internal `file_id` may additionally be stored for relational database use.

Additional analysis data such as Universe, Character, Themes and other module results are associated with the SHA512-based file record, normally through its internal `file_id` where one is used.

---

# 16. Record Status

Minimum supported statuses include:

```text
ACTIVE
ARCHIVED
```

Additional operational states such as `MISSING`, `DELETED` or `FAILED` may be introduced where required by Scanner or Database Maintenance specifications.

A status must not change the identity of the underlying SHA512 value.

---

# 17. SHA512 Calculation Failures

If SHA512 cannot be calculated reliably, the system must not invent a placeholder value and must not treat the file as a valid new identity.

Possible causes include:

* unreadable file;
* corrupted data;
* permission failure;
* interrupted read;
* storage or hardware failure.

The failure shall be logged according to DOC-011.

Where appropriate, the case may enter Review Queue.

The file must remain distinguishable from a successfully identified file until a valid SHA512 is obtained.

---

# 18. Integrity Principles

The project assumes that accidental SHA512 collisions are practically impossible for the intended collection size.

A SHA512 collision is therefore not treated as a normal operating scenario requiring an alternate identity system.

If inconsistent behaviour involving SHA512 is detected, it shall be treated as an internal software, hardware or database integrity problem.

The system must not silently resolve such a conflict by assigning arbitrary replacement hashes.

---

# 19. Relationship with Database Schema

DOC-005 shall implement this identity model.

In particular:

* SHA512 is the logical primary key of binary file identity;
* SHA512 must not be overwritten when binary content changes;
* a changed SHA512 represents a new file record;
* an internal `file_id`, if retained, is a technical surrogate and receives a new value for the new record;
* filenames and paths must never be used as the primary identity of a file.

---

# 20. Relationship with Other Documents

The following documents shall comply with the rules defined here:

* DOC-005 – Database Schema
* DOC-007 – Module Execution and Architecture
* DOC-101 – Scanner Module
* DOC-109 – Database Access
* DOC-201 – AutoSort Engine
* DOC-202 – Database Maintenance
* DOC-203 – File Renamer Module
* DOC-401 – Collection Consistency Checker

---

# 21. Design Principle

The project deliberately distinguishes between:

* **binary file identity** — SHA512;
* **internal database reference** — `file_id`, where used;
* **filesystem state** — path, filename, size and timestamps.

The primary identity of a binary file is its SHA512.

A filename, directory or storage location does not define file identity.

If binary content changes, SHA512 changes and the database must represent that content as a new file record rather than modifying the identity of the old record.
