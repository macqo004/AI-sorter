# DOC-009

# Database Access Layer

**Project:** AI Image Collection Management System

**Document:** DOC-009

**Version:** 2.0

**Status:** Draft

**Depends on:**

DOC-005
DOC-007
DOC-008
DOC-010
DOC-011
DOC-012
DOC-013

---

# 1. Purpose

This document defines the common architectural rules governing how modules use the project database.

The Database Access Layer is a project-wide architectural contract. It is not necessarily a single software library, although an implementation may provide shared database-access components.

The database is the shared persistence and communication layer between modules.

Modules do not communicate directly with one another. Persistent information exchanged between modules is exchanged through the database.

---

# 2. Design Philosophy

Every module is independently executable.

Modules do not call other modules, exchange process memory or use temporary files as an application-level communication channel.

The normal model is:

```text
Module A
    ↓
Database
    ↓
Module B
```

A module reads relevant existing information, performs its own work and writes the results belonging to its own responsibility back to the database.

This allows modules to be executed in different orders and at different times without creating a process-level pipeline.

The Scanner is a foundational exception in the sense that a file normally must first have a valid database identity before other modules can analyse it. This is a data prerequisite, not a requirement that Scanner remain running or that it run immediately before another module.

---

# 3. Database Responsibilities

The database stores persistent project state such as:

* file identity and filesystem metadata;
* analysis results;
* classification results;
* module execution records;
* user decisions;
* review information;
* file history;
* collection/root context where required by the logical schema.

Application and module configuration is managed through DOC-008 and collection-definition documents rather than being duplicated as unrelated module-owned configuration inside the database.

The exact logical schema is defined by DOC-005.

---

# 4. Communication Model

A module normally follows:

```text
Read relevant database state
        ↓
Perform module-specific work
        ↓
Write module-owned results/state
        ↓
Continue or finish execution
```

Modules do not:

* invoke another module directly;
* exchange application-level memory;
* exchange temporary files as a substitute for database communication;
* assume that another module process is currently running.

A module may of course use ordinary operating-system facilities, filesystem access, GPU resources, libraries and other technical dependencies required for its own operation.

---

# 5. Data Categories

The database contains several logical categories of information.

## File Facts

Objective or filesystem-derived information such as:

```text
SHA512
file size
modification time
image dimensions
extension
current path
```

File identity rules are defined by DOC-012.

## Analysis Results

Results produced by analysis modules, such as:

```text
IRL
Screenshot
Reaction
B&W / Color
Cosplay
Universe
Character
Theme
```

Analysis results may be probabilistic and may change when module, rule or model versions change.

## User Decisions

Information explicitly confirmed, rejected, modified or deferred by the user.

Examples include:

```text
manual classification
manual destination
accepted review decision
rejected suggestion
deferred review
```

User decisions take precedence over automatic suggestions for the applicable protected decision context.

## History

Historical information such as module executions and file events preserves how the current state was reached.

---

# 6. Reading Policy

Before processing a file, a module should read relevant information already stored in the database.

Existing valid results should be reused when appropriate to avoid unnecessary work.

A module may use results produced by another module when those results are part of its documented input.

For example:

```text
Universe Analysis
        ↓
Database
        ↓
Character Analysis
```

Character Analysis may use Universe candidates stored in the database, but it does not depend on the Universe Analysis process being active.

Absence of an optional analysis result must be handled according to the module specification rather than assumed to be an application-wide error.

---

# 7. Writing and Ownership Policy

Each module owns the persistent results belonging to its documented responsibility.

Examples:

```text
Scanner
    file discovery / filesystem synchronization state

Universe Analysis
    universe analysis results

Character Analysis
    character analysis results

Theme Analysis
    theme analysis results
```

A module must not silently overwrite another module's results.

User decisions are not module-owned analysis results and must not be overwritten merely because a later automatic execution disagrees with them.

Shared infrastructure entities are maintained by the components responsible for them according to the project architecture.

---

# 8. Incremental Saving

Long-running modules should persist successful work incrementally.

Example:

```text
File A
  ↓
Analyse
  ↓
Save valid result
  ↓
Continue

File B
  ↓
Analyse
  ↓
Save valid result
```

The project must not require an entire multi-million-file execution to finish before successful results become persistent.

Incremental persistence also supports recovery after interruption.

---

# 9. Failure Recovery

If processing stops unexpectedly, successfully committed results must remain valid.

Example:

```text
1000 eligible files
        ↓
999 successfully processed
1 failed
```

