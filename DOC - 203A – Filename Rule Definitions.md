# DOC-203A

# Filename Rule Definitions

**Project:** AI Image Collection Management System

**Document:** DOC-203A

**Module:** File Renamer – Rule Definitions

**Version:** 2.2

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

Separating these responsibilities allows rules to evolve without redesigning the Renamer Engine.

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

The output of one rule becomes the input to the next rule.

Current built-in ordering:

```text
1. remove_duplicate_suffix@1.0
2. remove_auto_conflict_suffix@1.0
3. remove_leading_non_alphanumeric@1.0
4. remove_trailing_non_alphanumeric@1.0
5. remove_duplicate_image_extension@1.0
```

This ordering means that an automatically generated `_x` conflict marker is stripped before ordinary filename normalization. The engine then decides whether the clean name is currently available. If it is still occupied, the existing `_x` marker is retained rather than generating another suffix.

Example:

```text
sample.jpg       -> sample.jpg
sample_x.jpg     -> sample_x.jpg   (while sample.jpg exists)
```

After `sample.jpg` is removed:

```text
sample_x.jpg     -> sample.jpg
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

# 7. Implemented Rule: Remove Auto-Conflict Suffix

**Rule ID:** `remove_auto_conflict_suffix`

**Version:** `1.0`

**Category:** `DUPLICATE_REMOVAL`

### 7.1 Purpose

Remove the Renamer's own automatically generated conflict suffix so that a later run can restore the clean filename when the original conflict no longer exists.

### 7.2 Accepted patterns

```text
_x
_x2
_x3
...
```

The suffix is matched only at the end of the filename stem and is case-insensitive.

### 7.3 Examples

When the clean destination is free:

```text
sample_x.jpg      -> sample.jpg
sample_x2.jpg     -> sample.jpg
```

When the clean destination is still occupied, the engine conflict policy restores the `_x` form instead of repeatedly changing the name.

```text
sample.jpg exists
sample_x.jpg      -> sample_x.jpg
```

### 7.4 Safety

The rule is reversible and engine-aware. It does not force a rename when removing `_x` would recreate a current collision.

The `_x` marker is therefore reserved for the Renamer's own conflict-resolution scheme. A filename ending in `_x` may still be preserved when the clean destination is occupied.

---

# 8. Implemented Rule: Remove Leading Non-Alphanumeric

**Rule ID:** `remove_leading_non_alphanumeric`

**Version:** `1.0`

**Category:** `NORMALIZATION`

### 8.1 Purpose

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

### 8.2 Examples

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

### 8.3 Safety

A filename is not modified when its stem contains no alphanumeric character after the leading sequence.

Therefore:

```text
---.jpg -> --- .jpg
```

is conceptually **unchanged**; the actual stored filename remains exactly `---.jpg`.

The rule must never generate an empty stem or an extension-only filename.

---

# 9. Implemented Rule: Remove Trailing Non-Alphanumeric

**Rule ID:** `remove_trailing_non_alphanumeric`

**Version:** `1.0`

**Category:** `NORMALIZATION`

### 9.1 Purpose

Remove the complete trailing sequence of Unicode characters for which `str.isalnum()` returns false from the filename stem.

### 9.2 Examples

```text
5_.jpg            -> 5.jpg
5---.png          -> 5.png
5___--_.webp      -> 5.webp
Furina_-test.jpg  -> Furina_-test.jpg
```

The rule removes only the trailing sequence. Characters in the middle of the filename remain unchanged.

### 9.3 Safety

If removing the trailing sequence would leave an empty stem, the original filename is preserved.

---

# 10. Implemented Rule: Remove Duplicate Image Extension

**Rule ID:** `remove_duplicate_image_extension`

**Version:** `1.0`

**Category:** `NORMALIZATION`

### 10.1 Purpose

Remove one repeated, known image extension immediately before the final image extension.

### 10.2 Recognised image extensions

```text
.jpg
.jpeg
.png
.webp
.gif
.bmp
.pns
```

Matching is case-insensitive.

### 10.3 Examples

```text
5.jpg.png       -> 5.png
image.jpeg.jpg  -> image.jpg
foo.webp.png    -> foo.png
```

Normal names remain unchanged:

```text
foo.version.jpg -> foo.version.jpg
foo.txt.jpg     -> foo.txt.jpg
foo.jpg         -> foo.jpg
```

### 10.4 Safety

The rule does not remove arbitrary dotted text. It only removes a recognised image extension immediately preceding the final recognised image extension.

---

# 11. Conflict Policy

The Renamer Engine, not an individual rule, owns filesystem conflict handling.

The engine must never overwrite an existing file.

When a clean transformed destination is occupied, the engine automatically selects a free `_x` variant:

```text
sample.jpg       exists
sample source    -> sample_x.jpg
```

For subsequent conflicts in the same namespace:

```text
sample.jpg       exists
sample_x.jpg     exists
sample source    -> sample_x2.jpg
```

The `_x` suffix is deliberately reversible. The `remove_auto_conflict_suffix` rule removes it during planning, and conflict resolution restores it only when necessary.

A file already carrying `_x`/`_x2` is not forcibly renamed while its clean destination remains occupied. This avoids oscillating names on repeated Renamer runs.

No operating-system-generated suffix such as `" (1)"` is used by the Renamer's conflict handler.

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
* the five current built-in rules behave exactly as specified above;
* filenames without matches remain unchanged;
* unsafe empty/extension-only results are prevented;
* conflict handling remains under DOC-203;
* `_x` conflict markers can be removed when their clean destination becomes free;
* adding a new rule does not require redesigning the engine.

---

# End of DOC-203A
