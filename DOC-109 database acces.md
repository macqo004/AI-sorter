# DOC-009

# Database Access Layer

**Project:** AI Image Collection Management System

**Document:** DOC-009

**Version:** 1.0

**Status:** Design Specification

---

# 1. Purpose

This document defines how every module interacts with the project database.

The Database Access Layer is not a software library but a collection of architectural rules ensuring that all modules use the database consistently.

The database is the only shared communication medium between modules.

---

# 2. Design Philosophy

Every module is independent.

Modules never communicate directly.

Instead, they:

* read existing information from the database,
* perform their own work,
* write only their own results back to the database.

The database is the single source of shared project knowledge.

---

# 3. Database Responsibilities

The database is responsible for storing:

* image metadata;
* analysis observations;
* module results;
* user decisions;
* migration suggestions;
* processing history.

The database is **not** responsible for storing application configuration.

Configuration belongs to Configuration Manager (DOC-008).

---

# 4. Communication Model

Every module follows the same communication pattern.

```text id="e4vhqy"
Read

↓

Process

↓

Write

↓

Exit
```

Modules never:

* exchange memory;
* call other modules;
* exchange temporary files.

---

# 5. Data Categories

The database stores three logical categories of information.

## Facts

Objective information.

Examples:

* SHA512
* file size
* modification date
* image dimensions
* file format

Facts are deterministic.

---

## Observations

Information produced by AI modules.

Examples:

* Universe
* Character
* Theme
* Species
* IRL
* Screenshot
* B&W
* confidence values

Observations may change as models improve.

---

## User Decisions

Information explicitly created by the user.

Examples:

* UserReject
* Accepted migration
* Rejected migration
* Manual verification

User Decisions always have higher priority than AI observations.

---

# 6. Reading Policy

Before analysing an image, a module should first read all relevant information already stored in the database.

Existing observations should be reused whenever possible.

Modules should avoid repeating expensive operations unnecessarily.

---

# 7. Writing Policy

Each module owns only its own observations.

Examples:

Scanner

updates Scanner data.

Universe Analysis

updates Universe observations.

Character Analysis

updates Character observations.

Modules shall never overwrite observations owned by another module.

---

# 8. Update Policy

Database updates should modify only changed values.

Unnecessary UPDATE operations should be avoided.

This reduces:

* database writes;
* SSD wear;
* execution time.

---

# 9. Incremental Saving

Long-running modules shall save progress incrementally.

Example:

```text id="tkujlwm"
Image

↓

Analyse

↓

Write results immediately

↓

Continue
```

A module must never wait until the end of processing before writing all results.

---

# 10. Failure Recovery

If processing stops unexpectedly:

```text id="8knkru"
1000 images

↓

999 processed

↓

1 failed
```

The results for the 999 successfully processed images remain valid.

Previously completed work is never discarded.

---

# 11. Memory Usage

Modules may use RAM as working memory.

The objective is not to minimise memory usage.

The objective is to minimise processing time while maintaining system stability.

Modules should adapt memory usage to available system resources.

Example:

* larger cache;
* larger processing batches;
* additional worker threads.

Provided that sufficient memory remains available for the operating system and other applications.

---

# 12. Working Cache

Modules may cache:

* database records;
* temporary analysis results;
* processing queues.

Large image collections shall not be loaded entirely into RAM.

Modules should process images in manageable batches or streams.

Temporary caches should be released after they are no longer needed.

The database remains the permanent source of truth.

---

# 13. Transactions

The project does not require long-running global transactions.

Short write operations are preferred.

Each successfully processed image should become immediately available to other modules.

---

# 14. Performance Guidelines

Modules should:

* batch INSERT operations when practical;
* avoid unnecessary UPDATE operations;
* use indexed fields;
* retrieve only required columns;
* avoid loading unnecessary records.

Performance optimisation must never compromise database consistency.

---

# 15. Database Consistency

Every completed write operation must leave the database in a valid state.

A partially completed module execution must never corrupt previously stored information.

---

# 16. Concurrency

The project assumes a single interactive user.

Complex database locking mechanisms are not required.

Future versions may introduce additional concurrency protection if multi-user operation becomes necessary.

---

# 17. Database Version

Modules should verify database schema compatibility before execution.

If an incompatible schema is detected, the module should terminate gracefully and report the problem.

---

# 18. Logging

Every database-related error should be logged.

Typical events include:

* failed connection;
* failed write;
* failed update;
* invalid schema;
* integrity violation.

Successful operations should not generate excessive log output unless verbose logging is enabled.

---

# 19. Design Principles

The Database Access Layer follows these principles:

* one shared database;
* independent modules;
* incremental saving;
* reusable observations;
* user decisions take precedence over AI observations;
* adaptive memory usage;
* performance without sacrificing consistency.

---

# 20. Acceptance Criteria

The Database Access Layer is considered correctly implemented when:

* all modules communicate exclusively through the database;
* completed work survives unexpected interruption;
* modules update only their own observations;
* user decisions are never overwritten by AI;
* memory usage scales with available system resources;
* the database remains consistent after every successful write operation.

---

# End of DOC-009
