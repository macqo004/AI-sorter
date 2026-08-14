# DOC-006

# Terminology and Naming Conventions

**Project:** AI Image Collection Management System

**Document:** DOC-006

**Version:** 2.0

**Status:** Draft

**Depends on:**

DOC-000
DOC-001
DOC-002
DOC-003
DOC-005
DOC-010
DOC-012
DOC-013

---

# 1. Purpose

This document defines the common terminology used throughout the project.

Its purpose is to ensure that the same concept is described by the same name in architecture documents, module specifications, database structures, configuration and source code.

DOC-006 defines terminology. It does not introduce system functionality.

Where another document is the authoritative owner of a concept, DOC-006 provides the terminology used to refer to that concept but does not redefine its complete technical specification.

---

# 2. General Principles

The following principles apply throughout the project:

* one concept should have one official name;
* different concepts should not use the same official name;
* terminology should remain stable once established;
* internal technical names are written in English;
* user-interface text may be translated;
* informal names may be used during discussion, but official documentation should use the defined terminology;
* a term must not imply behaviour that the architecture does not require.

---

# 3. File

**File** is the primary term for a file known to the system.

A File represents the binary object tracked by the framework together with the persistent identity and current filesystem state defined by DOC-012 and DOC-005.

File identity is independent of:

* filename;
* directory;
* collection tree;
* classification;
* analysis results.

A rename or move therefore does not by itself create a different File.

A change of binary content resulting in a different SHA512 is handled according to DOC-012.

The term **Image** may be used when discussing the visual content represented by a File, but `Image` is not a separate primary database entity unless a future specification explicitly introduces one.

---

# 4. File Identity

**File Identity** is the identity of a tracked binary object.

Its authoritative rules are defined by DOC-012.

The project uses:

```text
file_id
SHA512
```

as the fundamental identity information.

Filename and path are filesystem attributes, not identity.

---

# 5. Analysis Result

**Analysis Result** is information produced by an analysis module about a File.

Examples include:

```text
BW = true
IRL = false
SCREENSHOT = true
COSPLAY = false
```

An Analysis Result may include a confidence value and the version of the module that produced it.

Analysis Result is the current project term for what earlier documentation called an **Observation**.

The old term should not be used for new documentation unless explicitly discussing historical material.

Analysis results are not user decisions and are not filesystem metadata.

---

# 6. Analysis Feature

An **Analysis Feature** is the type of information produced by an analysis.

Examples:

```text
BW
IRL
SCREENSHOT
COSPLAY
REACTION
```

Feature names should be short, descriptive and stable.

The database representation of an analysis feature is defined by DOC-005.

---

# 7. Classification

**Classification** is the process of assigning semantic meaning to a File.

Examples include:

```text
Universe
Character
Theme
Set
```

Classification is represented by **Classification Results** in the database.

Classification is distinct from objective or visual Analysis Results, although a classification module may use analysis results as input.

---

# 8. Classification Result

A **Classification Result** is a semantic classification assigned to a File.

A Classification Result identifies at least:

* classification type;
* value;
* source;
* creation time;
* optionally confidence and producing module.

Possible sources include:

```text
AI
USER
IMPORTED
```

A user-created or user-confirmed classification has priority over an automatic classification for the same classification context unless the user later changes or removes that decision.

The detailed Review Queue and manual-correction rules are defined by DOC-013.

---

# 9. Manual Correction

**Manual Correction** is a user action that intentionally changes or confirms the classification or processing state of a File in a way that must take precedence over an automatic decision.

A manual correction is persistent project information, not merely a temporary UI action.

Automatic processing must not silently undo a protected manual correction.

The scope of protection is determined by the affected classification or decision. A manual correction to one classification does not automatically prohibit unrelated analysis.

---

# 10. Module

A **Module** is an independent executable component of the system with a defined responsibility.

Examples include:

```text
Scanner
Color Analysis
Monochrome Analysis
Screenshot Analysis
Reaction Image Analysis
IRL Analysis
Cosplay Analysis
Universe Analysis
Character Analysis
Theme Analysis
File Renamer
Database Maintenance
```

A module may read shared database information and write the results for which it is responsible.

Modules communicate primarily through the shared database rather than through undocumented temporary files.

Module responsibilities and interfaces are governed by DOC-010 and the individual module specifications.

---

