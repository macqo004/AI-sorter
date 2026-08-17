# DOC-203

# File Renamer Module

**Project:** AI Image Collection Management System

**Document:** DOC-203

**Module:** File Renamer

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
DOC-203A

---

# 1. Purpose

The File Renamer module provides a controlled and deterministic mechanism for modifying filenames within the project.

The module is intentionally conservative. It operates on filenames only and must never modify image contents, SHA512 identity or file identity.

The module may operate on files located in TODO, AI, primary collection trees, Themes or FINAL, provided that the selected scope and Directory Access Policy permit the requested modification.

---

# 2. Responsibilities

The File Renamer shall:

* rename files according to enabled filename rules;
* process a user-selected scope recursively when configured;
* detect filename conflicts before modification;
* synchronize successful filesystem renames with the database;
* preserve file identity;
* generate Undo information;
* create Review Queue entries for ambiguous or unsafe cases;
* record execution history and results.

The File Renamer shall not:

* modify image contents;
* calculate or change SHA512 as part of a rename operation;
* change file identity;
* create or modify collection classification;
* move files between collection trees as part of filename renaming;
* rename directories;
* invoke other modules directly.

---

# 3. Identity and Database Rules

The module follows DOC-012.

For a successful rename:

```text
SHA512   = unchanged
file_id  = unchanged
current_path = updated
filename = updated
```

A rename does not create a new file identity or invalidate analysis results.

Example:

```text
Before:
file_id = 152
SHA512 = AAAAA
current_path = AI/Furina (1).jpg

After:
file_id = 152
SHA512 = AAAAA
current_path = AI/Furina.jpg
```

The database must be updated only after the filesystem operation has succeeded and been verified.

---

# 4. Architecture

The module consists of two logical layers:

```text
Renamer Engine
      ↓
Filename Rules
```

The **Renamer Engine** manages scope, execution, conflict detection, filesystem changes, database synchronization, logging, Undo and Review Queue integration.

**DOC-203A** defines the configurable filename rules and their behaviour.

The engine must not contain hard-coded knowledge of every filename pattern.

---

# 5. Rule Independence

Rules are independently configurable.

A user may execute:

```text
Remove Duplicate Suffixes
```

then later:

```text
Replace Spaces
```

and later again:

```text
Remove Duplicate Suffixes
```

Each execution evaluates the current filename.

The engine must not assume that another rule was previously executed.

When several rules are selected in one execution, their configured execution order is respected. The output of one rule becomes the input of the next rule.

---

# 6. Working Scope

The user explicitly selects the starting root and processing options.

The module may process recursively according to the configured scope and Collection Definition/traversal rules where applicable.

Directory names are never changed by this module.

The module must respect Directory Access Policy:

```text
PROTECTED / READ_ONLY
    → no filesystem rename

MODIFY
    → rename permitted where the module's rules allow it
```

The module shall not assume that a physical tree named `TODO`, `AI` or `FINAL` has a universal meaning outside Collection Definition.

---

# 7. Safe Transformation Principle

A rename is performed only when the selected rule deterministically matches the filename and defines the transformation.

Example:

```text
furina (1).jpg
        ↓
furina.jpg
```

may be valid for an enabled duplicate-suffix rule.

The module must not infer that:

```text
furina_drawn_by_artist (1).jpg
```

should become:

```text
furina.jpg
```

unless an explicit rule defines that transformation.

When uncertain, the original filename is preserved.

---

# 8. Filename Conflict Handling

Before every physical rename, the module shall verify that the target filename does not already exist in the same destination directory.

Example:

```text
furina.jpg
furina (1).jpg
```

If removing `(1)` would produce an existing filename, the rename shall not be performed automatically.

The affected file remains unchanged.

A Review Queue entry may be generated according to DOC-013.

The conflict must not stop processing of unrelated files.

The module must never use destructive overwrite or arbitrary operating-system suffixes such as `(1)` to resolve a conflict.

---

# 9. Review Queue Integration

Review Queue shall be used when the module cannot safely determine the intended transformation.

Typical cases include:

* ambiguous suffixes;
* filename conflicts;
* unsupported patterns;
* permission or filesystem situations requiring user intervention.

