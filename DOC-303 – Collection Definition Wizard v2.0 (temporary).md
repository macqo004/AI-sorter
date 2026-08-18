# DOC-303

# Collection Definition Wizard – Temporary v2.0 Backup

**Project:** AI Image Collection Management System

**Original document:** DOC-301 – Collection Definition Wizard
**Purpose of this file:** temporary safety copy of the redesigned DOC-301 content
**Status:** Temporary — to be consolidated back into DOC-301

---

# 1. Purpose

Collection Definition Wizard is responsible for creating and maintaining the logical definition of the user's configured collection structure.

The Wizard does not analyse image contents.
It does not perform semantic image classification.
It does not move or rename files.
It does not create FINAL collection directories automatically.

Its purpose is to define, with explicit user control:

* which configured roots form collection trees;
* how those trees are traversed;
* which directories are part of the logical classification structure;
* where classification boundaries occur;
* which directories below those boundaries belong to user-managed organisation;
* which locations are available as valid destinations to other modules.

---

# 2. Source of Collection Definition

Collection Definition is based on directory structure explicitly selected by the user.

For FINAL collection trees, the Wizard uses the existing approved directory structure as its source.

TODO and AI are processing/workspace areas and are not treated as authoritative sources for FINAL collection structure.

The user explicitly selects the roots to configure. The Wizard must not assume that every directory on the machine belongs to the project.

---

# 3. Primary Collection Trees

A project may contain multiple independent primary collection trees.

Examples include:

```text
Anime
Monster Girls
Western Animation
```

These names are examples only and are not hard-coded.

The user may configure any number of primary trees and may choose their physical locations independently.

Theme may also be configured as a separate fallback tree, but it is not treated as a primary tree merely because it exists in the filesystem.

---

# 4. Directory Definition

The generated Collection Definition describes logical structure and access/traversal rules.

It may contain information such as:

```text
collection id
collection name
enabled state
root path
recursive/traversal rules
access policy
classification boundary information
future extensibility fields
```

The definition does not contain image-analysis results.

File identity and analysis results belong to the database.

---

# 5. First Configuration

During initial configuration:

1. The user selects one or more roots.
2. The Wizard inspects the selected directory structures.
3. The Wizard builds a temporary representation.
4. The Wizard presents that representation to the user.
5. The user defines traversal behaviour and Classification Boundaries.
6. The Wizard stores the resulting Collection Definition.

The Wizard does not infer semantic meaning merely from directory names.

---

# 6. Classification Boundary

A Classification Boundary marks the deepest directory that belongs to the logical collection classification structure.

Directories below that boundary belong to user-managed organisation unless separately configured by the user.

Example:

```text
Anime
└── Genshin Impact
    └── Furina          ← Classification Boundary
        ├── 001
        ├── 002
        ├── 003
        └── Favorites
```

The directories `001`, `002`, `003` and `Favorites` must not be interpreted as additional semantic classification levels.

This prevents a Set folder or other user-managed subdirectory from accidentally being treated as a character, universe, theme or other classification level.

---

# 7. Boundary Types

A Classification Boundary may have a configured logical type when the user wishes to identify the role of that level.

Possible types include:

```text
Primary Root
Universe
Character
Species
Theme
Other configured classification level
```

The list is extensible and must not be hard-coded to the examples above.

The boundary type describes the role of the configured directory in the collection structure. It does not itself produce an analysis result.

---

# 8. Traversal Rules

Collection Definition must support explicit traversal behaviour.

Typical rules may include:

```text
THIS DIRECTORY IS A COLLECTION ROOT
CONTINUE TRAVERSAL
STOP AT THIS DIRECTORY
IGNORE THIS BRANCH
```

The exact internal representation is implementation-defined.

The important rule is that modules must not assume that every subdirectory is a semantic classification level.

A configured boundary terminates normal classification traversal.

---

# 9. Boundary Protection

Once a Classification Boundary has been explicitly confirmed by the user, later scans must not automatically move that boundary deeper or shallower.

Example:

```text
Furina   ← configured boundary
├── 001
├── 002
├── 003
└── New Set
```

The Wizard must not decide that `New Set` is a new classification level merely because it appeared after the original configuration.

The existing user decision remains authoritative until explicitly changed by the user.

---

# 10. New Branch Detection

Collection structure can evolve over time.

When a new branch appears above an existing Classification Boundary, the Wizard may report the new branch to the user.

Example:

```text
Anime
└── Genshin Impact
    ├── Furina
    └── Navia
```