# 11. Module Execution

**Module Execution** is one execution instance of a Module.

It was previously called **Job** in older documentation.

Module Execution records execution state and statistics. It does not represent a File.

Typical states include:

```text
RUNNING
COMPLETED
CANCELLED
FAILED
```

The logical database representation is defined by DOC-005.

---

# 12. File Event

A **File Event** is a historical record describing an important operation or state transition affecting a File.

Examples include:

```text
SCANNED
MOVED
RENAMED
MOVED_TO_AI
MOVED_TO_FINAL
RETURNED_TO_TODO
USER_CORRECTED
ARCHIVED
DELETED
```

File Events describe history. They do not replace the current-state fields maintained by the database.

The project does not require pure event sourcing.

Historical event records should not be rewritten merely to make past events match the current state.

---

# 13. Tag

A **Tag** is a generic semantic label that may be assigned to a File independently of the physical collection tree.

Examples include:

```text
Christmas
Halloween
School Uniform
Bikini
Beach
Night
Rain
```

Tags may be multiple per File.

A Tag is not automatically equivalent to a folder name, classification or Theme.

In particular, the `Themes` final collection tree is a collection-organization concept and must not be assumed to be the same thing as the database Tag system.

---

# 14. Collection

A **Collection** is a configured set of filesystem roots and associated rules representing one managed image collection.

Collection configuration is defined by DOC-301 and DOC-302.

A Collection is a logical configuration object. Its physical paths are not fixed by this document.

---

# 15. Collection Root

A **Collection Root** is a configured filesystem root belonging to a Collection.

A Collection Root has a configured role and access policy.

Examples of logical roles include:

```text
SOURCE
TRANSITION
FINAL
```

These are logical roles, not required directory names.

The physical path, recursive behaviour, enabled state and access policy are defined by the collection configuration.

---

# 16. Source / Processing Tree

**Source** is a logical role for a root containing files that are available for processing.

The project has historically used the term **TODO Tree** for this role.

`TODO` may continue to be used as a user-facing or informal name, but official architecture should prefer the configured logical role where a specific physical directory name is not relevant.

A Source root may contain files awaiting initial processing or files deliberately returned for further processing.

---

# 17. Transition Workspace

**Transition Workspace** is a logical role for a root used as an intermediate working area during classification and manual organization.

The project has historically used **AI Tree** or **AI** for this role.

AI is therefore a convenient project name, not a requirement that every file in the workspace has been classified by an AI model.

The workspace may contain files such as:

```text
AI/Ben 10/example.jpg
```

where the directory structure represents a proposed or working classification.

A Transition Workspace is not a final collection.

---

# 18. Final Collection

A **Final Collection** is a user-curated collection tree that represents an accepted organization of files.

Final Collections are normally treated as protected against unsolicited modification, according to their configured access policy.

However, a Final Collection is not assumed to be permanently correct.

A file may later be identified as incorrectly classified and may be moved out of the Final Collection as part of a controlled correction workflow.

The final trees and their physical paths are defined by collection configuration rather than hard-coded project terminology.

---

# 19. Primary and Fallback Final Trees

The current collection model distinguishes between primary final trees and a fallback thematic tree.

The project currently uses concepts corresponding to:

```text
Anime
Monster Girls
Western Animation
Themes
```

The first three are examples of primary final-tree categories. `Western Animation` is a conceptual placeholder and is not required to be the user's physical directory name.

`Themes` is a fallback final-tree category for files that cannot be meaningfully accommodated by the applicable primary trees.

These names are examples of the user's current collection organization. They are **not hard-coded global categories** and must not be placed in the general system architecture as mandatory values.

---

# 20. Review Queue

**Review Queue** is the common mechanism for cases that require a user decision because automatic processing cannot safely determine the correct action.

Review Queue is defined by DOC-013.

A Review Queue item may concern:

* classification;
* file movement;
* ambiguous analysis;
* filesystem problems;
* other decisions explicitly assigned to the review mechanism.

The Review Queue does not itself move files.

A review decision may result in an operation such as:

```text
ACCEPT
REJECT
MODIFY
DEFER
```

The actual consequence may be movement of the File to an appropriate Final Collection or back to a Source/processing tree.

There is no separate Migration Queue in the current architecture. A proposed migration is handled as a Review Queue decision.

---

# 21. Confidence

