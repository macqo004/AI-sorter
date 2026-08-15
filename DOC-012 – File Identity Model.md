# DOC-012 – File Identity Model

## 1. Purpose

This document defines how image files are uniquely identified within the project.

Its purpose is to establish a deterministic and consistent model for tracking binary file versions throughout their lifecycle, regardless of physical location.

The rules defined here apply to all modules that reference files in the database.

---

# 2. Design Philosophy

The project manages files independently of their names and locations.

Folders, filenames and directory structures may change over time without changing the identity of an unchanged binary file.

The binary content of a file is the primary identity of that file within the project.

The project's logical file key is the **SHA512 hash of the binary content**.

An internal `file_id` may be used as a technical database surrogate for relationships and implementation convenience. It does not replace SHA512 as file identity.

---

# 3. Primary File Identity

The primary logical identifier of a binary file version is:

```text
SHA512
```

The project assumes that identical SHA512 values represent identical binary content.

A SHA512 collision is considered outside the normal operating model for the intended collection size. If inconsistent behaviour involving SHA512 is detected, it is treated as an integrity problem rather than as a normal file lifecycle case.

---

# 4. Internal Database Identifier

A database implementation may assign:

```text
file_id
```

`file_id` is an internal technical identifier for relationships between tables and other implementation purposes.

It is:

* assigned when the corresponding database record is created;
* unique within the database;
* never reused while the record is retained;
* independent of filename and directory;
* not an alternative definition of file identity.

If a new binary version receives a new SHA512 and therefore a new file record, it receives a new `file_id` where `file_id` is used.

---

# 5. SHA512 as the File Key

SHA512 is the logical primary key of binary file identity.

The database must not silently overwrite the SHA512 of an existing record when binary content changes.

Example:

```text
Before:
SHA512 = AAAA
file_id = 15

After binary modification:
SHA512 = BBBB
file_id = 16
```

The old record remains associated with `AAAA` and may become `ARCHIVED`. The new record represents `BBBB`.

This rule preserves the identity and analysis history of distinct binary versions.

---

# 6. Active Record Detection

During scanning or filesystem synchronization, the Scanner shall:

1. calculate SHA512 reliably;
2. search for the corresponding SHA512 record;
3. determine its current lifecycle state;
4. update the record and filesystem state as appropriate.

If the same SHA512 already exists in an archived record and the unchanged binary content is encountered again, the existing record may be restored to `ACTIVE` rather than creating a second logical identity, provided that the archived record is still retained.

If the SHA512 does not exist in the database, a new record shall be created.

---

# 7. Filename Changes

Changing a filename does not change file identity.

Example:

```text
/TODO/furina (1).jpg
```

to:

```text
/TODO/furina.jpg
```

If SHA512 remains unchanged:

* SHA512 remains unchanged;
* the same file record remains active;
* filesystem information such as `current_path` and `filename` is updated.

All analysis results associated with the file remain associated with the same binary identity.

---

# 8. File Relocation

Moving a file between configured directories does not change file identity.

Examples include:

```text
SOURCE → TRANSITION
TRANSITION → FINAL
FINAL → TRANSITION
TRANSITION → SOURCE
```

provided the binary content remains unchanged.

Only filesystem state changes.

---

# 9. Binary Modification

If the binary contents of a file change, the SHA512 changes.

Examples include:

* image editing;
* resizing;
* recompression;
* metadata changes that alter file bytes;
* pixel modifications;
* replacement with another binary file.

The modified binary is a new file identity.

The previous record is not rewritten with the new SHA512. A new record is created for the new SHA512.

The previous record may become `ARCHIVED` according to its actual filesystem state and the rules of Scanner and Database Maintenance.

---

# 10. Duplicate Binary Files

If multiple physical filesystem entries contain identical binary content, they have the same SHA512 and therefore the same logical file identity.

Different:

* filenames;
* directories;
* collection roots;
* copy/duplicate suffixes;
* storage locations

do not create different binary identities when SHA512 remains identical.

Handling of multiple physical copies is a separate operational concern and does not change this identity model.

---

# 11. Archived Records

A file record may become:

```text
ARCHIVED
```

when the corresponding binary file is no longer present in the managed filesystem, or when a new binary version replaces it.

Archived records:

* retain their original SHA512;
* retain their original `file_id`, if used;
* retain their historical identity;
* must not have their SHA512 overwritten with another binary file's SHA512.

Archived records may later be removed by Database Maintenance according to its retention policy.

If an archived record is still retained and the same unchanged SHA512 is encountered again, the record may return to `ACTIVE`.

---

# 12. Record Lifecycle

Typical lifecycle:

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

If the original binary later reappears unchanged and its archived record still exists:

```text
SHA512 A
   ↓
ARCHIVED
   ↓
encountered again
   ↓
ACTIVE
```

No second logical identity is required for the same retained SHA512.

---

# 13. Supported Path Changes

The following operations update an existing record without changing binary identity:

* filename change;
* folder change;
* AutoSort relocation;
* Renamer execution;
* user-approved migration or correction.

The condition is that the binary content remains unchanged and SHA512 remains unchanged.

---

# 14. Identity-Changing Operations

The following create a new binary file identity whenever they change SHA512:

* image editing;
* recompression;
* pixel modifications;
* binary modifications;
* replacement with another image;
* any other byte-level modification.

The decisive criterion is the resulting SHA512, not the type of operation that produced it.

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

Additional analysis and classification data are associated with the same SHA512-based file record, normally through its internal `file_id` where one is used.

---

# 16. Record Status

At minimum, the identity model recognizes:

```text
ACTIVE
ARCHIVED
```

Additional operational states such as `MISSING`, `DELETED` or `FAILED` may be introduced by Scanner or Database Maintenance without changing the underlying identity rules.

A status change does not change the SHA512 identity of the binary record.

---

# 17. SHA512 Calculation Failures

If SHA512 cannot be calculated reliably, the system must not invent a placeholder value and must not create a valid new file identity from an unreliable result.

Possible causes include:

* unreadable file;
* corrupted data;
* permission failure;
* interrupted read;
* storage or hardware failure.

The failure shall be logged according to DOC-011.

Where appropriate, the case may enter Review Queue.

The file remains distinguishable from a successfully identified file until a valid SHA512 is obtained.

---

# 18. Integrity Principles

The project does not implement a normal collision-resolution workflow for SHA512.

If a SHA512 collision or other inconsistent hash behaviour is detected, it shall be treated as a software, hardware or database integrity problem.

The system must not silently resolve such a case by inventing or substituting another hash.

---

# 19. Relationship with Database Schema

DOC-005 shall implement this identity model.

In particular:

* SHA512 is the logical primary key of binary file identity;
* SHA512 must not be overwritten when binary content changes;
* a changed SHA512 represents a new file record;
* an internal `file_id`, if retained, is a technical surrogate;
* filenames and paths must never be used as the primary identity of a file.

---

# 20. Relationship with Other Documents

The following documents shall comply with the identity rules defined here:

* DOC-005 – Database Schema
* DOC-007 – Module Execution and Architecture
* DOC-010 – Module Interface Specification
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

---

# 22. Consistency with Module Processing

The File Identity Model does not require every module to process every file at the same time.

Once Scanner has created a valid file record, other modules may process that file independently according to their own configured scope and execution schedule.

For a given module and file, the absence of that module's result may mean, among other things:

* the module has not yet been run for that file;
* the file was outside the module's processing scope when that execution occurred;
* the file was skipped;
* processing failed;
* the module deliberately does not produce a result for that file.

The existence and validity of a module result must therefore be represented explicitly rather than inferred solely from the absence of a record.
