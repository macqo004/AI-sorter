# DOC-302 – Collection Definition Format

**Project:** AI Image Collection Management System

**Document:** DOC-302

**Module / Area:** Collection Definition Format

**Version:** 2.0

**Status:** Design Specification

---

# 1. Purpose

This document defines the formal data model and semantics of a **Collection Definition**.

A Collection Definition describes how the application interprets configured filesystem roots, directory traversal, logical classification structure, collection boundaries, and access policies.

It is the configuration consumed by modules such as:

* Scanner;
* AutoSort;
* File Renamer;
* Set Detection;
* Collection Consistency Checker;
* analysis modules that need collection scope information.

This document defines **what a Collection Definition contains and what its fields mean**.

The process by which the user creates or edits the definition belongs to **DOC-301 – Collection Definition Wizard**.

---

# 2. Separation from DOC-301

The responsibilities are intentionally separated.

```text
DOC-301
Collection Definition Wizard
    ↓
creates / edits
    ↓
DOC-302
Collection Definition
    ↓
consumed by project modules
```

DOC-301 defines user interaction and discovery workflow.

DOC-302 defines the resulting configuration model.

A module must not depend on GUI details in order to consume a valid Collection Definition.

---

# 3. Design Philosophy

The Collection Definition separates:

* physical filesystem structure;
* logical collection structure;
* traversal behaviour;
* collection boundaries;
* access permissions;
* workspace roles.

The project shall not rely solely on directory depth to determine meaning.

Two directory trees with different physical layouts may represent equivalent logical structures when their Collection Definitions describe them accordingly.

Collection Definition is configuration, not image-analysis data.

It does not contain:

* image classifications;
* SHA512 values;
* image metadata;
* analysis results;
* Review Queue decisions.

Those belong to the database and module-specific data structures.

---

# 4. Definition Identity

Each Collection Definition shall have a stable internal identity.

Minimum fields:

```text
 definition_id
 format_version
 enabled
 created_at
 updated_at
```

`definition_id` identifies the configuration object, not an individual filesystem directory.

A Collection Definition may be versioned or replaced while the project remains the same.

---

# 5. Root Definition

A **Root Definition** describes a configured filesystem root used by the project.

Each root shall contain at least:

```text
root_id
path
role
enabled
recursive
access_policy
```

Optional properties may include:

```text
display_name
collection_tree_id
default_traversal_rule
notes
```

The exact serialized representation is implementation-defined, but the semantics above are mandatory.

---

# 6. Root Roles

A root shall have a configured role.

The role determines the broad purpose of that root and must not be inferred from its directory name alone.

Supported roles are:

### PRIMARY

A user-defined main collection tree.

Examples may include trees commonly named:

```text
Anime
Monster Girls
Western Animation
```

These are examples only. Their names are not hard-coded project requirements.

Multiple PRIMARY roots are allowed.

All configured PRIMARY trees have higher organisational priority than the Theme fallback.

### THEME_FALLBACK

A fallback organisation tree used when no suitable higher-priority PRIMARY destination is currently available.

Themes remain metadata even when a file is physically stored in a Theme destination.

### TODO

A processing/source workspace containing files that have not completed the intended classification workflow.

TODO may contain subdirectories used by the user's processing workflow.

### AI

A dynamic working/transitional workspace used by analysis and organisation workflows.

AI may contain classifications, universes, sets, or other workspaces that are not yet represented in FINAL.

AI may therefore change dynamically without modifying the PRIMARY Collection Definition.

### IMPORT_SOURCE

An optional source root used to import or stage data for processing.

This role is available for future or specialized workflows and does not imply FINAL status.

---

# 7. FINAL and Workspace Semantics

The Collection Definition distinguishes approved collection structure from processing workspaces.

```text
PRIMARY / THEME_FALLBACK
    = organised collection structure

TODO / AI
    = processing or transitional workspaces
```

