# DOC-012 – File Identity Model

## 1. Purpose

This document defines how image files are uniquely identified within the project.

Its purpose is to establish a deterministic and consistent model for tracking files throughout their lifecycle, regardless of their physical location within the managed collection.

The rules defined in this document shall be used by all modules interacting with the database.

---

# 2. Design Philosophy

The project manages **files**, not folders.

Folders, filenames and directory structures may change over time.

The binary content of a file is considered the primary identifier of that file.

Every image known to the system shall be represented by exactly one active database record.

---

# 3. File Identity

Each database record represents one specific binary version of one image.

A record is uniquely identified by two independent values:

* **file_id**
* **SHA512**

These values serve different purposes.

---

## file_id

`file_id` is the permanent identifier of a database record.

Its purpose is to provide a stable internal reference used by all project modules.

Rules:

* assigned only once;
* never modified;
* never reused;
* unique within the database.

Even if a record later becomes archived, its file_id shall never be assigned to another image.

---

## SHA512

SHA512 uniquely identifies the binary contents of a file.

The project assumes that identical SHA512 values represent identical binary content.

SHA512 is calculated by the Scanner Module.

---

# 4. Active Record Detection

During every scan the Scanner shall:

1. calculate SHA512;
2. search for an active record with the same SHA512.

If such a record exists:

* update its current path if necessary;
* update file metadata if necessary;
* refresh its last_seen timestamp;
* keep the existing file_id.

No new database record shall be created.

---

# 5. New Record Creation

If no active record exists with the calculated SHA512:

* a new file_id shall be assigned;
* a new database record shall be created;
* status shall be set to ACTIVE.

This applies regardless of filename or directory.

---

# 6. Filename Changes

Changing a filename does **not** create a new database record.

Example:

Before

/TODO/furina (1).jpg

After

/TODO/furina.jpg

Since SHA512 remains unchanged:

* file_id remains unchanged;
* only current_path is updated.

---

# 7. File Relocation

Moving a file between supported directories does **not** create a new database record.

Only current_path shall be updated.

Examples:

TODO → AI

AI → Archive

Archive → TODO

provided the SHA512 remains unchanged.

---

# 8. Binary Modification

If the binary contents of a file change, its SHA512 changes.

Examples include:

* brightness adjustment;
* contrast modification;
* colour correction;
* resizing;
* recompression;
* metadata removal that changes file bytes;
* image editing.

In this situation the modified file shall be treated as a **new file**.

The existing record shall remain unchanged until it becomes archived.

A new database record shall be created for the modified image.

---

# 9. Archived Records

After completion of a full Scanner execution:

Every previously ACTIVE record whose SHA512 was not encountered during the scan shall become:

ARCHIVED

Archived records:

* remain stored in the database;
* retain their original file_id;
* shall never become ACTIVE again automatically.

---

# 10. Record Lifecycle

Typical lifecycle:

ACTIVE

↓

file removed or modified

↓

ARCHIVED

A modified version of the image becomes an entirely new ACTIVE record with a new file_id.

---

# 11. Supported Path Changes

The following operations update an existing record:

* filename change;
* folder change;
* AutoSort relocation;
* Renamer execution.

Provided SHA512 remains identical.

---

# 12. Unsupported Identity Changes

The following operations always create a new record:

* image editing;
* recompression;
* pixel modifications;
* binary modifications;
* replacement with another image.

Any operation producing a different SHA512 shall be considered a new image.

---

# 13. Record Metadata

Every record shall contain at minimum:

* file_id
* SHA512
* current_path
* width
* height
* file size
* creation timestamp (database)
* last_seen timestamp
* status

Additional analysis data (Universe, Character, Themes, etc.) are associated with the same file_id.

---

# 14. Record Status

Minimum supported statuses:

ACTIVE

Image exists within one of the supported directories.

ARCHIVED

Image no longer exists within any supported directory.

FAILED

Reserved for records that could not be fully processed due to critical Scanner errors.

Additional statuses may be introduced by future project versions.

---

# 15. Integrity Principles

The system assumes that accidental SHA512 collisions are practically impossible for the intended collection size.

If inconsistent behaviour involving SHA512 is detected, it shall be treated as an internal software, hardware or database integrity problem rather than as a normal operating condition.

---

# 16. Relationship with Other Documents

This document defines the identity model used throughout the project.

The following documents shall comply with the rules defined here:

* DOC-005A — Database Schema
* DOC-007 — Module Execution Engine
* DOC-101 — Scanner Module
* DOC-109 — Database Access
* DOC-201 — AutoSort Engine
* DOC-202 — Database Maintenance
* DOC-203 — File Renamer Module
* DOC-401 — Collection Consistency Checker

---

# 17. Design Principle

The project deliberately distinguishes between:

* **logical database records** (file_id),
* **binary file contents** (SHA512).

A filename, directory or storage location does not define the identity of an image.

Only identical binary content represents the same image version.

This approach guarantees deterministic behaviour, simplifies module implementation and eliminates ambiguity during long-term collection management.
