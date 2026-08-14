# DOC-001

# Project Specification

**Project:** AI Image Collection Management System

**Document:** DOC-001

**Version:** 2.0

**Status:** Draft

---

# 1. Purpose

This document defines the high-level purpose, architecture and operating principles of the AI Image Collection Management System.

The system is an offline-first, modular application designed to assist with the organization and maintenance of very large collections of digital images.

The project is intended for collections containing millions of files and therefore prioritizes stability, predictable behaviour, incremental processing and user control over maximum automation.

This document defines the project-level architecture. Detailed definitions of shared mechanisms, database structures, module interfaces, collection configuration and individual modules belong to their respective documents.

---

# 2. Project Scope

The system is intended to:

* scan very large image collections;
* maintain a database representing known files and their analysis state;
* calculate and maintain file identity information;
* perform modular image analysis;
* identify possible classification errors;
* prepare files for further processing;
* assist the user with organizing files into configured collection trees;
* support controlled movement and renaming operations;
* maintain the collection without requiring permanent Internet access.

The application is not intended to be a general-purpose image management platform.

It is designed around configurable collections and a modular processing architecture.

---

# 3. Core Design Principles

## 3.1 Modularity

Each module shall have a clearly defined responsibility.

A module should not silently perform responsibilities belonging to another module.

For example:

```text
Scanner
    scans files and maintains file inventory

Analysis Module
    analyses files and records results

AutoSort
    evaluates existing analysis results and performs configured sorting operations

Renamer
    performs configured filename operations
```

Shared behaviour should be defined by common standards rather than duplicated independently in every module.

---

## 3.2 Offline-First Operation

The system shall be capable of operating without a permanent Internet connection.

The core system must not require:

* cloud services;
* online APIs;
* permanent Internet access;
* remote processing services.

AI models used by the system shall be capable of running locally.

Internet access may be used for optional development, acquisition or maintenance activities where explicitly supported, but it must not be a runtime requirement for the core collection-processing workflow.

---

## 3.3 User Control

The system assists the user; it does not replace the user's authority over the collection.

Automatic processing may make classifications and operational decisions only within the rules and permissions defined by the project configuration.

Manual user decisions have priority over automatic decisions.

A manual correction must not later be silently overwritten by an automatic classifier or sorter.

---

## 3.4 Safety

The system shall avoid unintended modification of user data.

Operations capable of modifying files shall be governed by the applicable module specification and configured directory access policy.

A module must not infer permission to modify a directory merely from its physical path or name.

Operations involving already organized collection trees require particular care because historical classification errors may exist and may need correction.

---

## 3.5 Database-Centred Architecture

The database is the system's authoritative source for file identity, analysis results, processing state and other persistent system information defined by the database architecture.

Physical directory names and paths are not file identities and must not be used as the sole basis for identifying files.

The database and the physical filesystem must remain synchronized according to the rules defined by the relevant specifications.

---

## 3.6 Incremental Development

The system is intentionally developed as a collection of independent modules and standards.

A completed module should provide useful functionality without requiring all future modules to exist.

Later modules extend the system rather than invalidating the usefulness of earlier completed work.

---

# 4. Collection Model

A Collection is a configured set of physical directory trees and rules that together define how the system processes and organizes a particular image collection.

The physical location of a tree is configurable.

The system must not rely on hard-coded paths or on directory names such as `TODO`, `AI` or `FINAL` to determine the role of a directory.

A configured tree has a logical role and an access policy defined by the collection configuration.

The detailed representation of a Collection Definition is specified by DOC-302.

---

# 5. Collection Tree Roles

The project recognizes several logical roles for collection trees.

## 5.1 Source / Input Trees

Source trees contain files that may enter the processing workflow.

A collection may define one or more source trees.

Source trees may represent:

* incoming material;
* existing unsorted collections;
* legacy collections;
* other user-defined sources.

The user may configure whether a source tree is scanned recursively and what operations are permitted for it.

A source tree may provide files for the transition area or, where explicitly permitted by collection configuration, for a final tree.

---

## 5.2 Transition Tree

The project uses a transition area as a working area for files undergoing classification, AI-assisted processing or manual correction.

The transition area is commonly referred to as the `AI` tree in project discussions, but the physical directory name is configurable.

The transition tree is not a final collection tree.

It may contain files that:

* require further analysis;
* have been assigned a provisional classification;
* were removed from an existing final tree because a possible classification error was detected;
* require manual review;
* are being used as a working set for AI models.

The transition tree may therefore contain subdirectories corresponding to provisional or proposed classifications.

For example:

```text
AI
└── Ben 10
    └── image.jpg
```

