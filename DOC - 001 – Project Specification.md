# DOC - 001 – Project Specification

**Project:** AI Image Collection Management System  
**Document:** DOC - 001  
**Version:** 3.0  
**Status:** Design Specification

---

# 1. Purpose

This document defines the high-level purpose, architecture and operating principles of the AI Image Collection Management System.

The system is an offline-first, modular application intended to assist with organizing and maintaining very large image collections.

The project is designed for millions of files and therefore prioritizes stability, incremental processing, traceability and user control over maximum automation.

Detailed mechanisms belong to their responsible documents.

---

# 2. Scope

The system is intended to:

* scan configured image collections;
* maintain a database of known binary identities and physical locations;
* calculate and maintain SHA512 identity;
* perform independent image-analysis modules;
* support semantic classification and review;
* organize files into user-defined collection trees;
* support controlled move and rename operations;
* operate without permanent Internet access.

---

# 3. Core Principles

## 3.1 Modularity

Each module has a defined responsibility.

Modules do not communicate directly with other project modules. Persistent information exchanged between modules is exchanged through the shared database.

## 3.2 Offline-First

The core collection workflow must operate without permanent Internet access.

Local AI models may be used where applicable. Online services are optional and must not be required for normal collection processing.

## 3.3 User Authority

The system assists the user but does not replace the user's authority over the collection.

Protected manual decisions take priority over later automatic suggestions for the affected decision context.

## 3.4 Safety

Filesystem modification requires explicit permission from the applicable collection access policy and the module specification.

FINAL is protected against uncontrolled automatic modification but is not assumed to be permanently correct.

## 3.5 Database-Centred State

The database is the shared persistent state layer for file identity, physical-location state, analysis results, classifications, user decisions and selected history.

Filesystem paths are state, not binary identity.

## 3.6 Incremental Processing

Modules may be executed repeatedly and independently. Work already committed successfully must survive unrelated later failures.

---

# 4. Collection Model

A Collection is a configured set of filesystem roots and rules.

The physical paths and roles are user-defined through Collection Definition. The system must not infer role from names such as `TODO`, `AI` or `FINAL`.

A configured root has a logical role and an access policy.

Detailed Collection Definition semantics belong to DOC - 301 and DOC - 302.

---

# 5. Logical Collection Roles

The architecture recognizes these configurable roles:

```text
PRIMARY
THEME_FALLBACK
TODO
AI
IMPORT_SOURCE
```

The physical names of these roles are configurable.

### PRIMARY

A main user-organized collection tree.

A project may contain any number of independent PRIMARY trees.

Examples from the current collection may include:

```text
Anime
Monster Girls
Western Animation
```

These names are examples, not global constants.

### THEME_FALLBACK

A fallback organization tree used when no suitable higher-priority PRIMARY destination is currently available.

All configured PRIMARY trees have higher organizational priority than THEME_FALLBACK.

### TODO

A processing/source workspace containing files that remain eligible for classification or other processing.

### AI

A dynamic transition/workspace area.

AI may contain newly discovered universes, characters, Sets or other workspaces that have no corresponding PRIMARY destination.

AI workspace expansion does not modify approved PRIMARY structure.

---

# 6. Primary versus Theme Organization

The current organizational rule is:

```text
configured PRIMARY destination
        ↓
THEME_FALLBACK
        ↓
remain in current valid workspace / review
```

Theme is not a peer classification category to PRIMARY trees.

A file may initially be stored in Theme fallback and later be promoted into a PRIMARY tree when a valid higher-priority destination becomes available.

The exact destination hierarchy is defined by Collection Definition and AutoSort.

---

# 7. Final Collection Behaviour

A configured PRIMARY or THEME_FALLBACK location represents approved final organization.

Final organization is user-curated but not immutable.

A file may later prove to be incorrectly placed and may be moved out through a controlled Review Queue/user-decision workflow.

Analysis modules must not autonomously rewrite FINAL merely because a model disagrees with the current placement.

---

# 8. AI Workspace Behaviour

AI is a working area, not a final collection.

An authorized workflow may create AI directories when configured criteria are satisfied, including a minimum population/count threshold for a newly detected universe.

Example:

```text
TODO
    ↓
Universe Analysis
    ↓
threshold exceeded for a new universe
    ↓
AI/Ben 10/
```

The corresponding PRIMARY destination does not have to exist.

The user may later move the files or complete AI directory to an existing valid final destination.

---

# 9. Classification Boundaries

Collection Definition defines Classification Boundaries that prevent user-managed subdirectories from being interpreted as additional semantic levels.