FINAL is a conceptual property of approved collection trees. The physical root may be represented by one or more PRIMARY roots and the configured Theme fallback.

AI and TODO are not treated as final collection trees merely because they contain classified files.

The existence of a directory in AI does not automatically add that directory to the approved PRIMARY structure.

---

# 8. Directory Access Policy

Every configured root shall have an access policy.

Supported policies are:

### PROTECTED

The strongest protection.

Modules may inspect the root only. No filesystem modification is permitted.

### READ_ONLY

Modules may inspect, hash, analyse, compare, report, and create database-side suggestions.

They may not modify files or directories.

### MODIFY

Modules may perform filesystem operations explicitly allowed by their own specifications.

Examples include:

* rename;
* move;
* creation of permitted workspace directories.

### PLAYGROUND

An experimental or testing area.

Operations are allowed according to the module and local configuration. Playground content is not automatically considered part of FINAL.

A future `DISABLED` state may be introduced without changing the general model.

Access Policy is a configuration attribute and must not be inferred from directory names.

---

# 9. Root-Specific Behaviour

Root configuration is independent.

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

# 10. Recursive Traversal

Each root or configured node shall define whether traversal continues into child directories.

The configuration shall not rely on a universal global recursion setting.

A root may be recursive while a child branch stops traversal, and another branch may explicitly continue it.

This allows different physical directory layouts to coexist.

---

# 11. Traversal Rules

Traversal rules describe **how a directory is interpreted**.

The following baseline rules are supported.

## 11.1 THIS_FOLDER_IS_COLLECTION

The selected directory represents a logical collection boundary.

Traversal does not continue below that directory for Collection Definition purposes.

## 11.2 IMMEDIATE_CHILDREN_ARE_COLLECTIONS

The selected directory is an organisational container.

Its immediate child directories are treated as logical collections.

Traversal stops at that child level unless an explicitly configured child rule requires further traversal.

## 11.3 CONTINUE_TRAVERSAL

The selected directory is an organisational node and traversal continues into its descendants.

## 11.4 IGNORE_BRANCH

The selected directory and its descendants are excluded from Collection Definition traversal.

These rules describe configuration semantics, not GUI actions.

---

# 12. Traversal Rule Inheritance

A traversal rule may be inherited from a parent configuration node.

A child may explicitly override the inherited rule.

Example:

```text
Games
    rule = IMMEDIATE_CHILDREN_ARE_COLLECTIONS

Games/Hoyoverse
    rule = CONTINUE_TRAVERSAL
```

In this case the child rule overrides the inherited behaviour.

The resulting definition must be deterministic regardless of filesystem traversal order.

---

# 13. Collection Nodes

A **Collection Node** represents a directory that is explicitly part of the logical approved structure.

A Collection Node shall contain at least:

```text
node_id
parent_node_id
path
role
enabled
```

Optional properties may include:

```text
display_name
classification_type
traversal_rule
boundary_type
notes
```

A node may be an organisational node rather than a classification destination.

The format must therefore distinguish logical role from filesystem existence.

---

# 14. Organisational Nodes

An organisational node exists to structure the filesystem without necessarily representing a final classification.

Example:

```text
PRIMARY
└── Games
    └── Hoyoverse
        └── Genshin Impact
            └── Furina
```

`Hoyoverse` may be an organisational node.

The Collection Definition must preserve such nodes because they affect traversal and paths, even when they are not valid placement destinations by themselves.

---

# 15. Classification Boundaries

A **Classification Boundary** marks the point where the logical classification structure ends.

Below that boundary, directories are considered user organisation or processing structure rather than additional classification levels.

Example:

```text
PRIMARY/Anime
└── Genshin Impact
    └── Furina    ← CLASSIFICATION BOUNDARY
        ├── 0001
        ├── 0002
        └── Favorites
```

The following directories must not automatically become classification nodes:

```text
0001
0002
Favorites
```

