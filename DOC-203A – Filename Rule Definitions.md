# DOC-203A – Filename Rule Definitions

## 1. Purpose

This document defines the rule system used by the File Renamer Module.

The purpose of the Rule Engine is to provide a configurable, deterministic and safe mechanism for modifying filenames without requiring changes to the File Renamer implementation.

The Rule Engine defines **what** operations may be performed.

The File Renamer defines **how** and **when** those operations are executed.

---

# 2. Design Philosophy

The Rule Engine is designed around the following principles:

* rules are deterministic;
* rules never attempt to interpret the meaning of filenames;
* rules operate only on explicitly defined patterns;
* ambiguous situations are never resolved automatically;
* user-defined rules take precedence over assumptions.

Whenever a filename cannot be processed with sufficient certainty, the operation shall not be performed automatically.

Instead, the module shall create a Review Queue entry according to DOC-013.

---

# 3. Rule Structure

Every filename rule shall contain at minimum:

* Rule Name
* Description
* Enabled / Disabled state
* Execution Priority
* Trigger
* Pattern Definition
* Replacement Definition
* Conflict Policy
* Logging Behaviour

Future versions may introduce additional attributes.

---

# 4. Rule Execution

Rules are executed individually.

The user may enable or disable each rule independently.

The Rule Engine shall never assume that all available rules should be executed together.

Example:

```text
☑ Remove Numeric Suffixes

☐ Replace Spaces

☐ Transliterate Non-Latin Characters

☐ Convert To Lowercase

☐ WWW Filename Normalization
```

Only enabled rules are executed.

---

# 5. Rule Priority

Rules are executed according to their configured priority.

Higher priority rules execute first.

Rules with identical priority execute in configuration order.

The project does not require a fixed execution order.

Users may change the enabled rule set without affecting unrelated rules.

---

# 6. Rule Categories

Rules may belong to one of the following categories:

* Duplicate Removal
* Character Replacement
* Filename Normalization
* WWW Preparation
* Transliteration
* User Defined
* Future Categories

Categories are informational and do not influence execution order.

---

# 7. Pattern Matching

Rules shall operate only on explicitly defined patterns.

Examples:

* trailing numeric suffix
* duplicated separator
* multiple consecutive spaces
* specific filename prefix
* specific filename suffix

Rules shall never remove text based solely on assumptions.

---

# 8. Replacement Rules

Each rule defines exactly how the filename shall be modified.

Example:

```text
Before

furina (1).jpg
```

↓

```text
After

furina.jpg
```

The replacement operation shall always be deterministic.

---

# 9. Scope

Rules operate only on filenames.

Rules shall never modify:

* directory structure;
* database metadata;
* image contents;
* SHA512 values;
* file identifiers.

Directory names may be supported by future versions.

---

# 10. Conflict Detection

Before renaming a file, the Rule Engine shall verify that the resulting filename does not already exist.

Example:

```text
Existing:

furina.jpg

Current:

furina (1).jpg
```

Target:

```text
furina.jpg
```

Since the destination already exists, the rule shall not perform the rename automatically.

Conflict handling is defined by DOC-203.

---

# 11. Ambiguous Matches

Some filenames may satisfy a rule while simultaneously containing information that should potentially be preserved.

The Rule Engine shall never attempt to determine semantic meaning.

Example:

```text
example (copy).jpg
```

Whether "(copy)" represents:

* duplicate information;
* user annotation;
* original filename;

cannot be determined automatically.

Such cases shall generate a Review Queue entry.

---

# 12. Review Queue Integration

Whenever a rule cannot safely determine whether a transformation should be performed, it shall generate a Review Queue entry according to DOC-013.

The original filename shall remain unchanged.

Review Queue entries should include:

* original filename;
* proposed filename;
* matching rule;
* reason for uncertainty.

---

# 13. Logging

Each executed rule shall generate log entries according to DOC-011.

The log shall contain:

* executed rule;
* affected file;
* rename result;
* skipped operations;
* detected conflicts;
* Review Queue creation.

---

# 14. User Configuration

Rules shall be configurable.

At minimum, the user shall be able to:

* enable or disable rules;
* modify execution order;
* create additional rule definitions in future versions.

Changing rule configuration shall not require modifications to the File Renamer implementation.

---

# 15. Safety Principles

The Rule Engine follows the principle:

> **Filename preservation is preferred over incorrect modification.**

If a rule cannot determine with sufficient certainty that a transformation is correct, no modification shall be performed.

The original filename shall always be preserved unless the rule matches deterministically.

---

# 16. Future Extensions

Future versions may extend the Rule Engine with support for:

* custom regular expression rules;
* directory renaming rules;
* project-specific rule sets;
* import and export of rule collections;
* shared rule libraries;
* module-specific rule profiles.

Such extensions shall remain fully compatible with the safety principles defined in this document.
