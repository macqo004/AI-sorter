# DOC-109

# Set Detection and Grouping Module

**Project:** AI Image Collection Management System

**Document:** DOC-109

**Module:** Set Detection and Grouping

**Version:** 2.1

**Status:** Draft

**Depends on:**

DOC-005
DOC-007
DOC-008
DOC-010
DOC-011
DOC-012
DOC-013
DOC-302

---

# 1. Purpose

The Set Detection and Grouping module identifies groups of visually related image files and represents those groups both:

* logically in the database; and
* physically as Set directories when the files have reached an appropriate primary collection tree.

A Set is therefore not merely an analytical abstraction. In the organised collection, a Set is a physical subdirectory containing a group of visually related images.

Example:

```text
Anime/
└── Genshin Impact/
    └── Furina/
        ├── 0001/
        ├── 0002/
        ├── 0003/
        └── ...
```

Each numbered directory is a Set containing visually related images.

The database remains the source of Set identity and membership state, while the physical Set directory is the filesystem representation of that Set.

---

# 2. Scope

The module may:

* analyse visual similarity between eligible files;
* identify groups of related files;
* create and update Set records;
* associate files with Sets;
* support creation of physical Set directories where the workflow permits it;
* provide grouped context to later modules through the database.

The module shall not:

* identify characters as its primary responsibility;
* identify universes as its primary responsibility;
* identify themes as its primary responsibility;
* decide the semantic primary collection tree by itself;
* silently replace user decisions;
* invoke another module directly.

---

# 3. Definition of Set

A Set is a group of image files that share a sufficiently strong visual relationship for them to be treated as one logical collection unit.

The physical representation of a Set is a directory containing its member files.

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

# 4. Example Collection Structure

A typical organised primary tree may look like:

```text
Anime/
└── Genshin Impact/
    └── Furina/
        ├── 0001/
        │   ├── image001.jpg
        │   ├── image002.jpg
        │   └── image003.jpg
        ├── 0002/
        │   ├── image004.jpg
        │   └── image005.jpg
        └── 0003/
            └── image006.jpg
```

In this example:

```text
Genshin Impact
    = Universe level

Furina
    = Character level

0001 / 0002 / 0003
    = Set level
```

The exact names and number of hierarchy levels are determined by Collection Definition rather than hard-coded by this module.

---

# 5. Invalid Set Examples

A Set must not contain unrelated images.

Example:

```text
0004/
    furina.jpg
    ben10.jpg
    sonic.jpg
    random_landscape.jpg
```

The fact that images share colours, composition or rendering style is not sufficient evidence of a meaningful Set.

---

# 6. Module Independence

Set Detection is independently executable once eligible files have valid database identities.

Scanner must discover files before they can participate in normal Set processing, but Scanner does not need to be running while Set Detection executes.

Set Detection does not invoke Universe Analysis, Character Analysis, Theme Analysis, AutoSort or any other module directly.

Other modules may provide analysis information through the database, and other modules may consume Set information through the database.

This is a data dependency, not a process dependency.

---

# 7. Input

The module reads the current database state for eligible files and may access corresponding images from the filesystem when visual comparison is required.

Required identity information includes:

```text
SHA512
file metadata
image dimensions where available
current path
```

Supporting Analysis Results may be consumed where configured.

The module must respect Collection Definition, traversal rules and Directory Access Policy when physical Set directories are inspected or created.

---

# 8. Output

The module creates or updates Set information in the shared database and, when authorised, creates or updates the corresponding physical Set directories.

A Set should have at least:

```text
set_id
status
created_at
updated_at
```

Set membership should associate:

```text
set_id
file identity / file_id
membership status
similarity or membership score where applicable
```

The database `set_id` is the logical identity of the Set.

The physical directory is the current filesystem representation of that Set.

---

# 9. Set Identity and Physical Directory

`set_id` is the stable logical identity of a Set.

The physical directory name, path or numeric label is not the Set's logical identity.

For example:

```text
set_id = 15482

physical directory:
Anime/Genshin Impact/Furina/0007/
```

If the Set is later moved within a valid primary tree or its physical number changes as part of a controlled reorganisation, its `set_id` remains unchanged.

---

# 10. Set Location in the Collection Hierarchy

A Set is normally the **lowest physical classification level** used by the organised primary collection tree.

For example:

```text
Primary Tree
    ↓
Universe
    ↓
Character
    ↓
Set
```

The actual hierarchy may differ between primary trees. Some may use Universe without Character, or another configured classification level.

The Set must therefore be attached to the appropriate existing primary-tree destination rather than assuming fixed names or depths.

Set Detection shall not hard-code:

```text
Anime
Monster Girls
Western Animation
```

or any other physical root names.

---

# 11. Set Creation in AI / Transition Workspace

When a newly detected Set does not yet belong to an established primary collection destination, an authorised AI/transition workflow may create a temporary Set directory for review and classification.

Example:

```text
AI/Sets/0001/
AI/Sets/0002/
```

These are temporary Set workspaces.

They are not FINAL collection definitions.

A user or later processing workflow may eventually place the Set into a valid primary tree such as:

```text
Anime/Genshin Impact/Furina/0001/
```

Set Detection itself may provide the grouping information, but semantic placement remains governed by the classification and sorting workflow.

---

# 12. Set Directory Creation in Primary Trees

Once a Set has a valid primary-tree destination, the physical Set directory may be created automatically by an authorised workflow.