If `Navia` was previously unknown, the Wizard may present it as a new branch requiring configuration.

New branches are not silently treated as approved classification structure.

---

# 11. User Confirmation

The Wizard requires explicit user confirmation when a newly detected branch would become part of the logical Collection Definition.

The Wizard must not automatically:

* assign semantic meaning;
* create Classification Boundaries;
* extend FINAL structure;
* change previously approved boundaries.

The user may accept, postpone or ignore a newly discovered branch according to the configuration workflow.

---

# 12. Collection Definition and FINAL

Collection Definition represents the structure that is considered valid for the user's organized collection.

FINAL may contain historical mistakes, but its configured structure remains the basis for approved destinations.

The existence of an actual directory on disk does not automatically make it a valid destination.

A directory becomes an approved destination through Collection Definition.

---

# 13. AI and TODO

AI is a working/transitional area and may contain dynamic directories that are not present in FINAL.

TODO is a processing source/workspace.

The Wizard does not use arbitrary AI-generated directories as proof that those directories belong to FINAL.

AI may therefore contain, for example:

```text
AI/Ben 10/
AI/Sets/0001/
```

without those directories being added to Collection Definition for FINAL.

---

# 14. Set Folders

A Set may create physical directories within AI or beneath an already configured primary collection destination.

For example:

```text
Anime
└── Genshin Impact
    └── Furina
        ├── 0001
        ├── 0002
        └── 0003
```

The numeric Set directories are below a configured classification boundary and therefore must not be interpreted as additional semantic levels by the Wizard.

Likewise, AI Set workspaces such as `AI/Sets/0001` are processing structures and are not automatically incorporated into FINAL Collection Definition.

---

# 15. Relationship with AutoSort

AutoSort uses Collection Definition as its source of valid destination structure.

The Wizard does not perform AutoSort operations.

If a destination is absent from Collection Definition, AutoSort must treat that destination as unavailable for FINAL placement.

AI workspace creation is a separate workflow and does not imply a new FINAL destination.

---

# 16. Relationship with Analysis Modules

Analysis modules may produce observations such as:

```text
Universe
Character
Species
Theme
```

Those observations do not automatically modify Collection Definition.

A classification becomes a valid FINAL destination only when the corresponding structure is defined by the user.

Analysis may nevertheless create or populate AI workspace directories when the applicable module/workflow thresholds allow it.

---

# 17. Multiple Roots and Trees

The user may configure multiple independent roots.

Each root may have its own traversal rules and access policy.

The Wizard must not assume that all roots share the same physical hierarchy.

A project may therefore have, for example:

```text
D:\Anime
E:\Monster Girls
F:\Western Animation
G:\Themes
```

without assuming that these are subdirectories of one another.

---

# 18. Updates

Collection Definition may be updated incrementally.

A later Wizard execution should focus on configuration changes and previously unknown branches rather than reinterpreting the entire collection from scratch every time.

Existing approved boundaries and rules remain intact unless the user explicitly changes them.

---

# 19. Access Policy

Each configured root may have an associated Directory Access Policy as defined by the project-wide access policy specification.

Examples:

```text
PROTECTED
READ_ONLY
MODIFY
PLAYGROUND
```

The Wizard records/configures the applicable policy but does not override it during later module execution.

---

# 20. Safety Principles

The Wizard follows these principles:

* user configuration takes precedence over inferred meaning;
* existing Classification Boundaries are protected;
* new branches require explicit confirmation before becoming approved structure;
* TODO and AI do not silently become FINAL definitions;
* Set directories below a configured boundary are not reinterpreted as semantic levels;
* the Wizard never moves image files;
* the Wizard never renames image files;
* the Wizard never performs image analysis;
* the Wizard never creates arbitrary FINAL directories.

---

# 21. Logging

Wizard executions shall follow DOC-007 and DOC-011.

The execution summary should include, where applicable:

```text
execution_id
selected roots
branches inspected
new branches found
boundaries added/changed by user
branches ignored
errors
completion status
```

---

# 22. Acceptance Criteria

The Collection Definition Wizard is compliant when it can:

* configure multiple independent collection roots;
* represent primary collection trees without hard-coded names;
* store traversal rules;
* store protected Classification Boundaries;
* avoid interpreting Set folders as semantic classification levels;
* detect newly appearing branches above configured boundaries;
* require user confirmation before approving new structure;
* keep AI and TODO outside the approved FINAL definition;
* provide Collection Definition used by AutoSort and other destination-aware modules;
* operate without analysing image contents.

---

# End of DOC-303 temporary backup
