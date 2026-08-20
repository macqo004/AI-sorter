# DOC-109

# Set Detection and Grouping Module

**Project:** AI Image Collection Management System

**Document:** DOC-109

**Module:** Set Detection and Grouping

**Version:** 2.2

**Status:** Design Specification

**Depends on:** DOC-005, DOC-007, DOC-008, DOC-010, DOC-011, DOC-012, DOC-013, DOC-014, DOC-205, DOC-302

---

# 1. Purpose

The Set Detection and Grouping module identifies groups of visually related image files and represents those groups both logically in the database and, when authorized, physically as Set directories.

A Set is therefore not merely an analytical abstraction. In the organized collection, a Set is a physical subdirectory containing a group of visually related images.

Example:

```text
Anime/
└── Genshin Impact/
    └── Furina/
        ├── 0001/
        ├── 0002/
        └── 0003/
```

The database is the source of Set identity and membership state; the physical directory is the filesystem representation.

# 2. Scope

The module may analyse visual similarity, identify groups, create/update Set records, associate files with Sets, support creation of physical Set directories where authorized and provide grouped context through the database.

It shall not identify characters, universes or themes as its primary responsibility; decide the semantic primary tree by itself; silently replace user decisions; or invoke another module directly.

# 3. Definition of Set

A Set is a group of image files with a sufficiently strong visual relationship to be treated as one logical collection unit.

A Set does not automatically mean the same character, universe, artist, source or identical file content.

# 4. Example Collection Structure

```text
Primary Tree
└── Universe
    └── Character
        ├── 0001
        ├── 0002
        └── 0003
```

Exact hierarchy is determined by Collection Definition rather than hard-coded names or depths.

# 5. Invalid Set Examples

A Set must not contain unrelated images merely because they share colour, aspect ratio, filename pattern or general rendering style.

# 6. Module Independence

Set Detection is independently executable once eligible files have valid database identities. Scanner does not need to remain active and no module is invoked directly.

# 7. Input

The module reads current database state and may access corresponding images for visual comparison. Required identity information includes SHA512, file metadata, dimensions where available and current physical occurrence information.

Supporting Analysis Results may be consumed through the database.

# 8. Output

The module creates/updates Set information in the database and, when authorized, its physical directories.

A Set should include:

```text
set_id
status
created_at
updated_at
```

Membership associates Set identity with the relevant file identity and optional similarity/membership evidence.

# 9. Set Identity and Physical Directory

`set_id` is the logical identity of a Set. The physical path and numeric directory label are representations, not the logical identity.

# 10. Set Location in the Collection Hierarchy

A Set is normally the lowest physical classification level in an organized primary tree, but the exact hierarchy is determined by Collection Definition.

The module must not hard-code Anime, Monster Girls, Western Animation or any other root names.

# 11. Set Creation in AI / Transition Workspace

An authorized AI/transition workflow may create temporary Set workspaces for groups that do not yet belong to an established primary destination, for example:

```text
AI/Sets/0001/
AI/Sets/0002/
```

These are working structures, not FINAL collection definitions.

# 12. Set Directory Creation in Primary Trees

Once a Set has a valid primary-tree destination, an authorized workflow may create the Set directory below that existing destination.

Creating a Set directory inside an established primary destination is different from creating a new primary semantic branch.

# 13. Set Folder Naming

Numeric Set labels such as `0001` are physical labels only. They must not be interpreted as semantic classification levels.

Collection Definition Classification Boundaries remain authoritative.

# 14. Set Creation Criteria

New Sets require configured grouping criteria that represent meaningful visual relationships rather than generic similarities such as colour or file size alone.

# 15. Set Merging

The module may propose Set merges when evidence supports treating two Sets as one logical group. Ambiguous merges use Review Queue. Authorized merges must preserve database/filesystem consistency.

# 16. Set Splitting

A Set may be split when its members no longer form one coherent group. Ambiguous or materially organizational changes use Review Queue.

# 17. Review Queue Integration

Review Queue may be used for uncertain Set creation, merge, split, conflicting evidence or uncertain physical regrouping. User decisions have priority for the protected context.

# 18. Processing and Reprocessing

Set Detection may be executed repeatedly and independently.

Existing valid Set membership/grouping information may be reused where appropriate.

A change to the module implementation, visual model, similarity rules, thresholds or configuration does **not** automatically clear Set results and does not automatically trigger a new grouping run.

When the user wants complete recalculation using changed grouping logic, the user shall use **DOC-205 – Module Result Cleanup Utility** to clear the Set Detection result set and then run Set Detection again.

New files entering the scope or a SHA512 change may naturally require new grouping work for those files. A path or filename change without a SHA512 change does not create a new binary identity or Set identity by itself.

# 19. Database Access

The module reads File, Module, existing Set data, relevant Analysis Results and Collection Definition where required. It writes Set state, membership and execution data. It must not overwrite other modules' results or user decisions.

# 20. Filesystem Operations

When authorized, the module/workflow may create Set directories inside AI or inside an already valid primary-tree destination, move Set members, update membership/path state after successful operations, merge/split Set directories and remove obsolete empty Set directories.

It must not create a new FINAL primary-tree classification, arbitrary universe/character/theme roots, or move files across primary trees merely because of visual similarity.

# 21. Performance and Resource Usage

Set Detection may be computationally expensive and should use staged similarity filtering, inexpensive pre-filtering, batching, configurable workers and limited candidate comparisons. The entire collection must not be required in RAM.

# 22. Threading

Parallel execution should be supported with configurable worker count and appropriate consistency protection.

# 23. Error Handling

Per-file/candidate failures are logged and should not stop unrelated work where safe. Incomplete Set membership must not be published as final state. A failed physical move must not be recorded as completed.

# 24. Logging

Each execution creates a Module Execution record and summary log according to DOC-007 and DOC-011, including Set changes, physical operations and errors where applicable.

# 25. Interaction with AI and FINAL

AI may contain temporary Set workspaces for groups not yet assigned to a primary tree.

Once classification is available, an authorized workflow may move the Set into an existing valid primary tree and represent it there as a Set directory.

Set creation does not authorize creation of a new primary semantic destination.

# 26. Design Principles

1. A Set is both a logical group and, in the organized collection, a physical directory.
2. Set identity is stored in the database, not in the directory name.
3. Files retain their SHA512 identity independently of Set membership.
4. Set grouping is about visual relationship, not semantic classification.
5. Set directories belong below an already valid primary destination.
6. AI may use temporary Set workspaces before final placement is known.
7. New primary-tree destinations remain user-controlled.
8. Uncertain merges, splits and destructive regrouping use Review Queue.
9. Modules remain independently executable and exchange persistent information through the database.
10. Collection Definition and Access Policy determine where physical Set directories may exist.

# 27. Acceptance Criteria

The module is compliant when it can identify meaningful groups, store Set identity and membership, represent Sets as physical subdirectories of valid primary destinations, support AI Set workspaces, preserve file identity, execute independently and repeatedly, use Review Queue where needed, avoid arbitrary new primary semantic directories, maintain DB/filesystem consistency and support full recalculation through DOC-205 when the user explicitly requests it.

---

# End of DOC-109
