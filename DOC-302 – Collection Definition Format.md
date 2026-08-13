# DOC-302 – Collection Definition Format


# 1. Purpose

This document defines the Collection Definition model used throughout the project.

The Collection Definition determines how the project interprets directory structures and identifies logical collections within the user's filesystem.

Unlike ordinary folder indexing, Collection Definition describes the logical organization of data rather than its physical layout.

This document serves as the primary reference for every module that traverses or interprets collection structures.

---

# 2. Scope

The Collection Definition is used by, but not limited to:

* DOC-101 – Scanner Module
* DOC-106 – Universe Analysis Module
* DOC-107 – Character Analysis Module
* DOC-108 – Theme Analysis Module
* DOC-201 – AutoSort Engine
* DOC-203 – File Renamer
* DOC-301 – Collection Definition Wizard
* DOC-401 – Collection Consistency Checker

All modules operating on collections shall interpret directory structures according to this specification.

---

# 3. Design Philosophy

The project deliberately separates **physical directory structure** from **logical collection structure**.

A directory hierarchy may contain:

* organizational folders;
* grouping folders;
* publisher folders;
* franchise folders;
* actual collections.

These concepts are not equivalent.

The Collection Definition exists to explicitly describe which directories represent logical collections and how traversal should continue.

The project shall never rely solely on directory depth.

---

# 4. Collection Definition Model

The Collection Definition consists of traversal rules assigned to selected directories.

Traversal rules describe **how a directory should be interpreted**, not how many levels exist below it.

This allows collections with completely different layouts to coexist within the same project.

Example:

```text id="jz3otw"
Games
├── KOF
├── Resident Evil
├── Hoyoverse
│   ├── Genshin Impact
│   ├── Honkai Impact
│   └── ZZZ
```

Although all directories exist within the same tree, they may follow different traversal rules.

---

# 5. Traversal Philosophy

Directory traversal is rule-driven.

The Wizard does not determine collection boundaries by counting folder levels.

Instead, every directory is interpreted according to the traversal rule assigned to it.

Traversal continues until a rule instructs the Wizard to stop or change behaviour.

This approach provides significantly greater flexibility than depth-based traversal.

---

# 6. Traversal Rules

Each configured directory shall use exactly one traversal rule.

---

## 6.1 This Folder Is A Collection

The selected directory itself represents a logical collection.

The Wizard shall:

* register the directory;
* stop scanning below it.

Example:

```text id="gkr4w6"
Games
└── KOF
```

Collection:

```text id="kefgob"
Games/KOF
```

Subdirectories are ignored by Collection Definition.

---

## 6.2 Immediate Children Are Collections

The selected directory acts only as a container.

Every direct child directory represents a collection.

Traversal stops after the first child level.

Example:

```text id="3rtphv"
Games
├── KOF
├── Resident Evil
├── Final Fantasy
└── Hoyoverse
```

Collections:

```text id="1v8ocw"
Games/KOF

Games/Resident Evil

Games/Final Fantasy

Games/Hoyoverse
```

Unless overridden by another traversal rule.

---

## 6.3 Continue Traversal

The selected directory serves only as an organizational node.

The Wizard continues scanning until another traversal rule is encountered.

Example:

```text id="1b7l9w"
Games
└── Hoyoverse
```

This directory is not considered a collection.

Its children are evaluated individually.

---

## 6.4 Ignore Branch

The selected directory and all descendants are excluded from Collection Definition.

Typical use cases include:

* temporary folders;
* archives;
* backups;
* unsupported content;
* user-defined exclusions.

---

# 7. Rule Inheritance

Traversal rules are inherited from parent directories unless explicitly overridden.

Whenever a child directory defines its own traversal rule, the inherited behaviour is replaced.

Example:

```text id="vq2wbq"
Games

Rule:

Immediate Children Are Collections
```

Normally:

```text id="wpf4ix"
Games/KOF
```

would become a collection.

However:

```text id="y7m3hp"
Games/Hoyoverse
```

defines:

```text id="gkhtgu"
Continue Traversal
```

Therefore:

```text id="1qkjlwm"
Games/Hoyoverse
```

is not registered as a collection.

Traversal continues.

Later:

```text id="wlaj1b"
Games/Hoyoverse/Genshin Impact
```

defines:

```text id="jzhggh"
Immediate Children Are Collections
```

Collections become:

```text id="yjlwm0"
Games/Hoyoverse/Genshin Impact/Furina

Games/Hoyoverse/Genshin Impact/Nahida

Games/Hoyoverse/Genshin Impact/Lumine
```

without requiring manual configuration for every character folder.

---

# 8. Why Rule-Based Traversal

Directory depth alone cannot describe real-world collections.

Example:

```text id="dy1nhh"
Games/KOF
```

represents a complete collection.

Meanwhile:

```text id="0nm3kw"
Games/Hoyoverse
```