The presence of a file in such a directory does not by itself constitute a final classification.

---

## 5.3 Final Trees

Final trees contain files that the user has reviewed and accepted as part of the organized collection.

The final collection is divided into four conceptual top-level trees:

```text
Anime
Monster Girls
Western Animation
Themes
```

`Western Animation` is a conceptual/project placeholder name. The physical directory name used by a real collection is configurable.

These four trees represent the current organizational model of the project and are not required to have fixed physical paths or fixed directory names.

The internal hierarchy of each final tree is configurable according to the collection definition.

Final trees are considered authoritative organized collection areas, but they are not immutable. Historical classification errors may exist and may need correction.

A file may therefore be deliberately removed or relocated from a final tree through a controlled user-approved operation.

---

# 6. Primary Final Tree Model

The four current final trees do not represent four equivalent analysis classifiers.

The primary classification trees are:

```text
Anime
Monster Girls
Western Animation
```

`Themes` is a valid final destination used when a file cannot be meaningfully accommodated by the primary collection trees according to the collection's organization rules.

Themes is therefore a fallback organizational tree, not an error state.

For example, a file that cannot be sensibly classified into the primary trees may be organized under:

```text
Themes
├── Bikini
├── Christmas
├── Halloween
└── School Uniform
```

The exact theme hierarchy is configurable.

The system must not assume that a file belongs in `Themes` merely because automatic classification failed. A file may remain in the transition area or return to a source/TODO area when no suitable final destination has been established.

---

# 7. Final Tree Classification Concepts

The primary final trees may use different internal classification models.

Examples include:

```text
Anime
└── Universe
    └── Character (optional)
```

```text
Monster Girls
└── Species
```

```text
Western Animation
└── Universe
```

These are architectural examples of the current organization model, not fixed physical directory structures.

A collection definition may enable or disable additional classification levels where supported.

The project does not require every final tree to use the same analysis modules or hierarchy.

---

# 8. Processing Flow

The general processing model is:

```text
Source / Input Trees
        ↓
   Processing / Analysis
        ↓
Transition Tree (AI workspace)
        ↓
User review / correction
        ↓
Final Tree
```

A file may also return to a source/TODO area when no suitable final destination has been established.

Files may originate from existing final trees when validation detects a possible classification error. Such files must be handled according to the controlled review and correction mechanisms rather than being silently relocated by an analysis module.

The exact processing flow of an individual module is defined by that module's specification.

---

# 9. Analysis and Sorting Separation

Analysis modules determine or record information about files.

Sorting components use existing database information and collection configuration to determine permitted operations.

The architecture should keep these responsibilities separate.

For example:

```text
Universe Analysis
        ↓
Database
        ↓
AutoSort
        ↓
Configured destination
```

An analysis module should not move files merely because it has produced a classification result unless its own specification explicitly includes such an operation and the operation is permitted by the collection configuration.

Likewise, AutoSort must not invent classification results that have not been established by analysis or user input.

---

# 10. Manual Correction and User Authority

The user may manually correct automatic classification.

Manual correction has priority over automatic classification.

When a user moves a file from the transition area into a final tree, the database shall record that the relevant classification or decision was established manually.

Automatic processing must respect the resulting manual state and must not repeatedly move the file according to a conflicting automatic result.

Manual overrides may be associated with the relevant classification or decision rather than necessarily disabling every future analysis of the file.

For example, a user may manually establish the Universe classification while still allowing independent analysis of other properties.

The exact representation of manual decisions is defined by the database and analysis specifications.

---

# 11. Review and Correction Workflow

The project uses Review Queue concepts for cases where an automatic process cannot safely make a final decision or where an existing classification may be incorrect.

Review does not imply that the system must automatically move the file to the suggested destination.

A possible workflow is:

```text
Existing classification
        ↓
Possible error detected
        ↓
Review / transition workspace
        ↓
User decision
        ↓
Manual classification / destination
```

For files originating from final trees, the system must preserve the original final location until a controlled operation is explicitly authorized.

The transition workspace may contain a provisional folder corresponding to the system's suggested classification. The user remains free to place the file somewhere else.

---

# 12. File Identity

A physical file is identified primarily by its binary content through the project's SHA512-based file identity model.

A database `file_id` provides the internal persistent database identifier.

Paths and filenames may change without creating a new file identity when the binary content remains unchanged.

If binary content changes and therefore produces a different SHA512 value, the system treats the result as a new file according to DOC-012.

The detailed file identity rules are defined by DOC-012.

---

# 13. Supported Environment

The initial target environment is:

