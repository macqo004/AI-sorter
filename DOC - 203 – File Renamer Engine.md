# DOC-203

# File Renamer Engine

**Project:** AI Image Collection Management System

**Document:** DOC-203

**Module:** File Renamer

**Version:** 1.0

**Status:** Draft

**Depends on:**

DOC-007
DOC-010
DOC-011
DOC-013
DOC-203A

---

# 1. Purpose

DOC-203 defines the executable Renamer Engine.

The engine applies deterministic filename rules defined by DOC-203A and performs filesystem renames only after a complete rename plan has been validated.

The engine operates on file names only. It does not modify file contents, SHA-512 values, file identity, directory names, or image-analysis results.

---

# 2. Responsibilities

The Renamer Engine shall:

* accept a set of filename rules;
* apply rules sequentially;
* produce rename proposals before changing the filesystem;
* support dry-run planning;
* reject destination collisions;
* reject duplicate destinations within one execution plan;
* execute a validated plan using temporary names when needed to avoid in-plan destination conflicts;
* report the rules responsible for each proposal.

The engine shall not silently overwrite an existing file or invent an operating-system collision suffix.

---

# 3. Rule Pipeline

Rules are applied in the order supplied to the engine.

Example:

```text
Input
  "  Furina (1).jpg"

Rule 1: Remove Duplicate Suffix
  "  Furina.jpg"

Rule 2: Remove Leading Non-Alphanumeric
  "Furina.jpg"
```

The output of one rule is the input to the next rule.

---

# 4. Current Built-In Rules

The current built-in rule set contains:

```text
remove_duplicate_suffix@1.0
remove_leading_non_alphanumeric@1.0
```

The implementation is intentionally conservative.

## 4.1 Remove Duplicate Suffix

Removes an explicit numeric suffix at the end of the filename stem when formatted as:

```text
(1)
(25)
[1]
{3}
```

Optional whitespace immediately before the bracketed suffix is also removed.

Examples:

```text
furina (1).jpg      -> furina.jpg
furina [25].png     -> furina.png
furina {3}.webp     -> furina.webp
furina.jpg          -> furina.jpg
```

The rule does not remove arbitrary text such as `(copy)` and does not treat strings such as `_1280_720` as duplicate suffixes.

## 4.2 Remove Leading Non-Alphanumeric

Removes the complete leading run of Unicode characters for which `isalnum()` is false from the filename stem.

Examples:

```text
"  __--sample.png"  -> "sample.png"
"---_ image.png"    -> "image.png"
"_001_test.webp"    -> "001_test.webp"
"---Furina.jpg"     -> "Furina.jpg"
```

The rule does not modify an already-clean filename and does not change anything when the stem contains no alphanumeric character after the leading run.

Therefore:

```text
---.jpg -> --- .jpg
```

is **conceptually unchanged**; the actual filename remains exactly `---.jpg`.

A filename consisting only of punctuation is preserved rather than converted into an empty or extension-only filename.

---

# 5. Planning

Planning must occur before filesystem modification.

For every source file:

1. verify that the source is a regular file;
2. apply the enabled rules sequentially;
3. compare the transformed name with the current name;
4. omit unchanged files from the executable plan;
5. create a destination in the same directory as the source;
6. validate destination collisions.

The planner is deterministic for a fixed source list and fixed rule configuration.

---

# 6. Collision Policy

The engine shall refuse a plan when:

* a destination already exists outside the same rename plan;
* two proposals target the same destination;
* a source disappears before execution;
* a temporary execution name already exists.

The engine shall never generate `_1`, `(1)`, or another automatic suffix to resolve a collision.

Collision handling belongs to the execution policy and may later be extended with Review Queue integration.

---

# 7. Batch Execution

Before execution, the complete plan is validated.

During execution, source files are first moved to private temporary names and are then moved to their final destinations.

This two-stage operation prevents a destination from being occupied by another rename already present in the same validated plan.

Rollback after an unexpected filesystem failure is best-effort and must never overwrite an existing path.

---

# 8. Dry-Run

Dry-run is the default CLI mode.

A dry-run:

* reads directory entries;
* evaluates rules;
* reports proposed changes;
* may write a CSV report;
* does not rename files.

The user must explicitly provide `--apply` to modify the filesystem.

---

# 9. CLI

The packaged command is:

```text
ai-sorter-renamer <root>
```

Options:

```text
--recursive / --no-recursive
--apply
--csv <path>
```

Example:

```text
ai-sorter-renamer "M:\\anime\\5-toubun_no_hanayome"
```

This performs a dry-run.

To execute the proposed renames:

```text
ai-sorter-renamer "M:\\anime\\5-toubun_no_hanayome" --apply
```

---

# 10. Deterministic Reporting

Every proposal reports:

```text
source
 destination
rule
reason
```

Rule information contains the rule identifier and version, for example:

```text
remove_duplicate_suffix@1.0
remove_leading_non_alphanumeric@1.0
```

---

# 11. Scope

The initial implementation operates on regular files returned by directory traversal.

It does not rename directories.

It does not change file contents.

It does not recalculate SHA-512.

It does not update database records directly.

Integration with the project database, execution history, Review Queue, and GUI may be added through future module integration work.

---

# 12. Safety Requirements

The Renamer Engine must:

* default to dry-run at the CLI layer;
* refuse destination overwrites;
* preserve files when a destination collision is detected;
* preserve filenames that would become empty or extension-only;
* keep rule transformations deterministic;
* use explicit rule versions;
* avoid hidden semantic interpretation of filenames.

---

# 13. Future Extensions

Possible future rules include:

```text
multiple-space normalization
character replacement
transliteration
lowercase conversion
WWW preparation
user-defined regex rules
```

These are not part of the current built-in rule set unless explicitly implemented and documented in a later version.

---

# 14. Acceptance Criteria

The implementation is compliant when:

* the engine can accept independent rules;
* rules execute sequentially;
* dry-run produces proposals without filesystem changes;
* `--apply` executes only a validated plan;
* existing destinations are never overwritten;
* duplicate destinations are rejected;
* the current built-in rules produce the transformations specified by DOC-203A;
* unit tests cover rule behaviour and collision protection.

---

# End of DOC-203
