# DOC-203A

# Filename Rule Definitions

**Project:** AI Image Collection Management System

**Document:** DOC-203A

**Module:** File Renamer – Rule Definitions

**Version:** 2.1

**Status:** Draft

**Depends on:**

DOC-010
DOC-011
DOC-013
DOC-203

---

# 1. Purpose

This document defines the deterministic filename transformations used by the File Renamer module.

DOC-203 defines the Renamer Engine and execution behaviour.

DOC-203A defines individual filename rules, their patterns, scope, and safety constraints.

Separating these responsibilities allows rules to evolve without redesigning the Renamer Engine. fileciteturn246file0

---

# 2. Design Philosophy

Filename rules shall be:

* deterministic;
* explicit;
* conservative;
* independently configurable;
* independent of semantic image classification.

A rule must operate on an explicitly defined filename pattern and must not infer semantic meaning from arbitrary text.

When a transformation would make a filename unsafe or empty, the original filename must be preserved.

---

# 3. Rule Structure

Each rule should define at least:

```text
rule_id
rule_name
description
enabled
execution_priority
trigger/pattern
replacement
conflict_policy
version
```

The executable Renamer Engine accepts rules independently and applies them sequentially.

---

# 4. Rule Ordering

Rules execute in the order supplied to the Renamer Engine.

The output of one rule becomes the input of the next rule.

Current built-in ordering:

```text
1. remove_duplicate_suffix@1.0
2. remove_leading_non_alphanumeric@1.0
```

This ordering means that a name such as:

```text
"  Furina (1).jpg"
```

is transformed as:

```text
"  Furina.jpg"
"Furina.jpg"
```

---

# 5. Rule Categories

Categories remain organisational metadata and do not themselves define execution order.

Possible categories include:

```text
DUPLICATE_REMOVAL
CHARACTER_REPLACEMENT
NORMALIZATION
WWW_PREPARATION
TRANSLITERATION
USER_DEFINED
```

---

# 6. Implemented Rule: Remove Duplicate Suffix

**Rule ID:** `remove_duplicate_suffix`

**Version:** `1.0`

**Category:** `DUPLICATE_REMOVAL`

### 6.1 Purpose

Remove an explicit numeric copy suffix from the end of the filename stem.

### 6.2 Accepted patterns

```text
(1)
(25)
[1]
{3}
```

Optional whitespace directly before the bracketed suffix is part of the removable pattern.

### 6.3 Examples

```text
furina (1).jpg      -> furina.jpg
furina [25].png     -> furina.png
furina {3}.webp     -> furina.webp
furina.jpg          -> furina.jpg
```

### 6.4 Explicit exclusions

The rule does not remove arbitrary textual suffixes such as:

```text
(copy)
(final)
artist
```

It does not treat values such as `_1280_720` as duplicate suffixes.

### 6.5 Safety

If removing the suffix would leave an empty stem, the original filename is preserved.

---

# 7. Implemented Rule: Remove Leading Non-Alphanumeric

**Rule ID:** `remove_leading_non_alphanumeric`

**Version:** `1.0`

**Category:** `NORMALIZATION`

### 7.1 Purpose

Remove the complete leading sequence of Unicode characters for which `str.isalnum()` returns false from the filename stem.

This includes, among others:

```text
spaces
_
-
+
.
,
(
)
[
]
{
}
@
#
$
%
&
```

The rule is intentionally broader than a simple leading-space cleanup.

### 7.2 Examples

```text
"  __--sample.png"  -> "sample.png"
"---_ image.png"    -> "image.png"
"_001_test.webp"    -> "001_test.webp"
"---Furina.jpg"     -> "Furina.jpg"
```

A clean filename is left unchanged:

```text
Furina.jpg         -> Furina.jpg
Furina_-test.jpg   -> Furina_-test.jpg
```

### 7.3 Safety

A filename is not modified when its stem contains no alphanumeric character after the leading sequence.

Therefore:

```text
---.jpg -> --- .jpg
```

is conceptually **unchanged**; the actual stored filename remains exactly `---.jpg`.

The rule must never generate an empty stem or an extension-only filename.

---

# 8. Extension Handling

Rules operate on the filename stem and preserve the existing extension unchanged.

Examples:

```text
"  sample.PNG" -> "sample.PNG"
"_001.webp"    -> "001.webp"
```

The rules do not convert extensions to lower case and do not change file format.

---

# 9. Pattern Matching

A rule may act only on the pattern explicitly defined by that rule.

A visual resemblance to a known pattern is not sufficient.

No rule may remove meaningful filename content merely because it contains punctuation or bracketed text.

---

# 10. Conservative Filename Semantics

Rules do not attempt to understand the semantic meaning of a complete filename.

For example:

```text
furina_drawn_by_artist (1).jpg
```

may become:

```text
furina_drawn_by_artist.jpg
```

under the duplicate-suffix rule, but the filename body is otherwise preserved.

Likewise:

```text
artist (copy).jpg
```

is not changed by `remove_duplicate_suffix` because `(copy)` is not an explicit numeric duplicate suffix.

---

# 11. Conflict Policy

The Renamer Engine, not an individual rule, owns filesystem conflict handling.

The engine must not overwrite an existing file and must not silently invent an operating-system suffix.

When multiple proposals target the same destination, the complete plan is rejected before execution.

---

# 12. Ambiguous Matches

When a rule cannot safely determine its transformation, the original filename is preserved.

The current built-in rules avoid semantic guessing and only perform explicit mechanical transformations.

---

# 13. Scope

Filename rules operate on file names only.

They do not:

* modify file contents;
* alter SHA-512;
* alter file identity;
* classify images;
* move files between directories;
* rename directories.

---

# 14. Versioning and Reproducibility

Each rule has an explicit version.

A completed rename execution should record the rule versions used so that the transformation can be reproduced and understood.

Changing a rule does not imply that existing files must be renamed again.

---

# 15. Future Rules

The architecture permits additional independently configurable rules such as:

```text
multiple-space normalization
character replacement
transliteration
lowercase conversion
WWW preparation
user-defined regular expressions
```

These are not part of the current built-in rule set unless implemented and documented in a later version.

---

# 16. Acceptance Criteria

The rule definition system is compliant when:

* each implemented rule has an explicit identifier and version;
* rules are deterministic;
* rules are applied sequentially;
* the current two built-in rules behave exactly as specified above;
* filenames without matches remain unchanged;
* unsafe empty/extension-only results are prevented;
* conflict handling remains under DOC-203;
* adding a new rule does not require redesigning the engine.

---

# End of DOC-203A