Example:

```text
PRIMARY/Anime/Genshin Impact/Furina
        ← classification boundary
        ├── 0001
        ├── 0002
        └── Favorites
```

`0001`, `0002` and `Favorites` are physical organization below the boundary and must not automatically become classifications.

Set directories follow this rule.

---

# 10. Processing Architecture

The system is not a single mandatory pipeline.

A conceptual workflow is:

```text
Source / TODO
        ↓
Scanner
        ↓
Database
        ↓
Independent Analysis Modules
        ↓
Database
        ↓
Review / AutoSort / other authorised operations
        ↓
AI / PRIMARY / Theme / TODO
```

The arrows describe data flow, not mandatory runtime ordering.

Outside the Scanner's data-ingestion prerequisite, modules can be executed in arbitrary order when their required database data exists.

---

# 11. Analysis and Sorting Separation

Analysis modules produce information.

AutoSort and other authorised processing components use that information to determine permitted physical operations.

Analysis does not automatically grant filesystem modification authority.

---

# 12. Manual Correction

When a user explicitly corrects a classification or destination, that decision becomes authoritative for the affected context.

The correction is stored in the database and protected from automatic overwriting.

A manual correction to one classification does not automatically disable unrelated analysis.

---

# 13. Review Queue

DOC - 013 defines the common Review Queue mechanism.

Review may be represented in the database, through a text report, or through the AI workspace when that is the appropriate physical review mechanism.

There is no separate Migration Queue architecture.

---

# 14. File Identity

Binary content identity is SHA512 according to DOC - 012.

The logical database model is:

```text
File
    = one SHA512 identity

FileLocation
    = one physical occurrence
```

Multiple physical locations with identical SHA512 represent the same binary content.

---

# 15. Supported Environment

Initial target environment:

```text
Windows 10 / Windows 11
Python
SQLite
Local workstation
Optional GPU
CPU-supported operation
No permanent Internet requirement
```

The architecture should avoid unnecessary coupling to one specific hardware configuration.

---

# 16. Supported Images

Initial image formats:

```text
JPG
JPEG
PNG
WEBP
BMP
GIF
PNS
```

Known video and archive formats are outside the normal image-processing scope and should be ignored unless a future module explicitly supports them.

An unsupported or unreadable file must not terminate processing of the entire collection merely because it is present.

---

# 17. Resource Philosophy

The project targets millions of files.

Modules should use available CPU, memory and GPU resources efficiently while respecting configured/system safety limits.

The entire image collection must not normally be loaded into memory.

---

# 18. Error Handling

Per-file failures should be isolated wherever safe.

Successful work must not be rolled back merely because an unrelated later file fails.

Unsafe or ambiguous filesystem operations should become visible to the user rather than silently guessing.

---

# 19. Extensibility

New modules and collection structures may be introduced through the existing shared architecture and configuration mechanisms.

The current example PRIMARY trees do not constrain the number or names of future PRIMARY trees.

A genuinely new cross-module mechanism should be documented once in its shared specification rather than duplicated across modules.

---

# 20. Project Success Criteria

The system succeeds when it materially reduces manual collection-management work while remaining predictable and safe.

Perfect automatic classification is not required.

The system should make mistakes easy to detect and correct and should preserve those corrections.

---

# 21. Related Documentation

```text
DOC - 000  Documentation Standards
DOC - 002  Database and Project Storage Architecture
DOC - 003  System Architecture
DOC - 005  Database Schema
DOC - 007  Module Execution and Architecture
DOC - 008  Configuration Manager
DOC - 009  Database Access Layer
DOC - 010  Module Interface Specification
DOC - 011  Logging Standard
DOC - 012  File Identity Model
DOC - 013  Review Queue
DOC - 014  Module Result Lifecycle and Cleanup
DOC - 301  Collection Definition Wizard
DOC - 302  Collection Definition Format
```

---

# 22. Acceptance Criteria

DOC - 001 is consistent when:

* the system is explicitly offline-first;
* modules are independent and communicate through the database;
* Scanner is the base file-ingestion prerequisite;
* SHA512 is the binary-content identity;
* FileLocation represents physical occurrence;
* collection roots and roles are configuration-driven;
* any number of PRIMARY trees may exist;
* Themes is a fallback below all PRIMARY trees;
* AI may dynamically expand as a working area;
* FINAL structure is user-defined and not autonomously expanded by analysis;
* Classification Boundaries prevent Set/user folders from becoming semantic classifications;
* manual decisions override automatic suggestions for their protected context.

---

# End of DOC - 001