**Confidence** is a numeric indication of how strongly a module supports an automatic result.

The conventional range is:

```text
0.0 – 1.0
```

Higher values indicate greater confidence.

Confidence is meaningful only where the producing module defines how it is calculated.

A confidence value does not override an explicit user decision.

---

# 22. Access Policy

**Access Policy** defines what a module is permitted to do with a configured Collection Root.

The currently defined policy concepts are:

```text
PROTECTED
READ_ONLY
MODIFY
PLAYGROUND
```

The detailed policy is defined by the dedicated Directory Access Policy specification when established.

A physical directory name must never be used as a substitute for an access policy.

---

# 23. Feedback

**Feedback** is information derived from user actions that may be useful for future processing or analysis.

Examples include:

* manually correcting a classification;
* moving a File to a different classification tree;
* returning a File to a Source tree;
* explicitly accepting or rejecting an automatic result.

Feedback is not automatically equivalent to a permanent training label. Its later use must be explicitly defined by the relevant analysis or learning specification.

---

# 24. Lifecycle State

**Lifecycle State** is the current database state of a File record.

The currently recognized states include:

```text
ACTIVE
MISSING
ARCHIVED
DELETED
```

Lifecycle state describes the existence and database status of the File record. It does not describe its collection classification.

Detailed lifecycle rules are defined by DOC-012 and database-maintenance specifications.

---

# 25. Current State and History

The project distinguishes between:

**Current state** — information needed to operate on the File now.

**History** — information describing what happened previously.

Current state is stored in the appropriate current database entities.

History is represented where required by File Events and superseded analysis or classification results.

The project does not require every state change to be reconstructed from an event stream.

---

# 26. Naming Conventions

The project uses the following conventions for internal identifiers.

### Database tables and logical entities

Use singular PascalCase when referring to logical entities in documentation:

```text
File
Module
ModuleExecution
AnalysisResult
ClassificationResult
FileEvent
Collection
CollectionRoot
ReviewItem
```

The exact physical SQL naming convention may be defined separately by the implementation specification.

### Database fields

Use a consistent machine-readable naming convention defined by the database implementation. Existing logical names include:

```text
file_id
sha512
current_path
module_id
execution_id
classification_id
```

The logical documentation does not require PascalCase database columns.

### Feature and classification types

Use stable uppercase identifiers where machine-readable values are required:

```text
BW
IRL
SCREENSHOT
UNIVERSE
CHARACTER
THEME
SET
```

### Module names

Module names should be human-readable English names:

```text
Scanner
Universe Analysis
File Renamer
Database Maintenance
```

---

# 27. Deprecated Terms

The following terms belong to older versions of the architecture and should not be introduced into new documentation without a specific reason:

| Old term | Current term |
|---|---|
| Image as primary database entity | File |
| Observation | Analysis Result |
| Feature/Value as a universal model | Analysis Result / Classification Result, according to context |
| Job | Module Execution |
| AI Tree as a mandatory directory | Transition Workspace / configured root role |
| TODO Tree as a mandatory directory | Source / processing root |
| Final Library as one fixed tree | Final Collection / configured Final roots |
| Migration Queue | Review Queue |

Historical documents may retain these terms when their original wording is relevant.

---

# 28. Terminology Ownership

The document that defines a mechanism in detail remains its authoritative specification.

For example:

```text
DOC-012 → File Identity
DOC-013 → Review Queue
DOC-010 → Module Interface
DOC-011 → Logging
DOC-301 → Collection Definition Wizard
DOC-302 → Collection Definition Format
```

DOC-006 provides common names for these mechanisms but does not replace their detailed specifications.

If two documents appear to define conflicting meanings for the same term, the conflict must be resolved during documentation refactoring rather than allowing two meanings to remain active.

---

# 29. Project Terminology Principles

The project follows these principles:

* one official term per concept;
* physical paths are not architectural concepts unless explicitly configured as such;
* user-facing names and logical roles are distinct;
* automatic results and user decisions are distinct;
* current state and history are distinct;
* analysis and classification are distinct where their semantics differ;
* user decisions have higher priority than automatic decisions;
* shared mechanisms should be defined once and referenced elsewhere;
* terminology should remain understandable to a technically competent user;
* terminology should reflect the actual architecture rather than historical implementation details.

---

# End of DOC-006