The results for the 999 successful files remain available.

A later execution may process the remaining file according to its current state.

Individual module transaction boundaries are defined by the module and database implementation, but failure handling must not unnecessarily discard unrelated successful work.

---

# 10. Memory and Working Cache

Modules may use RAM as working memory.

The objective is not to minimise memory usage regardless of performance. The objective is to use available resources efficiently while maintaining system stability.

Modules may use:

* processing batches;
* database caches;
* inference batches;
* worker queues;
* temporary decoded images;

provided that resource limits are respected.

The entire image collection must not be loaded into memory for ordinary processing.

The database remains the persistent source of shared state. Temporary caches may be discarded and rebuilt.

---

# 11. Transactions and Persistence

The architecture does not require long-running global transactions covering an entire module execution.

Short atomic database operations are preferred where practical.

Each committed result should become available to later module executions without requiring the producing module to remain active.

Modules must follow database integrity rules and must not leave invalid partial records presented as valid completed results.

---

# 12. Performance Guidelines

Where practical, modules should:

* use indexed database fields;
* read only required columns/data;
* batch compatible writes;
* avoid unnecessary UPDATE operations;
* reuse valid existing analysis results;
* process large collections incrementally.

Performance optimisation must not compromise database consistency, file identity or user decisions.

---

# 13. Multiple Independent Executions

A module may be executed many times independently of other modules.

For example, the following is valid:

```text
Day 1:
IRL Analysis × 1

Day 3:
IRL Analysis × 1
Screenshot Analysis × 2

Day 7:
IRL Analysis × 1
B&W Analysis × 10
```

Each run has its own Module Execution record.

The fact that one module was executed several times does not impose any execution count or schedule on another module.

A later execution reads the database state as it exists at that time.

---

# 14. Concurrency

The project is designed primarily for a single interactive user.

Complex multi-user locking is not a core requirement.

However, modules must still prevent unsafe concurrent operations where simultaneous execution could corrupt data or cause conflicting filesystem changes.

The required protection should be proportional to the risk and may be implemented through execution checks, locks, or module-specific safeguards.

---

# 15. Schema Compatibility

Modules should verify that the database schema is compatible with the module version before performing operations that depend on specific structures.

An incompatible schema should cause a clear failure rather than silent corruption or interpretation of fields according to an obsolete model.

Database schema and migration rules belong to the database architecture/implementation documentation, not to individual analysis modules.

---

# 16. Database Errors and Logging

Database-related failures must be logged according to DOC-011.

Examples include:

* failed connection/open;
* failed read;
* failed write;
* integrity violation;
* incompatible schema;
* transaction failure;
* unexpected database lock/contention.

Successful high-volume operations should not produce excessive logs unless verbose logging is enabled.

---

# 17. Review and User Decisions

Review Queue and user decisions are database-backed shared information.

A module may create a Review Queue item when its own specification determines that user intervention is required.

The module must not interpret the existence of a Review item as permission to modify the filesystem.

Likewise, a user decision recorded in the database must be treated as authoritative for its decision context unless the user later changes it.

---

# 18. Filesystem and Database Relationship

The database stores the known current state of files, but the filesystem remains the physical storage layer.

A filesystem operation is not considered successfully represented in the database until the operation has succeeded and the resulting state can safely be recorded.

This is particularly important for modules such as Scanner and AutoSort.

Modules must use SHA512/file identity rules from DOC-012 rather than assuming that a filesystem path alone identifies a file.

---

# 19. Architectural Principles

The Database Access Layer follows these principles:

* one shared database for shared persistent project knowledge;
* no direct module-to-module application communication;
* modules are independently executable;
* Scanner establishes the database identity of newly discovered files;
* later modules may operate in arbitrary order according to their own documented data requirements;
* modules persist their own results and expose them to other modules through the database;
* user decisions take precedence over automatic suggestions;
* successful work should survive interruption;
* memory usage should be performance-oriented but bounded by system stability;
* performance optimisation must not compromise consistency.

---

# 20. Acceptance Criteria

The Database Access Layer is correctly implemented when:

* modules communicate shared persistent information through the database;
* modules do not invoke one another directly;
* newly discovered files become available to other modules after Scanner has established valid file identity;
* modules can be executed repeatedly and in different orders;
* completed work remains persistent after interruption;
* modules modify only data within their documented ownership;
* user decisions are not silently overwritten;
* the database remains consistent after successful operations;
* the architecture scales to multi-million-file collections without requiring the entire collection in memory.

---

# End of DOC-009