This rule prevents numeric Set directories and other user-managed subfolders from being misinterpreted as semantic categories.

---

# 16. Boundary Types

Where a boundary represents a known classification layer, its type may be stored.

Examples include:

```text
UNIVERSE
CHARACTER
SPECIES
THEME
OTHER_USER_DEFINED
```

Boundary types are descriptive metadata for the structure.

They do not force a global taxonomy upon the project.

---

# 17. Set Handling at a Classification Boundary

Set directories may exist below a Classification Boundary.

Example:

```text
Anime
└── Genshin Impact
    └── Furina
        ├── 0001
        ├── 0002
        └── 0003
```

`0001`, `0002`, and `0003` represent physical Set directories, not additional semantic classification levels.

The Collection Definition must preserve the boundary so that Scanner and other traversal modules do not interpret these directories as Universe, Character, Theme, or another classification level.

Set Detection may still create and manage physical Set directories in AI and, when authorised, within an already valid parent collection structure.

Set creation does not create a new PRIMARY branch.

---

# 18. Collection Tree Identity

Each configured PRIMARY tree should have a stable `tree_id`.

Minimum properties:

```text
tree_id
root_id
display_name
enabled
```

The filesystem directory name is not the tree identity.

This permits directory renaming without changing the logical identity of the tree, provided the configuration is updated consistently.

---

# 19. Primary Tree Priority

All configured PRIMARY trees have higher organisational priority than `THEME_FALLBACK`.

The exact selection between multiple PRIMARY trees is determined by their configured classification and placement rules.

The following names are examples only:

```text
Anime
Monster Girls
Western Animation
```

The format does not require these names or any fixed number of PRIMARY trees.

The priority rule is structural:

```text
PRIMARY TREES
       ↓
THEME FALLBACK
```

---

# 20. Theme Fallback Definition

The Theme fallback is represented as a configured root with role `THEME_FALLBACK`.

A Theme destination is valid only when its path is represented in Collection Definition and the applicable access policy allows the intended operation.

Theme is a fallback physical organisation, not a replacement for classification metadata.

If a higher-priority PRIMARY destination becomes valid later, AutoSort may move the file out of the Theme fallback according to its specification.

---

# 21. AI Workspace Definition

The AI root is represented as a configured workspace root with role `AI`.

AI may contain dynamically created subdirectories such as:

```text
AI/Ben 10/
AI/Pokemon/
AI/Sets/0001/
```

These directories do not need to exist in PRIMARY trees.

AI workspace directories may be created when permitted by the relevant module and configured thresholds.

Creating an AI directory does not modify the PRIMARY Collection Definition.

---

# 22. TODO Workspace Definition

The TODO root is represented as a configured workspace root with role `TODO`.

TODO may contain user-defined staging directories.

Modules may scan TODO according to the configured traversal and access policy.

TODO subdirectories must not automatically become PRIMARY collection nodes.

---

# 23. Enabled and Disabled Entries

Roots and nodes may be enabled or disabled.

A disabled root or node remains part of the stored configuration but must not be used for normal processing until re-enabled.

Disabling configuration does not delete physical directories and does not delete database records.

---

# 24. Paths

Paths stored in Collection Definition identify the current physical location of a root or node.

A path may be absolute or use a project-defined path abstraction, provided all consuming modules interpret it consistently.

The format must preserve enough information to identify the actual filesystem location unambiguously.

A path is not a logical identity. Logical identities are represented by `root_id`, `tree_id`, and `node_id`.

---

# 25. Logical Name vs Filesystem Name

The format may store a display name independent of the physical directory name.

Example:

```text
Display name:
Genshin Impact

Filesystem name:
genshin_impact
```

Modules must use the configured path for filesystem operations and the configured logical name for presentation.

---

# 26. Empty Collections

An enabled collection node may exist even when the directory currently contains no image files.

Empty status does not invalidate the Collection Definition.

This is important for newly created final destinations that have not yet received files.

---

