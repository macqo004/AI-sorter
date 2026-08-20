# DOC-203A

# Filename Rule Definitions

**Project:** AI Image Collection Management System

**Document:** DOC-203A

**Module:** File Renamer – Rule Definitions

**Version:** 2.0

**Status:** Draft

**Depends on:**

DOC-010
DOC-011
DOC-013
DOC-203

---

# 1. Purpose

This document defines the configurable rules used by the File Renamer module.

DOC-203 defines the Renamer Engine and execution behaviour.

DOC-203A defines what filename transformations are recognised and how they are configured.

Separating these responsibilities allows filename rules to evolve without redesigning the Renamer Engine.

---

# 2. Design Philosophy

Filename rules shall be:

* deterministic;
* explicit;
* conservative;
* independently configurable;
* independent of semantic image classification.

A rule must never assume that a filename fragment has a particular meaning unless the rule explicitly defines that pattern as meaningful.

When a rule cannot safely determine that a transformation is correct, the original filename must be preserved and Review Queue may be used.

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

Additional properties may be introduced when justified.

The rule definition must remain understandable to a technically competent user.

---

# 4. Rule Independence

Rules may be enabled or disabled independently.

The system must not assume that all rules should always run.

Example:

```text
☑ Remove Duplicate Suffixes
☑ Replace Spaces
☐ Transliterate Characters
☐ Convert To Lowercase
☐ WWW Normalization
```

Only enabled rules participate in that execution.

The same rule may be run again later against the current filename.

---

# 5. Rule Ordering

When several rules are executed in one Renamer execution, they are applied sequentially.

Rules may have configurable execution priority.

Where two rules have the same priority, their configuration order determines execution order.

The project does not require a universal hard-coded rule order.

---

# 6. Rule Categories

Categories are organisational metadata and do not themselves determine execution order.

Possible categories include:

```text
DUPLICATE_REMOVAL
CHARACTER_REPLACEMENT
NORMALIZATION
WWW_PREPARATION
TRANSLITERATION
USER_DEFINED
```

New categories may be added later.

---

# 7. Pattern Matching

A rule may act only on patterns explicitly defined by the rule.

Possible patterns include:

```text
trailing numeric suffix
specific duplicate suffix format
duplicated separator
multiple consecutive spaces
specific prefix
specific suffix
specific character sequence
```

A visual resemblance to a known pattern is not sufficient when the rule could remove meaningful filename information.

---

# 8. Duplicate / Copy Suffixes

The rule set may contain explicit patterns such as:

```text
(1)
(25)
[1]
{3}
```

provided that the configured rule identifies the entire pattern and its location in the filename.

A suffix such as:

```text
_1280_720
```

must not be treated as a duplicate suffix unless a specific rule explicitly defines it that way.

Likewise:

```text
_artist (1)
```

must not be reduced to a different semantic name simply because a numeric suffix is present.

---

# 9. Conservative Filename Semantics

Rules must not attempt to understand the semantic meaning of a complete filename.

For example:

```text
furina (1).jpg
```

may safely match a duplicate-suffix rule.

But:

```text
furina_drawn_by_artist (1).jpg
```

must not be transformed into:

```text
furina.jpg
```

unless a separate explicit rule defines that complete transformation.

---

# 10. Replacement Definition

Each rule shall define its replacement operation deterministically.

Example:

```text
Input:
furina (1).jpg

Rule:
Remove Duplicate Suffixes

Output:
furina.jpg
```

A replacement must not depend on undocumented heuristics.

---

# 11. Conflict Policy

A rule must defer to DOC-203 for actual filesystem conflict handling.

At minimum, a rule must be capable of indicating that a proposed filename is unsafe when the resulting name already exists.

The Renamer Engine must not overwrite an existing file and must not silently invent an operating-system suffix.

---

# 12. Ambiguous Matches

If a filename appears to match a rule but the rule cannot determine the intended transformation safely, no automatic modification shall occur.

Example:

```text
example (copy).jpg
```

The rule must not automatically assume that `(copy)` is disposable unless that exact pattern is explicitly defined as safe.

The case may be sent to Review Queue.

---

# 13. Review Queue Integration

Ambiguous rule matches may generate Review Queue entries according to DOC-013.

The entry should contain:

```text
module
rule_id
current filename
proposed filename
reason
```

The existence of a proposed transformation does not authorize its execution.

---

# 14. Configuration

The user shall be able to:

* enable or disable rules;
* configure rule parameters where supported;
* configure execution priority;
* inspect the active rule set.

The rule configuration may be stored by the Configuration Manager according to DOC-008.

The rule definition itself must not depend on hard-coded collection names or fixed paths.

---

# 15. Versioning and Reproducibility

Rule definitions should have explicit versions.

A completed rename execution should record the rule version used so that the resulting change can be understood and, where appropriate, reversed.

Changing a rule does not automatically imply that every existing filename must be renamed again. Re-execution remains user-initiated.

---

# 16. Scope of Rules

Filename rules operate on file names only.

Rules do not:

* modify file contents;
* alter SHA512;
* alter file identity;
* classify images;
* move files between directories;
* modify directory names.

Directory renaming, if ever required, should be treated as a separate operation with its own specification.

---

# 17. Logging

Execution of every rule shall produce sufficient information for DOC-011 logging.

The record should identify:

```text
rule_id
rule_version
file identity
original filename
resulting filename
result
```

---

# 18. Future Extensions

Possible future extensions include:

* custom regular-expression rules;
* user-defined parameterised rules;
* rule import/export;
* shared rule libraries;
* project-specific rule profiles.

All future rules must remain compatible with the conservative transformation principle.

---

# 19. Acceptance Criteria

The rule system is compliant when:

* rules are independently configurable;
* transformations are deterministic;
* patterns are explicit;
* ambiguous matches are not automatically executed;
* conflict handling remains under DOC-203;
* rules do not modify file identity or image content;
* rule versions can be recorded for reproducibility;
* new rules can be added without redesigning the Renamer Engine.

---

# End of DOC-203A
