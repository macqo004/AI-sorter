# DOC - 000

# Documentation Standards

**Project:** AI Image Collection Management System

**Document:** DOC-000

**Version:** 2.1

**Status:** Draft

---

# 1. Purpose

This document defines the standards governing the project's technical documentation.

Its purpose is to keep the documentation consistent, maintainable and understandable as the project evolves, while avoiding unnecessary duplication and fragmentation.

DOC-000 defines how documentation is structured, numbered, maintained, updated and cross-referenced. It does not define the system architecture itself.

---

# 2. Scope

This standard applies to all project documentation, including:

* project and architecture specifications;
* database documentation;
* shared system standards;
* module specifications;
* collection and configuration documentation;
* maintenance documentation;
* future project extensions.

Discussion and design work may take place outside the official documentation. Only the project documents stored in the repository constitute the maintained technical documentation set.

---

# 3. Documentation Language

Official technical documentation shall be written in English.

Design discussions, comments, commit messages and development conversations may use other languages.

Terminology should remain consistent across the documentation regardless of the language used during project discussions.

---

# 4. Document Identity and Numbering

Each document has a unique permanent document identifier.

Examples:

```text
DOC-000
DOC-005
DOC-101
DOC-301
```

Document numbers are never reused for a different purpose.

A document may be renamed or consolidated during documentation refactoring, but its document identifier remains associated with its logical subject whenever practical.

The authoritative list of existing documents is maintained as part of the project documentation set. New document numbers must not be invented or assigned solely because a number is unused.

---

# 5. Number Allocation

The project uses logical number ranges:

```text
000–099    Core documentation, architecture and shared standards
100–199    Analysis and analysis-related modules
200–299    Processing, automation and operational modules
300–399    Collection management and configuration
400–499    Validation and maintenance
```

These ranges are organizational conventions, not restrictions on the internal architecture.

Additional ranges may be introduced if the project requires them.

---

# 6. Document Structure

The exact structure depends on the purpose of the document.

A document should normally contain, where applicable:

* title;
* project name;
* document identifier;
* version;
* status;
* purpose;
* scope;
* definitions or terminology;
* architecture or technical specification;
* functional rules;
* safety and error handling;
* integration with other components;
* logging;
* configuration;
* acceptance criteria;
* future extensions.

Not every document needs every section. Sections should be included when they provide useful information for the subject being documented.

A document should describe the complete responsibility of its subject rather than splitting closely related information into unnecessary auxiliary documents.

---

# 7. Document Granularity

Documentation should be divided according to logical responsibility rather than according to individual features or paragraphs.

As a general rule:

> One document should describe one logical component, standard or architectural subject.

A module normally requires one document. A second document may be created when the module contains a substantial, independently maintained area such as a rule language, data format or configuration specification.

Additional documents should only be introduced when the separation provides a practical maintenance benefit.

A document must not be created merely because a new subsection has been added to an existing specification.

Shared behaviour used by multiple modules should normally be defined once in a shared standard instead of being duplicated in individual module documents.

---

# 8. Single Source of Truth

Each architectural rule, interface, definition or mechanism should have one authoritative location in the documentation.

Other documents may summarize or reference that rule, but should not independently redefine it unless the difference is intentional and explicitly stated.

For example:

```text
DOC-010
    Module interface contract

DOC-011
    Logging standard

DOC-012
    File identity model

DOC-013
    Review Queue
```

A module document should describe how the module uses these standards, not reproduce their complete definitions.

---

# 9. Cross-References

Documents may and should reference other project documents when responsibilities overlap.

References should use document identifiers rather than repository file names.

Example:

```text
Conforms to: DOC-010
References: DOC-012, DOC-013
```

Cross-references should point to the document that owns the relevant rule rather than duplicating that rule.

When a document is renamed, consolidated or replaced, affected cross-references should be reviewed and corrected.

---

# 10. Versioning and Revisions

Each maintained document contains its own version number.

Version numbers describe the state of the document, not the Git history.

Minor changes may increment the minor version:

```text
1.0 → 1.1
1.1 → 1.2
```

A substantial restructuring or architectural rewrite may increment the major version:

```text
1.x → 2.0
```

However, a new version number does **not** normally require creating a separate file.

The canonical document should normally remain in one file and be updated in place.

Git history is the authoritative record of previous contents and provides the historical record of changes.

Separate files such as:

```text
DOC-101 v1.1 – Scanner Module Update.md
```

should not be created merely to record an update to an existing document.

A separate document is justified only when the new document represents a genuinely independent specification or historical artifact whose continued existence has a practical purpose.

---

# 11. Documentation Refactoring

Existing documentation may be substantially rewritten when architectural understanding improves.

Refactoring may include:

* consolidating multiple documents with overlapping responsibilities;
* moving a rule to the document that is its proper owner;
* removing obsolete requirements;
* correcting terminology;
* resolving contradictions;
* restructuring sections for clarity;
* incorporating the contents of historical update documents into the current canonical document.

When documents are consolidated, the resulting document should become the single current source of truth.

Historical versions remain available through Git history and do not need to remain as separate active documentation files.

Refactoring must not silently discard an established architectural decision. If a decision is intentionally changed, the change should be explicitly identified during the design process.

---

# 12. Document Status

Recommended document statuses are:

```text
Draft
Review
Approved
Deprecated
```

**Draft** indicates that the document is actively being developed.

**Review** indicates that the document is complete enough for architectural or technical review but has not yet been accepted as the current standard.

**Approved** indicates that the document is the current accepted specification.