# 27. Configuration Does Not Contain Image State

Collection Definition shall not store per-file state such as:

```text
SHA512
file_id
Universe confidence
Theme confidence
Review decisions
```

Such state belongs to the database.

Collection Definition describes the environment in which those records are interpreted.

---

# 28. Configuration Versioning

The serialized Collection Definition shall contain a format version.

Changes that alter field meaning or compatibility require a format-version update.

A module consuming an unsupported format version must fail safely rather than silently interpreting unknown semantics.

---

# 29. Import and Export

A Collection Definition may be exported independently of the image database.

Export is intended for:

* project configuration backup;
* migration to another computer;
* disaster recovery;
* controlled transfer between project instances.

An imported definition must be validated before activation.

Import does not import:

* image records;
* SHA512 values;
* analysis results;
* Review Queue decisions.

---

# 30. Validation Rules

A valid Collection Definition shall not contain:

* duplicate `root_id` values;
* duplicate `tree_id` values;
* duplicate `node_id` values;
* broken parent references;
* circular parent relationships;
* invalid traversal rules;
* an unsupported access policy;
* multiple contradictory definitions for the same configured path;
* a child node outside the scope of its configured root;
* an invalid Classification Boundary relationship.

A root or node whose physical path no longer exists may remain stored for user review, but consuming modules must report the missing path rather than silently redirecting to another directory.

---

# 31. Manual Configuration Priority

User-approved Collection Definition takes priority over automatic filesystem interpretation.

Automatic discovery may propose changes, but it must not silently replace an existing user-defined boundary, root role, access policy, or traversal rule.

The Wizard may present changes for explicit user approval according to DOC-301.

---

# 32. Compatibility with Modules

Modules shall consume Collection Definition according to their own scope.

Examples:

```text
Scanner
→ root paths + traversal + processing scope

AutoSort
→ primary destinations + fallback destinations + access policy

Renamer
→ selected filesystem scope + access policy

Set Detection
→ eligible image scopes + permitted Set workspaces

Collection Consistency Checker
→ FINAL/PRIMARY structure for read-only validation
```

No module may invent missing Collection Definition entries and silently treat them as configured destinations.

---

# 33. Relationship with AI-created Directories

AI-created directories are runtime workspace objects and must not automatically become persistent PRIMARY Collection Definition entries.

For example:

```text
AI/Ben 10/
```

may exist without:

```text
PRIMARY/.../Ben 10/
```

When the user later creates an approved destination in the PRIMARY structure, the Collection Definition may be updated through DOC-301.

This preserves the distinction between discovery/workspace and approved collection structure.

---

# 34. Relationship with Set Directories

Physical Set directories may be created dynamically in AI.

They may also be created inside an already valid PRIMARY classification boundary when the Set module is authorised to do so.

Examples:

```text
AI/Sets/0001/

PRIMARY/Anime/Genshin Impact/Furina/0001/
```

Neither case permits creation of an arbitrary new PRIMARY parent such as:

```text
PRIMARY/New Universe/
```

unless that parent has been explicitly added to Collection Definition by the user.

---

# 35. Determinism

The same Collection Definition applied to the same filesystem state shall produce the same logical interpretation regardless of module execution order.

Changes in interpretation must result from a configuration change, filesystem change, or explicit versioned semantics change, not from nondeterministic traversal order.

---

# 36. Acceptance Criteria

DOC-302 is considered complete when the format can unambiguously represent:

* one or more configured roots;
* primary collection trees;
* Theme fallback;
* TODO workspace;
* AI workspace;
* root-specific access policies;
* recursive traversal settings;
* traversal rules;
* organisational nodes;
* logical collection nodes;
* Classification Boundaries;
* Set boundaries and physical Set directories;
* enabled/disabled entries;
* stable configuration identifiers;
* filesystem paths;
* versioning;
* import/export;
* validation requirements;
* user-approved configuration semantics.

---

# End of DOC-302
