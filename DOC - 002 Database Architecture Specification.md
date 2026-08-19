# DOC - 002

# Database and Project Storage Architecture

**Project:** AI Image Collection Management System

**Document:** DOC-002

**Version:** 2.0

**Status:** Draft

**Depends on:** DOC-001 Project Specification

**Related:** DOC-012 File Identity Model, DOC-013 Review Queue, DOC-301 Collection Definition Wizard, DOC-302 Collection Definition Format

---

# 1. Purpose

This document defines the architecture of the project database and its relationship with the physical image collection.

The database is the central persistent state and coordination layer. The filesystem contains the actual image data. The database records file identity, current filesystem state, analysis results, classification state, user decisions and relevant history.

This document consolidates the former database architecture and project storage model. It defines the storage model at architectural level; concrete paths and user configuration belong to Collection Definition.

Detailed tables, columns, indexes and SQL constraints belong to the database schema documentation.

---

# 2. Design Goals

The architecture shall be:

* fully usable offline;
* lightweight and portable;
* resilient against failures;
* capable of handling millions of image records;
* straightforward to back up and restore;
* independent of permanent Internet access;
* extensible without redesigning the core model for every new module;
* independent of hard-coded directory names and paths.

---

# 3. Database Engine

SQLite is the selected engine for the initial implementation.

Reasons include zero server configuration, single-file storage, Python support, transactions, portability and suitability for a large offline desktop application.

Application architecture should avoid unnecessary coupling to SQLite-specific behaviour so that migration to another SQL engine remains possible if future requirements justify it.

---

# 4. Database as the Application State Layer

The database is the authoritative source for recorded application state and facts.

Physical directory names must not be application logic. Modules must not contain assumptions such as:

```text
if directory == "AI"
if directory == "FINAL"
```

Collection roots, their logical roles and access policies are supplied by configuration.

A path is a property of the current filesystem state of a file, not its identity.

The database does not replace the filesystem: the filesystem remains the location of the actual image bytes.

---

# 5. File Identity

Each active file has a permanent internal `file_id`.

Detailed identity rules are defined by DOC-012. At this architectural level:

* filename does not define identity;
* path does not define identity;
* moving a file does not create a new identity;
* renaming a file does not create a new identity;
* a changed binary object with a different SHA512 is handled according to DOC-012.

Modules should use `file_id` as their primary database relationship rather than paths.

---

# 6. SHA512

SHA512 is the project's primary binary-content identifier.

It supports identification and comparison of file contents, detection of moved or renamed files, association of analysis with a binary object, detection of content changes and validation of pending user decisions.

A failed checksum operation must never produce an invented or placeholder hash. It is an error condition handled by the relevant module and logging/review mechanisms.

Detailed SHA512 and content-change rules belong to DOC-012.

---

# 7. Separation of Responsibilities

The database stores state and facts. Modules perform analysis and operations.

No module owns the database as a whole. A module should update only data belonging to its responsibility and must not overwrite another module's result merely because it accesses the same file.

Examples:

```text
Scanner
    file discovery
    filesystem metadata
    identity information

Color / Monochrome Analysis
    colour-related classification

Screenshot Analysis
    screenshot classification

Universe Analysis
    universe classification

Character Analysis
    character classification

Theme Analysis
    theme classification

Renamer / File Operations
    filename and location state

Database Maintenance
    lifecycle and maintenance operations
```

The exact database fields and ownership are defined by the schema and module specifications.

---

# 8. Logical Database Areas

The database may be understood as these logical areas:

```text
File Identity
      ↓
Filesystem State
      ↓
Analysis Results
      ↓
Classification / Sorting State
      ↓
User Decisions and Overrides
      ↓
History / Audit Information
```

These are logical responsibilities, not necessarily separate SQLite databases or tables.

---

# 9. Project Storage Model

The project has three principal logical working roles:

```text
SOURCE / TODO
      ↓
AI / WORKSPACE
      ↓
FINAL COLLECTION
```

These are **logical roles**, not mandatory directory names.

The user may define the physical paths and the number of roots through Collection Definition. A role may therefore contain multiple configured roots.

The system must never require literal directories named `TODO`, `AI` or `FINAL`.

