# DOC-109

# Set Detection and Grouping Module

**Project:** AI Image Collection Management System

**Document:** DOC-109

**Module:** Set Detection and Grouping

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

The Set Detection and Grouping module identifies groups of visually related image files and represents those groups as logical **Sets** in the database.

The purpose of grouping is to provide later analysis modules with an optional higher-level analysis unit when processing related files together can improve efficiency or classification quality.

A Set is a database concept. Set detection does not itself determine Universe, Character or Theme classification and does not decide the final physical destination of files.

---

# 2. Scope

The module may:

* analyse visual similarity between eligible files;
* identify groups of related files;
* create and update Set records;
* associate files with Sets;
* provide grouped context to later modules through the database.

The module shall not:

* identify characters as its primary responsibility;
* identify universes as its primary responsibility;
* identify themes as its primary responsibility;
* decide final collection placement;
* silently replace user decisions;
* invoke another module directly.

---

# 3. Definition of Set

A Set is a logical group of files that share a sufficiently strong documented relationship for later processing to benefit from treating them together.

A Set does not automatically mean:

* the same character;
* the same universe;
* the same artist;
* the same source;
* identical files.

Possible Set relationships include:

```text
expression variations
pose/view variations
related artwork variants
closely related image series
other visually meaningful groups
```

Visual similarity alone is not sufficient when the images do not form a useful logical group.

---

# 4. Examples

Possible valid Set:

```text
furina_smile.jpg
furina_angry.jpg
furina_surprised.jpg
furina_happy.jpg
```

Possible invalid Set:

```text
furina.jpg
ben10.jpg
sonic.jpg
random_landscape.jpg
```

The fact that images share colours, composition or general rendering style is not sufficient evidence of a meaningful Set.

---

# 5. Module Independence

Set Detection is independently executable once eligible files have valid database identities.

Scanner must discover files before they can participate in normal Set processing, but Scanner does not need to be running while Set Detection executes.

Set Detection does not invoke Universe Analysis, Character Analysis, Theme Analysis or any other module directly.

Later modules may consume Set information from the database.

For example:

```text
Set Detection
      ↓
Database
      ↓
Universe Analysis
```

is a database-level data dependency, not a process dependency.

---

# 6. Input

The module reads the current database state for eligible files and may access the corresponding images from the filesystem when visual comparison is required.

Required identity information includes:

```text
SHA512
file metadata
image dimensions where available
```

Existing analysis results may be consumed as supporting information when configured, but Set Detection must not depend on another module process being active.

---

# 7. Output

The module creates or updates logical Set information in the shared database.

A Set should have at least:

```text
set_id
status
created_at
updated_at
```

A Set membership record should associate:

```text
set_id
file identity / file_id
membership status
similarity or membership score where applicable
```

The exact physical database schema is defined by DOC-005.

Set membership is database state; a folder name is not the identity of a Set.

---

# 8. Set Identity

`set_id` is the internal logical identity of a Set.

A physical folder name, path or automatically assigned number is not the permanent identity of a Set.

A Set may change physical location, folder name or membership without changing its `set_id`.

This is analogous to the project's file identity model: filesystem representation must not be confused with logical identity.

---

# 9. Set Membership

A file may belong to one Set or multiple Sets only where the module's grouping model explicitly allows overlapping groups.

The initial implementation should prefer one primary membership unless overlapping membership provides a clear practical benefit.

A membership has its own state and may become invalid or superseded as grouping results change.

Set Detection must not use Sets to overwrite file identity or other module classifications.

---

# 10. Relationship with Analysis Modules

Sets are an optional higher-level processing context.

A later module may choose to analyse:

```text
individual file
```

or, where supported:

```text
complete Set
```

This is a module-level processing decision.

Set Detection does not require every downstream module to use Sets.

A module must not assume that every file belongs to a Set.

---

# 11. Set-Level Analysis

When a downstream module supports Set-level processing, the Set may provide evidence such as:

* repeated visual identity;
* common poses or expressions;
* consistent presentation;
* repeated costume or source characteristics;
* shared contextual information.

Set-level evidence is supporting information and must not be treated as proof of Universe, Character or Theme by Set Detection itself.

A downstream classification module remains responsible for its own classification result.

---

# 12. Set Storage and AI Workspace

Sets are logical database objects and do not require a dedicated physical folder.

If an authorised workflow chooses to expose Sets physically in the AI/transition workspace, it may create a Set workspace directory according to the configured rules.

For example:

```text
AI/Sets/0001/
AI/Sets/0002/
```

Such directories are workspaces, not FINAL collection definitions.

AI workspaces may be created dynamically where the applicable configured workflow permits it.

Set Detection must not create new FINAL directories.

---

# 13. Folder Naming

If a physical AI Set workspace uses automatically assigned names, the naming convention is implementation/configuration data rather than Set identity.

A numeric format such as:

```text
0001
0002
0003
```

may be used for readability.

The database `set_id` remains authoritative.

The module must not assume that the numeric folder name uniquely defines the Set.

