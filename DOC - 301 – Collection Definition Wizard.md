# DOC-301 – Collection Definition Wizard

**Project:** AI Image Collection Management System

**Document:** DOC-301

**Version:** 2.0

**Status:** Design Specification

---

# 1. Purpose

Collection Definition Wizard is responsible for creating and maintaining the logical definition of the user's configured collection structure.

The Wizard does not analyse image contents, perform semantic classification, move files, rename files, or automatically create FINAL collection directories.

Its purpose is to define, with explicit user control:

* which configured roots form collection trees;
* how those trees are traversed;
* which directories are part of the logical classification structure;
* where Classification Boundaries occur;
* which directories below those boundaries belong to user-managed organisation;
* which locations are available as valid destinations to other modules.

The resulting configuration is represented by the Collection Definition specified in **DOC-302**.

---

# 2. Source of Collection Definition

Collection Definition is based on directory structures explicitly selected by the user.

For FINAL collection trees, the Wizard uses the existing approved directory structure as its source.

TODO and AI are processing/workspace areas and are not authoritative sources for FINAL collection structure.

The user explicitly selects the roots to configure. The Wizard must not assume that every directory on the machine belongs to the project.

---

# 3. Primary Collection Trees

A project may contain multiple independent PRIMARY collection trees.

Examples such as `Anime`, `Monster Girls`, or `Western Animation` are illustrative only. Their names are not hard-coded.

The user may configure any number of PRIMARY trees and may choose their physical locations independently.

A Theme fallback may also be configured. It has lower organisational priority than every configured PRIMARY tree.

---

# 4. Directory Definition

The Wizard builds a Collection Definition containing information such as:

```text
root identity
root path
root role
collection tree identity
logical nodes
enabled state
traversal rules
Classification Boundaries
access policy
```

The definition does not contain image-analysis results.

File identity and analysis results belong to the database.

The formal meaning of these fields is defined by DOC-302.

---

# 5. First Configuration

During initial configuration:

1. The user selects one or more roots.
2. The Wizard inspects the selected directory structures.
3. The Wizard builds a temporary representation.
4. The Wizard presents that representation to the user.
5. The user defines traversal behaviour and Classification Boundaries.
6. The Wizard validates the resulting configuration.
7. The Wizard stores the resulting Collection Definition.

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

This prevents a Set folder or other user-managed subdirectory from accidentally being treated as a character, universe, theme, or another classification level.

---

# 7. Boundary Types

A Classification Boundary may have a configured logical type when the user wishes to identify the role of that level.

Possible types include:

```text
PRIMARY_ROOT
UNIVERSE
CHARACTER
SPECIES
THEME
OTHER_USER_DEFINED
```

The list is extensible and must not be hard-coded to the examples above.

The boundary type describes the role of the configured directory. It does not itself produce an analysis result.

---

# 8. Traversal Rules

Collection Definition must support explicit traversal behaviour.

Typical rules include:

```text
THIS_FOLDER_IS_COLLECTION
IMMEDIATE_CHILDREN_ARE_COLLECTIONS
CONTINUE_TRAVERSAL
IGNORE_BRANCH
```

The exact serialized representation is defined by DOC-302.

The important rule is that modules must not assume that every subdirectory is a semantic classification level.

A configured Classification Boundary terminates normal classification traversal.

---

# 9. Boundary Protection

Once a Classification Boundary has been explicitly confirmed by the user, later Wizard executions must not automatically move that boundary deeper or shallower.

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
* extend approved FINAL structure;
* change previously approved boundaries;
* convert an AI-created directory into a PRIMARY destination.

The user may accept, postpone, ignore, or otherwise configure a discovered branch according to the GUI workflow.

---

# 12. Collection Definition and FINAL

Collection Definition represents the structure considered valid for the user's organised collection.

FINAL may contain historical mistakes. The existence of a directory on disk does not automatically make it a valid destination.

A directory becomes an approved FINAL destination through Collection Definition.

Conversely, an existing FINAL directory remains a real filesystem location and may contain files that later require correction. Collection Consistency Checker and Review Queue handle such cases without assuming that FINAL is infallible.

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