**Deprecated** indicates that the document is retained for historical or compatibility reasons but is no longer the current source of truth.

A document under active architectural refactoring should normally be marked Draft or Review until the new version is accepted.

---

# 13. Section Numbering

Section numbers should be stable during ordinary maintenance.

During a substantial document rewrite, section structure may be reorganized or renumbered when this materially improves clarity. Such changes do not require preserving obsolete section numbers merely for historical reasons.

References to section numbers in other documents should be avoided when possible. Cross-references should normally point to the document identifier and, where necessary, the named section rather than relying on a permanently fixed section number.

---

# 14. Terminology and Naming

The same concept shall use the same terminology throughout the project documentation.

Different names must not be introduced for the same concept unless the distinction is intentional.

Document titles should clearly describe their subject.

Examples:

```text
Scanner Module
Universe Analysis Module
Database Maintenance
Configuration Manager
Review Queue Specification
```

Project terminology defined by the relevant architectural or terminology document takes precedence over informal wording.

When a new architectural decision changes terminology, affected documents should be updated as part of the same documentation refactoring effort.

---

# 15. Technical Detail

Documentation should describe:

* responsibilities;
* behaviour;
* interfaces;
* data and state relevant to the specification;
* constraints;
* safety rules;
* dependencies;
* expected interactions.

Implementation details should be documented when they are necessary to define correct behaviour or interoperability.

Implementation details that are purely incidental to the current implementation should normally remain in source code or developer documentation.

The goal is not to hide implementation details, but to prevent the architectural specification from becoming dependent on unnecessary implementation choices.

---

# 16. Examples

Examples should be used whenever they make a rule easier to understand or remove ambiguity.

Examples must not silently become additional requirements.

When an example is illustrative rather than normative, it should be clear from the surrounding text that it is an example.

---

# 17. Requirements, Decisions and Proposals

Documentation should distinguish between:

* established requirements;
* established architectural decisions;
* implementation rules;
* examples;
* proposed or future functionality.

A proposal must not be presented as an existing requirement.

Future extensions should be clearly identified as such.

When an architectural decision is not yet finalized, the document should use wording such as:

```text
Proposed
Future
Under consideration
```

rather than presenting it as mandatory system behaviour.

---

# 18. Compatibility and Breaking Changes

New documentation should remain compatible with established architecture whenever practical.

Compatibility must not be preserved at the cost of maintaining an obsolete or contradictory design indefinitely.

When a new architectural decision intentionally changes an existing requirement, the affected documents should be updated so that the current documentation describes one coherent architecture.

The old behaviour remains available through Git history unless it is separately required for operational or compatibility reasons.

---

# 19. Legacy Documentation

Older documents may contain decisions that were valid at the time they were written but are no longer part of the current architecture.

Historical documents and historical versions are preserved by the repository history.

They are not automatically considered current specifications.

A document that has been superseded should either be consolidated into the current document or explicitly marked Deprecated when it must remain as a separate artifact.

The project should avoid maintaining multiple active documents that describe different versions of the same architectural rule.

---

# 20. Documentation and Git History

Git is used to preserve documentation history.

The current contents of a project document represent the current specification. Previous versions can be recovered from repository history when necessary.

Documentation files therefore do not need to be duplicated solely to preserve previous revisions.

Commit messages should identify the architectural or documentation change clearly enough to make the repository history useful during later review.

---

# 21. Documentation Stability

Core architectural documents should change less frequently than module documents, but stability does not mean that known architectural errors should remain uncorrected.

Changes should be driven by:

* new requirements;
* discovered design problems;
* clarified architectural decisions;
* removal of obsolete assumptions;
* improvements necessary to maintain consistency between documents.

Changes should not be introduced solely for stylistic reasons.

---

# 22. Third-Party Components and Licensing Documentation

The project should minimize unnecessary use of third-party copyrighted or otherwise protected material when doing so does not materially harm the project's functionality, maintainability or safety.

Third-party material may be used when its licence or another applicable legal basis clearly permits the intended use, including free use where relevant. The fact that a component is free to download or use does not by itself establish that it may be redistributed, modified or bundled with this project.

This principle applies, as applicable, to:

* source code and libraries;
* Python packages;
* machine-learning models and model weights;
* datasets and sample data;
* images, icons and other graphics;
* fonts;
* bundled runtimes and native libraries;
* executable utilities and other external components.

Before a third-party component becomes part of the project or its distributed application package, the project should record at least:

```text
component name
source
version
licence / usage terms
intended use
redistribution requirements where applicable
```

When the licence permits use but imposes attribution, notice, redistribution or source-disclosure requirements, those obligations must be preserved in the appropriate project or distribution documentation.

A component with unclear, missing or incompatible licensing terms should not be adopted merely because it is technically convenient. A functionally useful alternative with clearer permissible licensing should be preferred where practical.

This section defines a documentation and governance rule. Detailed implementation packaging requirements are defined by DOC - 016.

---

# 23. Acceptance Criteria

The documentation standard is considered satisfied when:

* each document has a clear responsibility;
* document numbers are unique and stable;
* the active documentation has one coherent architectural model;
* shared rules have a single authoritative definition;
* terminology is consistent;
* cross-references are maintained;
* obsolete specifications are not presented as current requirements;
* documentation is detailed enough to implement and maintain the system without unnecessary duplication;
* Git history preserves previous document versions;
* third-party components used by the project have their relevant licence information documented;
* the number of documents remains manageable as the project grows.

---

# End of DOC-000