```text
Operating System:
    Windows 10 / Windows 11

Primary language:
    Python

Primary database:
    SQLite

Execution:
    Local workstation

Internet:
    Not required for core operation

GPU:
    Optional

CPU execution:
    Supported
```

The architecture should avoid unnecessary dependencies on specific hardware.

GPU acceleration may be used where supported, but lack of a suitable GPU must not make the core system unusable.

---

# 14. Supported Image Formats

The initial supported image formats are:

```text
JPG
JPEG
PNG
WEBP
BMP
GIF
PNS
```

`PNS` should be handled as a PNG-compatible format whenever technically possible.

Video files are outside the image-processing scope and should normally be ignored:

```text
MP4
WEBM
AVI
MKV
```

Additional formats may be supported in the future.

An unsupported or unreadable file should not cause processing of the entire collection to fail.

---

# 15. AI Architecture

AI is an optional processing capability, not a prerequisite for basic system operation.

The system must be able to perform basic scanning, database management and non-AI analysis without AI services.

AI models are expected to run locally when used by the project.

AI processing is intended to be modular so that different models or analysis methods can be introduced without redesigning the complete application.

The transition/AI tree acts as a working area for AI-assisted processing and manual correction.

The exact model selection, confidence thresholds and reprocessing rules are defined by the relevant analysis module specifications and configuration.

---

# 16. Memory and Performance Philosophy

The project is intended to process millions of files and therefore performance is a significant architectural concern.

Modules should use available system resources intelligently.

The objective is not minimum resource consumption at all costs, but a practical balance between performance and system stability.

Modules should use additional RAM, CPU resources or GPU resources when this provides a meaningful performance benefit and remains within configured or system safety limits.

The system must avoid uncontrolled resource exhaustion.

---

# 17. Error Handling and Safety

A failure affecting one file should not unnecessarily terminate processing of the remaining collection.

Modules should record failures in the appropriate logs and, where applicable, Review Queue or database state.

The system must not invent file identity information when checksum calculation fails.

Operations that modify files must validate their preconditions before execution and must respect configured access policies.

The project must favour predictable failure and user visibility over silent recovery that could alter collection contents incorrectly.

---

# 18. Extensibility

The architecture must permit future collection structures and modules without requiring hard-coded knowledge of specific physical paths.

Future collection trees may be introduced through configuration where the relevant module capabilities support them.

Future analysis modules may introduce additional classification dimensions.

The existence of the current four final trees does not prevent the architecture from supporting future collection structures, but any change to the project's established final-tree model must be explicitly incorporated into the project specification and collection configuration rules.

---

# 19. Initial Development Direction

The initial development effort is focused on establishing reliable infrastructure before introducing increasingly complex AI classification.

The general development direction is:

```text
Database / storage foundations
        ↓
Scanner
        ↓
Basic image analysis
        ↓
Screenshot / reaction / IRL analysis
        ↓
Universe analysis
        ↓
Character / theme analysis
        ↓
Sorting and maintenance refinement
```

The exact implementation order is not a global runtime dependency. Modules are user-initiated and may be executed when their documented prerequisites are satisfied.

---

# 20. Project Success Criteria

The project is considered successful when it materially reduces the amount of manual work required to organize and maintain the collection while remaining predictable and safe.

Perfect automatic classification is not required.

The system should allow errors to be corrected efficiently and should preserve those manual corrections.

Stability, traceability and user control are more important than achieving maximum automation at the cost of unpredictable behaviour.

---

# 21. Related Documentation

The following documents define detailed aspects of the architecture:

```text
DOC-000    Documentation Standards
DOC-002    Database Architecture Specification
DOC-003    System Architecture
DOC-007    Module Execution Engine
DOC-008    Configuration Manager
DOC-010    Module Interface Specification
DOC-011    Logging Standard
DOC-012    File Identity Model / Specification
DOC-013    Review Queue Specification
DOC-301    Collection Definition Wizard
DOC-302    Collection Definition Format
```

The exact responsibility of each document is defined by the current documentation set.

---

# 22. Acceptance Criteria

This project specification is considered complete when:

* the project's high-level purpose is clearly defined;
* the system is explicitly offline-first;
* module responsibilities are separated;
* the database-centred architecture is established;
* source, transition and final tree roles are defined without hard-coded physical paths;
* the current four final-tree model is documented;
* Themes is correctly defined as a fallback final tree rather than an error state;
* final trees are recognized as user-accepted but not immutable;
* manual corrections have priority over automatic results;
* AI is treated as an optional local capability and working area rather than a prerequisite;
* detailed implementation rules remain in their responsible documents;
* the specification does not contradict the shared architectural standards.

---

# End of DOC-001
