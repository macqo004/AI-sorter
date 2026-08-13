# DOC-003

# System Architecture

**Project:** AI Image Sorter

**Version:** 0.1

**Status:** Draft

**Depends on:**

DOC-001

DOC-002

---

# 1. Purpose

This document defines the architecture of the entire application.

It describes how independent modules cooperate.

It does not describe implementation details.

---

# 2. Architectural Philosophy

The application follows a strict modular architecture.

Every module must have exactly one responsibility.

Modules communicate only through:

* SQLite database
* filesystem

Direct module-to-module communication is forbidden.

---

# 3. Core Principles

## Single Responsibility Principle

Every module performs exactly one task.

Example:

Scanner

↓

build database

Nothing else.

---

## Independent Execution

Every module can be executed independently.

Example:

Scanner

today

B&W

tomorrow

IRL

next week

Modules never require simultaneous execution.

---

## Stateless Modules

Modules do not store internal project state.

Persistent state belongs exclusively to the database.

---

## Append-Only Knowledge

Modules should append information.

They should not overwrite unrelated data.

---

# 4. High Level Architecture

Scanner

↓

Database

↓

Filter Modules

↓

AI Modules

↓

Feedback

↓

Mover

↓

Rename

Every component communicates through the database.

---

# 5. Processing Pipeline

The processing pipeline consists of independent stages.

Stage 1

Scanner

Stage 2

Simple Filters

Stage 3

AI Classification

Stage 4

User Review

Stage 5

Learning

Stage 6

Maintenance

Each stage may be stopped independently.

---

# 6. Scanner Layer

Responsibilities:

* discover files
* identify files
* update database

Scanner never performs image analysis.

---

# 7. Filter Layer

Examples:

B&W

Screenshot

Meme

IRL

Responsibilities:

Analyze images.

Store classification.

Never move files.

---

# 8. AI Layer

Examples:

Universe detection

Character detection

Theme detection

Responsibilities:

Predict.

Never rename.

Never move.

Never delete.

---

# 9. Feedback Layer

Observes user actions.

Produces training information.

Never performs classification.

---

# 10. File Operation Layer

Contains modules:

Mover

Rename

Archive

Responsibilities:

Modify filesystem.

Never perform AI.

---

# 11. Maintenance Layer

Examples:

Database cleanup

Integrity verification

Backup

Statistics

These modules never classify images.

---

# 12. Filesystem Philosophy

Filesystem is passive.

Database is active.

The application always reasons using database information.

Filesystem only reflects current physical storage.

---

# 13. TODO Tree

The TODO tree is the only source of new work.

Only files located here are eligible for active processing.

---

# 14. AI Tree

AI tree represents pending review.

No module should actively classify images located here.

Only monitoring is allowed.

---

# 15. FINAL Tree

FINAL represents confirmed user decisions.

Modules must treat FINAL as read-only.

---

# 16. Event Driven Behaviour

Modules react to events.

Examples:

New file

Moved file

Renamed file

Deleted file

Accepted classification

Rejected classification

Events update database state.

---

# 17. Failure Isolation

Module failure must never stop the entire application.

Example:

Meme filter crashes.

Scanner continues working.

B&W continues working.

Only Meme becomes unavailable.

---

# 18. Configuration

Every module has its own configuration.

Modules never modify another module's configuration.

---

# 19. Logging

Every module produces its own log.

Logs are independent.

Central log aggregation may be added later.

---

# 20. Future Compatibility

The architecture is designed for future expansion.

Adding a new module must never require redesign of existing modules.

New modules should only:

Read database.

Analyze data.

Write results.

No architectural modifications should be necessary.

---

End of DOC-003