A review item may contain:

```text
module
rule
file_id
SHA512
current path
current filename
proposed filename
reason
confidence where applicable
```

A Review Queue suggestion is not an authorization to rename the file.

The user decision remains authoritative for the protected context.

---

# 10. Dry Run

The module shall support Dry Run.

During Dry Run:

* files are analysed;
* proposed filenames are generated;
* conflicts are detected;
* Review Queue entries may be generated;
* database current-path state is not changed;
* files are not renamed.

Example:

```text
Current:
furina (1).jpg

Proposed:
furina.jpg
```

---

# 11. Execution

The recommended physical operation order is:

```text
1. Read current file state
2. Evaluate rule
3. Validate target name
4. Check access policy
5. Check conflict
6. Perform filesystem rename
7. Verify result
8. Update current_path / filename in database
9. Store Undo information
10. Write event/log information
```

The database must not report the rename as successful before the filesystem operation has succeeded.

---

# 12. Undo Information

Every successful rename should generate persistent Undo information independent from ordinary logs.

At minimum it should contain:

```text
execution_id
rule
file_id
SHA512
original path
original filename
new path
new filename
timestamp
```

Undo shall restore the previous filename without changing the file's SHA512 identity.

The exact storage implementation is defined by the database implementation.

---

# 13. Logging

Each execution shall create a Module Execution record according to DOC-007 and logs according to DOC-011.

The execution summary should include:

```text
starting scope
rules executed
processed
renamed
skipped
conflicts
Review Queue items
errors
Undo records
duration
```

Individual rename events should identify the file SHA512 where available.

---

# 14. Error Handling

Errors affecting one file shall not stop unrelated processing where safe.

Typical errors include:

```text
permission denied
file locked
filename conflict
filesystem failure
database synchronization failure
unsupported filename
```

A database synchronization failure after a filesystem rename is a critical consistency condition and shall be logged and handled according to the module's recovery procedure. The system must not silently pretend that the rename did not happen.

---

# 15. Execution Independence

File Renamer is an independently executable module.

It does not require another analysis module to be running.

The module may be executed repeatedly and in any order relative to other project modules.

For example:

```text
Day 1: Renamer
Day 2: IRL Analysis
Day 3: Renamer
Day 4: Universe Analysis
Day 5: Renamer
```

Each execution uses the current filesystem and database state.

---

# 16. Performance

The collection may contain millions of files.

The implementation should therefore:

* process files incrementally;
* avoid loading the entire collection into memory;
* use configurable batching where beneficial;
* use parallel workers only where deterministic behaviour and filesystem safety can be preserved;
* avoid modifying the same file concurrently;
* preserve database consistency.

Performance optimisation must not compromise deterministic transformations or safety.

---

# 17. User Control

The user controls at minimum:

* starting scope;
* recursive processing;
* enabled rules;
* rule ordering;
* Dry Run / Execute mode;
* execution start.

The File Renamer shall never start itself as a consequence of another module execution.

---

# 18. Integration with Other Modules

The File Renamer does not invoke other modules.

Its information flow is:

```text
Filesystem + Database
        ↓
File Renamer
        ↓
Filesystem + Database
```

Other modules may observe the updated filename/path state through the shared database.

The Renamer must not modify analysis results owned by other modules.

---

# 19. Safety Principles

The File Renamer shall follow these principles:

* never guess filename meaning;
* never remove information without an explicit matching rule;
* never overwrite an existing file;
* never silently resolve conflicts;
* never modify image contents;
* never modify SHA512;
* never create a new file identity because of a rename;
* never modify directory names;
* preserve the original filename whenever uncertainty exists.

---

# 20. Acceptance Criteria

The module is considered compliant when it can:

* perform deterministic filename transformations;
* use independently configurable rules defined by DOC-203A;
* process user-selected scopes safely;
* respect Directory Access Policy;
* preserve SHA512 and file identity;
* update database path state only after successful filesystem changes;
* detect and safely handle filename conflicts;
* support Dry Run;
* integrate with Review Queue;
* provide persistent Undo information;
* continue after recoverable per-file failures;
* execute independently and repeatedly on large collections.

---

# End of DOC-203