is only a publisher grouping.

Likewise:

```text id="ytuy1r"
Games/Hoyoverse/Genshin Impact
```

may itself be only a grouping folder containing character collections.

A fixed maximum depth would therefore fail to describe the intended structure.

Traversal rules solve this problem by describing the meaning of directories rather than their position.

---

# 9. Directory Discovery

The Collection Definition Wizard traverses the filesystem according to traversal rules.

Traversal begins from one or more user-selected root directories.

The Wizard processes every directory using the following logic:

1. Read traversal rule.
2. Interpret current directory.
3. Apply rule.
4. Continue traversal if required.
5. Register discovered collections.

Traversal order is implementation-dependent.

The resulting Collection Definition shall remain identical regardless of traversal order.

---

# 10. Graphical Configuration

Traversal rules are intended to be configured through the Collection Definition Wizard.

Example context menu:

```text id="7e6sq2"
Collection Rule

○ This folder is a collection

○ Treat direct children as collections

○ Continue scanning deeper

○ Ignore this branch
```

The user should never be required to manually edit configuration files.

The Wizard shall provide an intuitive interface for assigning traversal behaviour.

---

# 11. General Principles

The Collection Definition shall satisfy the following requirements:

* independent from directory depth;
* independent from absolute filesystem location;
* deterministic;
* human-readable;
* easily editable;
* extensible;
* compatible with future collection types.

Traversal rules describe **logical intent**, not physical hierarchy.

This principle takes precedence throughout the entire project.

# DOC-302 – Collection Definition Format

## Part 2/3

---

# 12. Collection Types

A Collection represents the smallest logical unit managed by the project.

A Collection may correspond to:

* a game;
* an anime;
* a character;
* a theme;
* a species;
* an artist;
* or any future user-defined category.

The project deliberately does not enforce a fixed taxonomy.

The Collection Definition only describes relationships between collections.

---

# 13. Collection Properties

Every Collection should contain, at minimum:

* unique internal identifier;
* display name;
* current filesystem path;
* traversal rule (if applicable);
* parent collection (if applicable);
* collection type;
* enabled status.

Additional properties may be introduced without breaking compatibility.

---

# 14. Root Collections

Root Collections define the starting points of the project.

Examples include:

```text id="2kn7h4"
Games

Anime

Monster Girls

Themes

IRL

Reference
```

A Root Collection does not necessarily represent a searchable collection.

It usually acts as an organizational node.

---

# 15. Organizational Nodes

Many directories exist solely to improve filesystem organization.

Examples:

```text id="fgzz8w"
Games
└── Hoyoverse
```

"Hoyoverse" is not a collection.

It is an organizational node.

Likewise:

```text id="rv4w8j"
Anime
└── Seasonal
```

may exist only to group several collections.

The Collection Definition explicitly distinguishes organizational nodes from logical collections.

---

# 16. Collection Hierarchy

Collections may form parent-child relationships.

Example:

```text id="msr32d"
Games

└── Hoyoverse

    └── Genshin Impact

        ├── Furina

        ├── Nahida

        └── Lumine
```

Logical hierarchy:

```text id="o1bbjr"
Games

↓

Genshin Impact

↓

Furina
```

"Hoyoverse" exists only as an organizational node.

---

# 17. Collection Categories

Collections should belong to a category.

Typical categories include:

* Game
* Anime
* Character
* Theme
* Monster Girl
* Artist
* Original Character
* VTuber
* Meme
* Screenshot

Additional categories may be introduced later.

The system shall not require modifications to existing collections when new categories are added.

---

# 18. Collection Relationships

Collections may reference other collections.

Examples:

```text id="u0kxsk"
Character

↓

Universe

↓

Theme
```

or

```text id="fx1trq"
Monster Girl

↓

Species
```

These relationships describe logical organization.

They do not necessarily correspond to directory structure.

---

# 19. User-Defined Collections

Users may create their own collections.

Examples:

```text id="m7wzh0"
Cyberpunk

Military

Halloween

Christmas

School Uniform

Fantasy Weapons
```

The Collection Definition shall treat user-created collections exactly like predefined ones.

---

# 20. Collection Naming

Collection names should remain independent from physical directory names.

Display name:

```text id="llj8nt"
Genshin Impact
```

Filesystem:

```text id="tujmko"
genshin_impact
```

Both may coexist.

This allows filesystem-friendly naming while preserving readable presentation.

---

# 21. Collection Paths

Each Collection stores its current filesystem location.

Example:

```text id="l6urc2"
D:\Games\Hoyoverse\Genshin Impact\Furina
```

This location is considered the current source directory.

If moved, the Collection Definition should be updated by the appropriate maintenance tools.

---

# 22. Empty Collections

A Collection may temporarily contain no files.

Example:

```text id="8krgrh"
New Character

↓

(empty)
```