For example, after a file group has been classified as:

```text
Anime/Genshin Impact/Furina
```

an authorised workflow may create:

```text
Anime/Genshin Impact/Furina/0001/
```

and place the Set members there.

This is different from creating a new primary-tree classification.

Creating a Set directory **inside an already valid primary-tree destination** is permitted when the Collection Definition and access policy allow it.

Creating a new primary-tree root or semantic destination remains a user-controlled operation.

---

# 13. Set Folder Naming

Where numeric Set directories are used, the naming convention should be configurable.

A simple default may be:

```text
0001
0002
0003
```

The number is a physical label, not the Set identity.

The module must not infer semantic meaning from the number.

A directory named `001` must not automatically be interpreted as a character, universe or other classification simply because it is a child directory.

Classification boundaries and traversal rules defined by Collection Definition remain authoritative.

---

# 14. Set Creation Criteria

A new Set may be created when the module determines that a group of files meets configured grouping criteria.

The criteria should consider meaningful visual similarity rather than generic properties such as:

* common colour palette;
* identical aspect ratio;
* similar file size;
* filename similarity alone.

The module should retain enough evidence to explain why files were grouped.

---

# 15. Set Merging

The module may identify that two existing Sets represent the same logical group.

A merge requires sufficient evidence under configured rules.

Similarity alone is not automatically equivalent to logical identity.

Where confidence is insufficient, the proposed merge should enter Review Queue.

When a merge is authorised, the resulting physical directory and database membership must remain consistent.

No duplicate Set should remain as an active representation of the same logical group unless explicitly justified.

---

# 16. Set Splitting

A Set may later be split when analysis determines that its members do not form one coherent group.

Automatic splitting should be conservative.

When a split is ambiguous or could materially change user organisation, Review Queue should be used.

Set splitting must preserve file identity and sufficient historical information for traceability.

---

# 17. Review Queue Integration

The module may create Review Queue cases for:

* uncertain Set creation;
* uncertain Set merge;
* uncertain Set split;
* conflicting grouping evidence;
* uncertain physical regrouping.

Review Queue decisions are user decisions and take priority over later automatic suggestions for the protected context.

The module must not execute an uncertain destructive regrouping merely because a suggestion exists.

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
Collection Definition where required
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

# 20. Filesystem Operations

When authorised to manage physical Set directories, the module may:

* create a new Set directory within an already valid primary-tree destination;
* move Set members into that directory;
* update Set membership/path state after successful moves;
* merge or split physical Set directories as authorised;
* remove obsolete empty Set directories after a successful regrouping operation.

It must not:

* create a new FINAL primary-tree classification on its own;
* create arbitrary new universe/character/theme roots;
* move files across primary trees merely because they look visually similar;
* treat a numeric Set directory as semantic evidence.

All filesystem operations are subject to Directory Access Policy and the relevant collection definition.

---

# 21. Performance and Resource Usage

Set Detection may be computationally expensive because visual grouping can require large numbers of candidate comparisons.

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

# 22. Threading

Parallel execution should be supported.

Worker count shall be configurable through the common module interface/configuration system.

Concurrent workers must not create conflicting Set state or duplicate physical directories for the same grouping operation.

---

# 23. Error Handling

If processing of an individual file or candidate relationship fails:

* the error shall be logged;
* unrelated work should continue where safe;
* incomplete Set membership must not be published as valid final state;
* a failed physical move must not be recorded as completed.

An execution-level database or consistency failure may stop the execution when continuing would risk corrupting Set state.

---

# 24. Logging

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
filesystem operations
errors
duration
```

---

# 25. Interaction with AI and FINAL

AI may contain temporary Set workspaces for groups that have not yet been assigned to a primary collection tree.

Once semantic classification is available, the Set may be physically moved into an existing valid primary tree and represented there as a Set directory.

FINAL remains controlled by Collection Definition at the primary-tree level. Set directories inside an already valid primary-tree destination may be created by an authorised workflow when permitted by the relevant access policy.

Thus:

```text
AI/Set workspace
        ↓
classification
        ↓
valid primary-tree destination
        ↓
primary tree / Universe / Character / 0001/
```

Set creation does not authorize creation of a new primary semantic destination.

---

# 26. Design Principles

The module follows these principles:

1. A Set is both a logical group and, in the organised collection, a physical directory.
2. Set identity is stored in the database, not in the directory name.
3. Files retain their SHA512 identity independently of Set membership.
4. Set grouping is about visual relationship, not semantic classification.
5. Set directories belong below an already valid primary collection destination.
6. AI may use temporary Set workspaces before final placement is known.
7. New primary-tree destinations remain user-controlled.
8. Uncertain merges, splits and destructive regrouping should be reviewed rather than guessed.
9. Modules remain independently executable and exchange persistent information through the database.
10. Collection Definition and Directory Access Policy determine where physical Set directories may exist.

---

# 27. Acceptance Criteria

The module is considered compliant when it can:

* identify meaningful groups of visually related files;
* store Set identity and membership in the database;
* represent classified Sets as physical subdirectories of valid primary-tree destinations;
* support temporary Set workspaces in AI;
* preserve file identity independently of Sets;
* support repeated independent execution;
* support conservative merge and split operations;
* use Review Queue for materially uncertain grouping decisions;
* avoid creating arbitrary new primary semantic directories;
* maintain consistency between database Set state and physical Set directories;
* operate efficiently enough for multi-million-image collections.

---

# End of DOC-109