---

# 10. Source / TODO

Source/TODO contains files available for processing that have not reached accepted final organization, including:

* newly discovered files;
* files awaiting analysis;
* files requiring reprocessing;
* files manually returned for processing;
* unresolved files that the user does not yet want in FINAL.

TODO is not required to become empty. Files may remain there indefinitely.

Its physical paths and subdirectory structure are configuration, not application logic.

---

# 11. AI / Working Area

AI is a working and transitional area used by automated processing and user-assisted classification. It is not a final collection.

AI may contain automatically organized proposals or files requiring further user review. Its structure may mirror relevant portions of the configured FINAL collection.

Example:

```text
AI
└── Ben 10
    └── image.jpg
```

This means that `Ben 10` is currently a proposed or working classification. It is not a final user decision.

AI can also be used to isolate a file found in an incorrect FINAL location:

```text
FINAL/Winx Club/image.jpg
            ↓
AI/Ben 10/image.jpg
```

The user may then place the file into any appropriate FINAL or TODO location. The name of the AI directory is not proof that the suggested classification is correct.

Information that must survive regeneration of AI must be stored in the database, not inferred solely from the current AI directory.

---

# 12. FINAL Collection

FINAL represents the user's accepted, organized collection.

FINAL is **not immutable**. A file may be incorrectly classified and must be capable of being moved or removed as part of a controlled user-approved correction.

Automated analysis must not silently move a FINAL file merely because a model disagrees with its current location. A detected possible error is handled through the Review Queue and the controlled user-decision mechanism.

Therefore FINAL is:

* authoritative as the user's accepted organization;
* protected against uncontrolled automation;
* subject to explicit user-approved correction;
* not a permanently read-only filesystem area.

---

# 13. FINAL Collection Trees

FINAL consists of configurable Collection Trees rather than one mandatory directory structure.

The current conceptual collection includes trees such as:

```text
Anime
Monster Girls
Western Animation
Themes
```

These are examples of the current collection design, not hard-coded system requirements. The actual names and paths are defined by Collection Definition.

`Themes` has a specific current role: it is a fallback organizational tree for material that cannot appropriately be placed into the principal collection trees. It is not a mandatory fourth classification category for every file.

Additional Collection Trees may be added without changing the database architecture.

---

# 14. Database and Filesystem Relationship

The filesystem and database provide different information:

```text
FILESYSTEM
    actual image bytes
    current physical paths
    filenames

DATABASE
    file identity
    recorded filesystem state
    analysis results
    classification state
    user decisions
    history
```

The database does not assume that a stored path is permanent.

The filesystem remains authoritative for whether the actual file exists at a particular location. Modules must reconcile filesystem observations with database state rather than treating a stale path as proof that the file still exists there.

---

# 15. User Decisions and Manual Corrections

User decisions are persistent application state.

A manual classification must be distinguishable from an automatic result.

A manual correction has priority over later automatic results for the same classification unless the user explicitly changes or removes the manual decision.

This prevents a later model run from silently undoing a deliberate correction.

A manual correction may apply to one classification dimension without disabling independent analysis. For example, manually correcting Universe does not necessarily disable Theme Analysis.

The exact representation of manual overrides belongs to the database schema and Review Queue specifications.

---

# 16. Review Queue Integration

Uncertain cases are handled by the Review Queue defined by DOC-013.

Review Queue is a logical mechanism, not necessarily a separate service or physical queue directory.

Depending on the case, review information may be represented through database state, a text/report file, or placement of a file into an appropriate AI workspace.

The essential rule is:

> An automatic prediction does not become a final decision merely because a module produced it.

The user's decision becomes authoritative.

No separate Migration Queue is required by this architecture. Migration/correction cases are user decisions handled through the Review Queue mechanism.

---

# 17. Logical Data Flow

A typical workflow is:

```text
Filesystem
    ↓
Scanner
    ↓
File Identity / Filesystem State
    ↓
Analysis Modules
    ↓
Database
    ↓
Classification / AutoSort
    ↓
AI Workspace
    ↓
User Decision
    ↓
FINAL or Source/TODO
```