The Collection shall remain valid.

The absence of files does not invalidate Collection Definition.

---

# 23. Collection Validation

The Wizard should verify:

* duplicate collection names under the same parent;
* missing directories;
* invalid traversal rules;
* circular parent references;
* inconsistent hierarchy.

Detected problems should be reported according to DOC-011.

---

# 24. Collection Discovery

Discovery is performed by traversing directories according to traversal rules.

Whenever a directory satisfies the current traversal rule, the Wizard registers it as a Collection.

Discovery shall never depend solely on folder depth.

---

# 25. Manual Overrides

The user may manually adjust Collection Definition after automatic discovery.

Examples include:

* changing traversal rules;
* changing collection category;
* changing parent relationships;
* excluding collections.

Manual decisions always take precedence over automatic discovery.

---

# 26. Future Compatibility

The Collection Definition shall remain compatible with future modules.

Future modules may introduce:

* additional collection categories;
* additional relationships;
* custom metadata;
* plugin-defined attributes.

The format shall remain extensible without requiring structural redesign.

27. Import

The Collection Definition Wizard shall support importing previously saved Collection Definitions.

Import allows the user to restore an existing project configuration without repeating the discovery process.

The import mechanism should validate:

document version;
required fields;
collection identifiers;
traversal rules;
hierarchy consistency.

Invalid definitions shall not be imported without user confirmation.

28. Export

The Collection Definition may be exported for:

project backup;
migration to another computer;
sharing between project instances;
disaster recovery.

The exported definition should contain only logical collection information.

Image analysis results, database contents and module metadata are outside the scope of Collection Definition.

29. Versioning

The Collection Definition format shall contain a version identifier.

Every future modification affecting compatibility shall increase the document format version.

Example:

Collection Definition

Version:

1.0

Future versions should remain backward-compatible whenever practical.

When compatibility cannot be preserved, the importing module shall notify the user.

30. Synchronization

Collection Definition represents the intended logical structure of the project.

The filesystem may change independently.

Examples include:

directory renamed;
directory moved;
collection removed;
collection added manually.

Modules responsible for synchronization shall detect these changes and update the Collection Definition when requested by the user.

Collection Definition shall never silently modify itself without explicit user action.

31. Relationship with Scanner

The Scanner Module shall use the Collection Definition to determine:

which directories belong to a collection;
where collection boundaries exist;
which branches should be ignored.

The Scanner shall never attempt to infer collection structure independently.

32. Relationship with AutoSort

The AutoSort Engine uses the Collection Definition to determine valid destination collections.

The Collection Definition defines where files may be placed.

The AutoSort Engine decides which destination is appropriate.

33. Relationship with Analysis Modules

Analysis modules may reference Collection Definitions during classification.

Examples:

Universe Analysis
Character Analysis
Theme Analysis

The Collection Definition provides the logical hierarchy into which analysis results may later be mapped.

Analysis modules shall not modify the Collection Definition directly.

34. Relationship with Collection Consistency Checker

The Collection Consistency Checker validates whether:

collections still exist;
directory paths remain valid;
traversal rules remain consistent;
duplicate definitions exist.

Any detected inconsistencies shall be reported to the user.

Automatic repair shall only occur if explicitly requested.

35. Example Configuration

Example:

Games
Rule:
Immediate Children Are Collections

Games/Hoyoverse
Rule:
Continue Traversal

Games/Hoyoverse/Genshin Impact
Rule:
Immediate Children Are Collections

Games/KOF
Rule:
This Folder Is A Collection

Games/Resident Evil
Rule:
This Folder Is A Collection

Result:

Games/KOF

Games/Resident Evil

Games/Hoyoverse/Genshin Impact/Furina

Games/Hoyoverse/Genshin Impact/Nahida

Games/Hoyoverse/Genshin Impact/Lumine

without requiring every character directory to be configured individually.

36. Best Practices

Users are encouraged to:

keep directory structures consistent;
avoid unnecessary organizational levels;
configure traversal rules only where exceptions are required;
review Collection Definitions after major filesystem changes;
export Collection Definitions before performing large-scale reorganization.

These practices simplify long-term maintenance.

37. Design Objectives

The Collection Definition model has been designed to achieve the following goals:

independence from fixed directory depth;
support for heterogeneous directory structures;
deterministic traversal;
minimal configuration effort;
future extensibility;
compatibility with all project modules.

The model intentionally separates filesystem organization from logical project organization.

38. Final Principle

The Collection Definition describes how the project understands the filesystem, not how the filesystem itself is organized.

Directories are interpreted according to explicitly assigned traversal rules rather than their position within the directory tree.

This allows collections with completely different layouts to coexist within a single project while remaining fully deterministic and easy to maintain.

The Collection Definition shall be considered the authoritative source describing the logical organization of all collections managed by the project.

End of DOC-302