---

# 14. Set Creation

A new Set may be created when the module determines that a group of files meets the configured grouping criteria.

Creation thresholds should be configurable.

The module should retain enough evidence to explain why the files were grouped.

A Set should not be created merely because two images happen to share generic visual properties such as colour palette or aspect ratio.

---

# 15. Set Merging

The module may identify that two existing Sets represent the same logical group.

A merge should require sufficient evidence under configured rules.

Examples of strong merge evidence may include:

* identical or near-identical source relationships;
* very high visual similarity combined with consistent contextual evidence;
* confirmed duplication of the same logical group.

Similarity alone is not automatically equivalent to logical identity.

Where confidence is insufficient, the proposed merge should enter Review Queue.

---

# 16. Set Splitting

A Set may later be split when analysis determines that its members do not form one coherent group.

Automatic splitting should be conservative.

When a split is ambiguous or could materially change user organisation, Review Queue should be used.

Set splitting must preserve file identity and the historical Set relationship where required for traceability.

---

# 17. Review Queue Integration

The module may create Review Queue cases for:

* uncertain Set creation;
* uncertain Set merge;
* uncertain Set split;
* conflicting grouping evidence;
* cases where the system cannot safely determine whether two groups should be combined.

Review Queue decisions are user decisions and take priority over later automatic suggestions for the protected context.

The module must not execute an uncertain merge merely because a suggestion exists.

---

# 18. Processing Rules

Set Detection may be executed repeatedly and independently.

A previous valid Set result should normally be reused when still applicable.

Reprocessing may be triggered by:

* new files entering the processing scope;
* changes to file identity caused by a SHA512 change;
* module version changes;
* similarity/model/rule changes;
* explicit user or reprocessing request;
* changes to existing Set membership that invalidate earlier grouping decisions.

A filename or path change without a SHA512 change does not by itself create a new binary file identity or require a new Set identity.

---

# 19. Database Access

The module reads:

```text
File
Module
existing Set data
relevant Analysis Results where configured
```

The module writes:

```text
Set
Set membership
Module Execution state
appropriate File Events where explicitly required
```

It must not overwrite other modules' analysis results or user decisions.

Persistent information exchange with other modules occurs through the shared database.

---

# 20. Performance and Resource Usage

Set Detection may be computationally expensive because pairwise comparison does not scale linearly with collection size.

The implementation should therefore use scalable strategies such as:

* staged similarity filtering;
* inexpensive pre-filtering before expensive comparison;
* batch processing;
* configurable worker count;
* persistent intermediate results where useful;
* limited candidate comparisons rather than all-to-all comparisons.

The module should use available resources efficiently without exhausting configured system limits.

The entire collection must not be required in RAM.

---

# 21. Threading

Parallel execution should be supported.

Worker count shall be configurable through the common module interface/configuration system.

Concurrent workers must not create conflicting Set state or duplicate Set creation for the same evidence group.

---

# 22. Error Handling

If processing of an individual file or candidate relationship fails:

* the error shall be logged;
* unrelated work should continue where safe;
* incomplete Set membership should not be published as valid final state.

An execution-level database or consistency failure may stop the execution when continuing would risk corrupting Set state.

---

# 23. Logging

Each execution shall create a Module Execution record and summary log according to DOC-007 and DOC-011.

The summary should include where applicable:

```text
started
finished
files considered
sets created
sets updated
memberships added
memberships removed
merges proposed/accepted
splits proposed/accepted
errors
duration
```

---

# 24. Interaction with AI and FINAL

Set Detection may support the AI/transition workflow by providing logical groups for later inspection and classification.

AI may contain Set workspaces even when equivalent structures do not exist in FINAL.

FINAL remains user-defined and must not be extended automatically by Set Detection.

A later authorised processing workflow may move files or complete Set workspaces into an existing valid primary collection destination according to Collection Definition, access policy and user decisions.

Set Detection itself does not determine that destination.

---

# 25. Design Principles

The module follows these principles:

1. Grouping is an analysis aid, not semantic classification.
2. Visual similarity is not automatically semantic identity.
3. Set identity is stored in the database, not in folder names.
4. Files retain their SHA512-based identity independently of Set membership.
5. Sets may change as evidence improves.
6. Uncertain merges and splits should be reviewed rather than guessed.
7. Modules consuming Sets remain independent processes and communicate through the database.
8. AI workspaces may be dynamic; FINAL structure remains controlled by Collection Definition.

---

# 26. Acceptance Criteria

The module is considered compliant when it can:

* identify meaningful groups of visually related files;
* store Set identity and membership in the database;
* support repeated independent execution;
* preserve file identity independently of Sets;
* provide optional grouped context to downstream modules;
* support conservative merge and split operations;
* use Review Queue for materially uncertain grouping decisions;
* support AI workspace grouping without creating arbitrary FINAL directories;
* operate efficiently enough for multi-million-image collections;
* maintain database consistency after successful writes.

---

# End of DOC-109
