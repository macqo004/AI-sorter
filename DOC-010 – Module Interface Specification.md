# DOC-010

# Module Interface Specification

**Project:** AI Image Collection Management System

**Document:** DOC-010

**Version:** 1.0

**Status:** Design Specification

---

# 1. Purpose

This document defines the standard interface implemented by every module within the AI Image Collection Management System.

The goal is to ensure consistency between existing and future modules while minimizing duplicated design effort.

Every module should conform to this specification unless explicitly documented otherwise.

---

# 2. Design Philosophy

Each module is an independent executable component.

Modules are loosely coupled.

The database is the only communication medium between modules.

A module performs one clearly defined responsibility.

---

# 3. Standard Module Lifecycle

Every module follows the same high-level execution flow.

```text id="6k5qcm"
Start

↓

Load Configuration

↓

Validate Environment

↓

Open Database

↓

Read Required Data

↓

Process

↓

Write Results

↓

Write Log

↓

Exit
```

Modules may omit unnecessary stages, but the overall lifecycle remains the same.

---

# 4. Initialization

During startup, a module should:

* load its configuration;
* verify required directories;
* verify database accessibility;
* verify compatibility with the current database schema;
* prepare internal resources.

---

# 5. Input

A module may obtain data from:

* Configuration Manager;
* Project Database;
* Collection Definition;
* user-selected files or directories.

Modules never obtain data directly from another module.

---

# 6. Output

A module may produce:

* database observations;
* log entries;
* reports;
* generated files;
* exported data.

Modules never write results directly into another module.

---

# 7. Database Ownership

Every module owns only its own observations.

Examples:

Scanner

* SHA512
* file metadata

Universe Analysis

* universe observations

Character Analysis

* character observations

Theme Analysis

* theme observations

A module shall never modify data owned by another module.

---

# 8. Configuration

Every configurable parameter must be obtained from Configuration Manager.

Modules shall not contain hardcoded user settings.

Examples:

* thresholds;
* thread count;
* directories;
* cache size.

---

# 9. Logging

Every module shall generate logs.

Minimum events:

* module started;
* module finished;
* warning;
* error.

Verbose logging is optional.

---

# 10. User Interface

Every module should expose a consistent interface.

Recommended information:

* module name;
* version;
* short description;
* execution status;
* progress indication.

---

# 11. Execution Status

A module should report its current state.

Recommended states:

Idle

Running

Completed

Completed with warnings

Failed

Cancelled

---

# 12. Progress Reporting

Long-running modules should provide progress information.

Recommended methods:

* progress bar;
* percentage;
* processed item count;
* activity indicator.

The goal is to inform the user that the module is actively working.

---

# 13. Error Handling

A module should recover gracefully whenever possible.

Recoverable errors:

* unreadable image;
* corrupted metadata;
* unsupported format.

Fatal errors:

* missing database;
* incompatible schema;
* invalid configuration.

Fatal errors terminate only the current module.

Other modules remain unaffected.

---

# 14. Memory Usage

Modules may use RAM as working memory.

Memory consumption should be adaptive rather than fixed.

Modules should use available RAM when it significantly improves performance while leaving sufficient resources for the operating system.

Modules should avoid retaining unnecessary data after processing.

---

# 15. Parallel Processing

A module may internally use multiple threads.

Thread management is an implementation detail.

The number of worker threads should be configurable.

---

# 16. Restart Behaviour

Modules may be executed repeatedly.

Repeated execution is always initiated by the user.

Modules should not assume they are executed only once.

---

# 17. Dependency Declaration

Every module should document its recommended inputs.

Example:

Scanner

Inputs:

Filesystem

Outputs:

Facts

Universe Analysis

Inputs:

Facts

Outputs:

Universe Observations

Character Analysis

Inputs:

Facts

Universe Observations

Outputs:

Character Observations

This dependency description is informational only.

Execution order is never enforced.

---

# 18. Generated Data

Every module should clearly define:

* which database tables it reads;
* which tables it writes;
* which reports it generates;
* which files it creates.

No hidden side effects should exist.

---

# 19. Module Metadata

Each module should expose basic metadata.

Recommended fields:

* Module Name
* Module ID
* Version
* Description
* Category
* Author (optional)

---

# 20. Categories

Current categories include:

Infrastructure

Analysis

Maintenance

Additional categories may be introduced in future versions.

---

# 21. Extensibility

Adding a new module should require only:

* implementing the module;
* defining its configuration;
* documenting its inputs and outputs.

Existing modules should not require modification.

---

# 22. Design Principles

Every module should:

* perform one responsibility;
* remain independent;
* communicate only through the database;
* support repeated execution;
* generate logs;
* expose execution status;
* respect user decisions;
* follow the common lifecycle defined in this document.

---

# 23. Acceptance Criteria

A module is considered compliant with this specification when:

* it follows the standard lifecycle;
* it uses Configuration Manager;
* it communicates exclusively through the database;
* it logs its activity;
* it reports execution status;
* it documents its inputs and outputs;
* it does not interfere with the internal operation of other modules.


# 24. Applicability

This specification applies to all modules developed after the publication of DOC-010.

Modules documented prior to DOC-010:

DOC-101
DOC-102
DOC-103
DOC-104
DOC-105
DOC-105A
DOC-106
DOC-107
DOC-108
DOC-201
DOC-301
DOC-401

were developed before this specification was formalised.

These modules shall nevertheless be considered compliant with DOC-010, as this document formalises the architectural conventions established during their development.

Future revisions of those documents are not required solely for the purpose of referencing DOC-010.
---

# End of DOC-010