without those directories being added to the PRIMARY Collection Definition.

If the user later decides that a directory should become part of FINAL, the change is explicitly configured through the Wizard.

---

# 14. Set Folders

A Set is a physical directory containing a group of visually similar images.

A Set may create physical directories inside AI or beneath an already configured PRIMARY classification destination.

Example:

```text
Anime
└── Genshin Impact
    └── Furina
        ├── 0001
        ├── 0002
        └── 0003
```

The numeric Set directories are below the configured Classification Boundary and therefore must not be interpreted as additional semantic levels.

Likewise, AI Set workspaces such as `AI/Sets/0001` are processing structures and are not automatically incorporated into FINAL Collection Definition.

Set creation does not create a new PRIMARY branch.

---

# 15. Relationship with AutoSort

AutoSort uses Collection Definition as its source of valid FINAL destination structure.

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

Analysis workflows may nevertheless create or populate AI workspace directories when applicable thresholds and policies allow it.

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
H:\AI
I:\TODO
```

without assuming that these are subdirectories of one another.

The names above are examples only.

---

# 18. Access Policy Configuration

The Wizard allows the user to assign a Directory Access Policy to each configured root, and where supported, to relevant child scopes.

Typical policies include:

```text
PROTECTED
READ_ONLY
MODIFY
PLAYGROUND
```

The Wizard records the policy; it does not override it during later module execution.

The policy is not inferred from directory names.

---

# 19. Root-Specific Configuration

Each configured root may independently specify:

```text
role
path
enabled state
access policy
recursive/traversal behaviour
collection tree identity, where applicable
```

For example:

```text
Root A
role = PRIMARY
access_policy = MODIFY
recursive = true

Root B
role = PRIMARY
access_policy = READ_ONLY
recursive = true

Root C
role = AI
access_policy = MODIFY
recursive = true
```

One module execution may therefore legitimately have different permissions and traversal behaviour for different roots.

---

# 20. Updates

Collection Definition may be updated incrementally.

A later Wizard execution should focus on configuration changes and previously unknown branches rather than reinterpreting the entire collection from scratch every time.

Existing approved boundaries, root roles, access policies, and traversal rules remain intact unless the user explicitly changes them.

---

# 21. AI Thresholds and Dynamic Folders

The Wizard does not itself decide when an AI universe or Set folder should be created.

Those decisions belong to the applicable modules and workflows.

For example, an analysis workflow may create:

```text
AI/Ben 10/
```

when the configured amount of evidence for a previously absent universe exceeds the applicable threshold.

The existence of that directory does not require or imply the existence of a corresponding FINAL directory.

---

# 22. Validation Before Save

Before saving a Collection Definition, the Wizard shall validate at least:

* root paths are syntactically valid;
* root roles are valid;
* access policies are valid;
* traversal rules are valid;
* parent/child relationships are consistent;
* Classification Boundaries are valid;
* no contradictory definitions exist for the same configured scope;
* configured PRIMARY trees do not conflict with one another;
* AI and TODO are not silently represented as PRIMARY structure.

Invalid configurations must not become active definitions.

---

# 23. Logging

Wizard executions shall follow DOC-007 and DOC-011.

The execution summary should include, where applicable:

```text
execution_id
selected roots
branches inspected
new branches found
boundaries added/changed by user
branches ignored
validation errors
completion status
```

---

# 24. Safety Principles

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

# 25. Acceptance Criteria

The Collection Definition Wizard is compliant when it can:

* configure multiple independent roots;
* configure multiple PRIMARY collection trees without hard-coded names;
* configure a Theme fallback without treating it as a PRIMARY tree;
* configure TODO and AI roots independently;
* store traversal rules;
* store protected Classification Boundaries;
* avoid interpreting Set folders as semantic classification levels;
* detect newly appearing branches above configured boundaries;
* require user confirmation before approving new structure;
* keep AI and TODO outside the approved FINAL definition;
* configure Directory Access Policies;
* provide a validated Collection Definition consumed by AutoSort and other destination-aware modules;
* operate without analysing image contents.

---

# End of DOC-301