This is a conceptual flow, not a mandatory global execution order. Modules are user-initiated and may operate independently when their prerequisites are satisfied.

The database provides persistent communication between modules instead of requiring temporary inter-module files.

---

# 18. Image Lifecycle

A file may pass through many states without becoming a different file merely because it was renamed or moved.

Typical events include:

* discovered;
* scanned;
* analyzed;
* classified;
* proposed for organization;
* moved;
* renamed;
* manually corrected;
* returned to processing;
* deleted;
* archived from active database state.

Content changes that produce a new SHA512 are handled according to DOC-012.

---

# 19. History

The system should preserve sufficient history to explain important state changes and user decisions.

History should record observable facts rather than inventing causes.

Example:

```text
file_id: 12345
old_path: FINAL/Winx Club/image.jpg
new_path: AI/Ben 10/image.jpg
timestamp: ...
operation: MOVE
```

The record should not claim that a particular model caused the move unless that information is actually known and recorded.

Detailed logging and history rules belong to the relevant standards and maintenance specifications.

---

# 20. Performance and Scale

Initial architectural target:

```text
5,000,000 image records
```

The architecture should remain practical for significantly larger collections; approximately 20 million records is an indicative future target.

Growth should normally be handled through indexes, query optimization, batching, caching or storage configuration rather than conceptual redesign.

---

# 21. Transactions and Failure Isolation

Transactions should be used where atomic consistency between related database changes is required.

A processing run must not unnecessarily depend on one giant transaction if a later unrelated failure would cause successfully processed files to be lost.

For example, a scanner must be able to retain successfully recorded files even if a later file cannot be processed.

Detailed transaction behaviour belongs to individual module specifications.

---

# 22. Backup and Recovery

The database is a critical project asset and must be backed up independently of image files.

A valid database backup must be restorable without requiring a complete collection rescan merely to reconstruct ordinary application state.

Backup scheduling and database maintenance belong to the relevant maintenance documentation.

Image files remain separate assets and require their own backup strategy.

---

# 23. Extensibility

The architecture must support additional modules without redesigning the core database concept.

Possible future capabilities include OCR, wallpaper detection, pose detection, outfit detection, similarity analysis and additional recognition/classification modules.

A new module should normally add or use data belonging to its own responsibility rather than changing the meaning of fields owned by unrelated modules.

---

# 24. Collection Definition Boundary

Database architecture does not hard-code the physical collection layout.

Collection Definition specifies configured roots, logical roles, Collection Trees and associated policies.

DOC-301 defines the Collection Definition Wizard. DOC-302 defines the resulting Collection Definition format.

This separation allows the database architecture to support different physical layouts without changing module logic.

---

# 25. Architectural Rules

1. The database is the central persistent application-state layer.
2. File paths are state, not identity.
3. `file_id` is the primary internal file relationship.
4. SHA512 identifies the binary content for file-identity purposes.
5. Directory names must not be hard-coded into module logic.
6. Source/TODO, AI/Workspace and FINAL are logical roles, not mandatory directory names.
7. AI is a working area and does not constitute final user approval.
8. FINAL is user-curated but not permanently immutable.
9. Automatic processing must not silently override an explicit manual correction.
10. Uncertain decisions are handled through Review Queue.
11. The filesystem stores actual image data; the database stores application state and recorded facts.
12. New modules integrate through the shared database architecture rather than ad-hoc inter-module files.
13. Detailed schema belongs to the database schema documentation.
14. Physical collection configuration belongs to Collection Definition documentation.

---

# 26. Acceptance Criteria

The architecture is considered correctly implemented when:

* millions of files can be represented without directory names defining identity;
* moving or renaming a file does not create a new identity record;
* content changes follow DOC-012;
* modules exchange persistent state through the database;
* collection paths and tree names can be changed without rewriting module logic;
* AI can be used as a working area without becoming the authoritative collection;
* FINAL can be corrected through controlled user decisions;
* manual corrections cannot be silently overwritten by later automatic classification;
* review cases do not require a separate Migration Queue architecture;
* database backups can be restored independently of a complete collection rescan;
* additional modules can be introduced without redesigning the fundamental database architecture.

---

# End of DOC - 002
