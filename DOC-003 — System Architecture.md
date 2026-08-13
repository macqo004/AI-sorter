# DOC-002

# Database Architecture Specification

**Project:** AI Image Sorter

**Version:** 0.1

**Status:** Draft

**Depends on:** DOC-001 Project Specification

---

# 1. Purpose

This document defines the architecture of the project database.

The database is the central component of the application.

Every module reads information from the database and stores its own results inside it.

The database is considered the **single source of truth**.

Directory structure is treated only as the physical location of files.

---

# 2. Design Goals

The database must satisfy the following requirements:

* fully offline
* lightweight
* portable
* resilient against crashes
* capable of handling millions of images
* easy to backup
* independent of operating system

The database should remain usable for many years without requiring structural redesign.

---

# 3. Database Engine

SQLite has been selected for the first implementation.

Reasons:

* zero configuration
* single file
* no server required
* excellent Python support
* ACID transactions
* fast enough for millions of records
* perfect for offline applications

Future migration to another SQL engine should remain possible without redesigning application logic.

---

# 4. Fundamental Design Principles

## 4.1 Source of Truth

The database always contains the authoritative state.

Folders never define application logic.

Modules must never rely exclusively on directory names.

---

## 4.2 Immutable Image Identity

Every image receives a permanent internal identifier.

The identifier never changes.

File name changes do not create a new image.

Folder changes do not create a new image.

Only deletion removes an image from active use.

---

## 4.3 SHA-512

SHA-512 is the primary technical identifier.

It is used to:

* recognize files
* detect moved files
* detect renamed files
* connect AI history
* detect manual corrections

Filename is never treated as identity.

---

## 4.4 Separation of Responsibilities

The database stores facts.

Modules perform analysis.

No module owns the database.

Every module only updates fields belonging to its own responsibility.

Example:

Scanner:

* creates image record
* updates file metadata

B&W Filter:

* updates monochrome classification

Screenshot Filter:

* updates screenshot classification

Mover:

* updates file location

Rename:

* updates filename

No module modifies another module's results.

---

# 5. Database Layers

The database is logically divided into several layers.

Layer 1

Image identity

Layer 2

Filesystem information

Layer 3

Analysis results

Layer 4

AI classification

Layer 5

User feedback

Layer 6

History

This separation keeps modules independent.

---

# 6. Logical Data Flow

Scanner

↓

Image Identity

↓

Filesystem Metadata

↓

Filter Results

↓

AI Results

↓

User Review

↓

History

Every module appends information.

Earlier results are preserved whenever possible.

---

# 7. Image Lifecycle

An image enters the system once.

Scanner creates its database record.

The image keeps the same internal identity throughout its entire lifetime.

Possible events:

* scanned
* analyzed
* classified
* moved
* renamed
* accepted
* rejected
* deleted

These are events.

They are not different images.

---

# 8. Directory Philosophy

Directories are user interface.

Database is application interface.

This distinction is fundamental.

Changing a directory should never require rebuilding the database.

---

# 9. TODO Tree

Only images located inside the TODO tree are eligible for automatic classification.

Modules performing active classification may process only TODO images.

---

# 10. AI Tree

Images inside the AI tree are considered waiting for user verification.

Modules do not classify these images again.

The system only monitors:

* location
* filename
* existence

---

# 11. FINAL Tree

The FINAL tree represents the user's confirmed library.

Files inside FINAL are never automatically reclassified.

The database may only observe:

* movement
* rename
* deletion

---

# 12. User Feedback

User actions are treated as valuable information.

Examples:

Accepted prediction

Wrong character

Wrong universe

Wrong category

Returned to TODO

Moved elsewhere

Deleted

Every action may later improve AI behaviour.

---

# 13. History

The database never assumes why something happened.

Instead it records observable facts.

Example:

Image moved

Old path

↓

New path

Timestamp

No assumptions are made.

Interpretation belongs to higher-level modules.

---

# 14. Performance Goals

Initial target:

5 million images

Future target:

20 million images

The schema should remain unchanged.

Only indexes may require optimization.

---

# 15. Backup Strategy

SQLite database is backed up independently from image files.

The database must always be recoverable without rescanning the entire collection.

Periodic backups should be supported by future maintenance tools.

---

# 16. Future Expansion

The database architecture reserves space for future modules.

Examples:

OCR

Wallpaper detection

Pose detection

Outfit detection

Similarity search

Character recognition

Universe recognition

No redesign should be required when new analysis modules appear.

---

# 17. Next Document

DOC-003

Database Schema

The next document defines:

* tables
* columns
* indexes
* constraints
* relations

This document intentionally contains no SQL implementation.

It defines architecture only.
