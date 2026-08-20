# DOC-003

# System Architecture

**Project:** AI Image Collection Management System

**Document:** DOC-003

**Version:** 2.0

**Status:** Draft

**Depends on:**

DOC-001

DOC-002

DOC-007

DOC-008

DOC-010

DOC-011

DOC-012

DOC-013

---

# 1. Purpose

This document defines the system-level architecture of the application.

It describes how the major parts of the system cooperate and where their responsibilities begin and end.

It does not define the detailed implementation of individual modules, database tables, logging syntax, or collection configuration formats. Those subjects are defined by their respective documents.

---

# 2. Architectural Philosophy

The application follows a modular, database-centered architecture.

The system is intended to operate offline and must not require permanent Internet access for its normal operation.

Modules are independently executable components. They use shared project state rather than depending on direct runtime communication with other modules.

The architecture prioritizes:

* independent modules;
* predictable behaviour;
* user control;
* shared standards;
* database-backed state;
* safe filesystem operations;
* failure isolation;
* extensibility without unnecessary coupling.

---

# 3. Responsibility Boundaries

Each module should have a clearly defined primary responsibility.

A module may perform supporting operations required for that responsibility, but unrelated functionality should not be silently incorporated into the module.

For example:

```text
Scanner
    discovers files and maintains filesystem identity information

Analysis Module
    analyzes files and stores its analysis results

AutoSort
    performs configured classification/sorting operations

Renamer
    performs filename normalization according to its rules

Database Maintenance
    maintains database integrity and performs defined maintenance tasks
```

The detailed responsibility of each component belongs to its own specification.

---

# 4. Shared Database

The database is the primary communication and persistent-state layer of the system.

Modules should normally communicate results through the database rather than through temporary module-specific files.

The general model is:

```text
Module A
    ↓
Database
    ↓
Module B
```

The database stores persistent information such as:

* file identity;
* filesystem state;
* analysis results;
* classification state;
* manual decisions and overrides;
* processing state;
* history required by the relevant specifications.

The database is not a substitute for the filesystem. Image files remain physical filesystem objects and the database records their identity and current state.

---

# 5. Filesystem and Database Relationship

The filesystem is the physical storage layer.

The database is the system's structured representation of the collection and its processing state.

Modules should reason primarily using database records and `file_id`, while the current filesystem path is used when an actual filesystem operation is required.

The filesystem is therefore not treated as a database of classification state.

Changes to files or paths must eventually be reflected in the database according to the relevant module specification.

---

# 6. Module Independence

Modules are started by the user.

There is no requirement for a globally fixed execution sequence.

A module may depend on information produced by another module, but such dependencies should be represented through database state rather than requiring both modules to run simultaneously.

For example:

```text
Scanner
    ↓
Database
    ↓
Universe Analysis
```

The Scanner may finish before Universe Analysis is started.

A module must clearly report that it has started and is working so that the user does not accidentally launch the same operation repeatedly.

The system does not require a global dependency scheduler unless a future specification introduces one.

---

# 7. Module Runtime State

Modules may have temporary runtime state such as:

* active worker threads;
* queues;
* caches;
* loaded models;
* GUI state;
* progress information.

Such runtime state does not constitute authoritative project state.

Persistent project state belongs in the appropriate persistent storage defined by the architecture, primarily the database.

A module must not rely on hidden persistent state that cannot be reconstructed or validated from the project's documented configuration and database state.

---

# 8. Database Writes and Data Ownership

Modules should write only the data that belongs to their defined responsibility.

A module must not overwrite unrelated information merely because it has database access.

The architecture does **not** require all database information to be append-only.

Analysis results may be updated, invalidated or superseded according to the relevant analysis specification.

User decisions and manual overrides have higher authority than automatic results where the relevant classification is concerned.

The exact database ownership and update rules are defined by DOC-002 and the specifications of the individual modules.

---

# 9. Processing Model

The system does not require a single mandatory processing pipeline.

A typical workflow may look like:

```text
Source / TODO
      ↓
Scanner
      ↓
Database
      ↓
Analysis Modules
      ↓
AI / working area
      ↓
User review and correction
      ↓
FINAL or TODO
```

This is a conceptual workflow, not a mandatory execution sequence.

Individual modules may be run independently when their required input state is available.

---

# 10. Collection Trees

Collection trees are logical roles defined by collection configuration. Their physical directory names and locations are not hard-coded by the architecture.

The system may contain, among others:

```text
Source / Input trees
Transition / AI tree
Final trees
```

The exact number and physical location of these trees are defined by the collection configuration.

`TODO`, `AI` and `FINAL` are therefore architectural concepts, not required directory names.

---

# 11. Source / TODO Area

A source or TODO area contains files that remain eligible for processing.

It is not assumed that every collection must use a directory literally named `TODO`.

Files may be analyzed, classified, moved to the AI working area, or placed into a configured final tree according to module rules and user decisions.

---

# 12. AI Working Area

The AI area is a working and transitional area.

It may contain files that:

* require further analysis;
* have been assigned a provisional classification;
* require manual inspection;
* were identified as potentially misplaced in a final tree;
* are being used as a working set for models or the user.

For example:

```text
AI
└── Ben 10
    └── image.jpg
```

The `Ben 10` directory may represent the system's current classification proposal. It is not necessarily the user's final decision.

The AI area may therefore be processed again when the relevant module is run. It is not a permanently excluded area.

---

# 13. Final Areas

Final areas contain files that the user considers organized and accepted as part of the collection.

Final areas are not immutable.

A file may be incorrectly classified and may therefore need to be removed or moved from a final area as part of a controlled user decision.

Modules performing ordinary analysis should not autonomously alter final files merely because they disagree with an existing classification.

A possible error in FINAL should instead enter the project's review/correction workflow.

The system must support controlled correction of final content without treating FINAL as an unrestricted working area.

---

# 14. Final Tree Classification Model

The current collection concept includes multiple final trees whose exact names and locations are user-configurable.

Conceptually, the collection may contain primary trees corresponding to major content categories and a fallback `Themes` tree.

The architecture must not hard-code names such as:

```text
Anime
Monster Girls
Western Animation
Themes
```

These are examples of collection structure, not universal system categories.

In the current project model, a Themes tree may be used when content cannot be sensibly placed in the primary final trees. This rule belongs to collection configuration and classification logic rather than to the filesystem implementation.

---

# 15. Analysis Layer

Analysis modules inspect files and produce structured results in the database.

Examples include:

* Color Analysis;
* Monochrome Analysis;
* Screenshot Analysis;
* Reaction Image Analysis;
* IRL Analysis;
* Cosplay Analysis;
* Universe Analysis;
* Character Analysis;
* Theme Analysis;
* Set Detection and Grouping.

Analysis modules do not automatically gain permission to modify files simply because they produce a classification result.

Filesystem modification is controlled by the relevant operation module and collection access policy.

Analysis results may be consumed by later modules without requiring the producing module to remain running.

---

# 16. Automatic Classification and User Decisions

Automatic classification is advisory or operational according to the specification of the module using the result.

A model result does not automatically override an explicit user decision.

When a user manually corrects a classification, the database must record that manual decision in a form that prevents the corresponding automatic classification from immediately undoing it.

The scope of the manual override should correspond to the affected classification where practical.

For example, correcting a Universe classification does not necessarily disable unrelated Theme or Character analysis.

---

# 17. Review and Correction Workflow

The system uses the Review Queue concept defined by DOC-013 for cases where automatic processing cannot safely make the final decision.

Review does not require a single physical queue implementation.

Depending on the location and type of case, review information may be represented by:

* database state;
* a report or text file containing affected paths;
* a file placed into the AI working area for manual processing.

A file in FINAL that may be incorrectly classified should not be silently moved merely because a module produced a high-confidence result.

The user remains the final authority over the correction.

---

# 18. File Operation Layer

Filesystem-modifying operations are performed only by components that are explicitly permitted to modify files.

Examples include:

* AutoSort;
* File Renamer;
* other future modules explicitly assigned filesystem operations.

An analysis module should not silently perform unrelated filesystem operations.

Before a controlled operation is executed, the relevant module must obey the configured directory access policy and the safety rules of the operation it performs.

---

# 19. Directory Access Policy

Filesystem access is governed by the Directory Access Policy defined by the project's shared architecture.

The policy is attached to configured directories or collection roots rather than being inferred from names such as `TODO`, `AI` or `FINAL`.

The architecture supports policy concepts such as:

```text
PROTECTED
READ ONLY
MODIFY
PLAYGROUND
```

The exact semantics are defined by the dedicated Directory Access Policy specification.

A read-only directory may still be affected by a user-approved controlled operation if the policy and operation mechanism explicitly permit that exception. Ordinary analysis must not interpret such an exception as permission for autonomous modification.

---

# 20. Configuration

Collection configuration and module configuration are separate concepts.

Collection configuration defines things such as:

* collection identity;
* root directories;
* logical roles of roots;
* recursion;
* access policies;
* enabled state;
* collection-specific structure.

Module configuration defines settings specific to the module itself.

A module must not silently modify another module's configuration.

The Configuration Manager is responsible for the mechanisms governing configuration according to DOC-008.

---

# 21. Logging

Each module follows the common Logging Standard defined by DOC-011.

Modules should provide enough information to determine:

* what operation was performed;
* what happened;
* which file or database record was affected where relevant;
* whether an error occurred;
* whether user intervention is required.

The architecture does not require every module to maintain a completely isolated logging system if the common logging standard provides shared infrastructure.

---

# 22. Failure Isolation

Failure of one module must not unnecessarily stop unrelated modules or corrupt the entire project state.

For example:

```text
Reaction Analysis fails
        ↓
Reaction Analysis becomes unavailable
        ↓
Scanner and unrelated analysis modules may continue
```

Modules should therefore perform operations in a way that allows partial progress to remain valid when appropriate.

A failure must not cause already valid database state to be silently discarded.

---

# 23. Memory and Resource Usage

Modules should use available system resources intelligently.

The architecture does not require minimum-memory operation.

A module may use additional RAM, CPU or other resources when doing so provides a meaningful performance benefit, provided that configured and system safety limits are respected.

Resource management details belong to individual module specifications where necessary.

---

# 24. Offline Operation

The core application must be usable without continuous Internet access.

Internet access may be used by optional development, model acquisition, updates or other explicitly supported functions, but ordinary collection management must not depend on a live network connection.

Models and required resources intended for offline operation must be locally available before the corresponding module is run.

---

# 25. Extensibility

New modules should be able to integrate with the system by following the existing shared interfaces, database model and configuration mechanisms.

Adding a new module should not require redesigning unrelated modules.

However, extensibility does not mean that no architectural change will ever be necessary. A new capability may legitimately require a new shared standard when it introduces a genuinely new cross-module concept.

Such a standard should be documented once and reused by affected modules.

---

# 26. Architectural Dependency Model

The architecture is layered by responsibility rather than by a mandatory execution sequence.

A simplified dependency model is:

```text
Collection Configuration
        ↓
Module Configuration / Execution
        ↓
Database + File Identity
        ↓
Analysis / Processing Modules
        ↓
User Decisions
        ↓
Controlled Filesystem Operations
```

Individual modules may depend on specific database state or analysis results, but those dependencies should be documented by the module specification.

---

# 27. Relationship with Other Documents

This document defines system-level architecture.

The main related specifications are:

```text
DOC-001    Project Specification
DOC-002    Database and Storage Architecture
DOC-007    Module Execution Engine
DOC-008    Configuration Manager
DOC-010    Module Interface Specification
DOC-011    Logging Standard
DOC-012    File Identity Model
DOC-013    Review Queue Specification
```

Future shared standards should be referenced here when they become part of the system architecture.

Module-specific behaviour belongs in the corresponding module document.

---

# 28. Architectural Invariants

The following principles are architectural invariants unless explicitly changed by a later approved specification:

1. Modules are independently executable.
2. Persistent project state is database-backed.
3. File identity is independent of filename and path.
4. Collection paths and roles are configuration-driven rather than hard-coded.
5. Analysis results do not by themselves grant filesystem modification authority.
6. User decisions have higher authority than automatic classification for the affected classification.
7. FINAL is protected from autonomous analysis-driven modification but is not immutable.
8. AI is a working area, not a permanently excluded processing state.
9. The system does not require continuous Internet access for normal operation.
10. Shared behaviour should be defined once and reused rather than duplicated across modules.

---

# 29. Acceptance Criteria

DOC-003 is considered architecturally consistent when:

* module responsibilities are clearly separated;
* database and filesystem responsibilities are distinguished;
* collection locations are configuration-driven;
* no processing stage depends on a mandatory global execution sequence;
* AI and FINAL behaviour matches the current collection model;
* user corrections cannot be silently overwritten by automatic classification;
* filesystem modification is governed by explicit permissions and policies;
* failures remain isolated where practical;
* shared standards are referenced instead of duplicated;
* the architecture remains suitable for offline operation and very large collections.

---

# End of DOC-003
