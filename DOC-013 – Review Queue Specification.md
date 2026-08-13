# DOC-013 – Review Queue Specification

## 1. Purpose

This document defines the Review Queue mechanism used throughout the project.

The Review Queue is a centralized system for collecting operations that require user verification before execution or classification.

The purpose of the Review Queue is to ensure that no module performs uncertain or potentially destructive operations automatically.

The Review Queue is intended to assist the user, not replace user decisions.

---

# 2. Design Philosophy

The project follows the principle:

> **The system shall never guess when confidence is insufficient.**

Whenever a module cannot make a decision with sufficiently high confidence, it shall:

* skip the operation;
* create a Review Queue entry;
* continue processing remaining files.

The existence of Review Queue entries shall never stop module execution unless explicitly configured by the user.

---

# 3. Scope

The Review Queue may be used by any module.

Examples include:

* File Renamer
* Universe Analysis
* Character Analysis
* Theme Analysis
* Collection Consistency Checker
* Migration Queue
* future modules

Modules are encouraged to use the Review Queue instead of making assumptions.

---

# 4. Review Queue Entry

Each Review Queue entry shall contain enough information for the user to understand why the operation was not performed.

Minimum information:

* unique review identifier;
* module name;
* date and time;
* affected file_id (if available);
* SHA512 (if available);
* current file path;
* operation type;
* reason for review;
* suggested action;
* confidence level (if applicable).

---

Example:

```text
Review ID:
RQ-000001

Module:
File Renamer

File:
AI/Games/Genshin/Furina/furina (copy).jpg

Operation:
Filename normalization

Reason:
Filename matches multiple rename rules.

Suggested action:
Review manually.

Confidence:
Low
```

---

# 5. Review Categories

Every Review Queue entry shall belong to a category.

Recommended categories:

* Filename Review
* Classification Review
* Migration Review
* Database Review
* Duplicate Review
* Manual Verification
* Other

Additional categories may be added in future versions.

---

# 6. Confidence Levels

Modules that perform automatic recognition should include confidence information whenever possible.

Recommended values:

* High
* Medium
* Low

Modules that do not calculate confidence (for example File Renamer) may leave this field empty.

---

# 7. Suggested Action

Modules may provide a suggested action.

Examples:

```text
Rename to:

furina.jpg
```

or

```text
Suggested universe:

Genshin Impact
```

or

```text
Suggested destination:

Anime/Games/Genshin Impact/Furina
```

Suggestions shall never be executed automatically.

---

# 8. User Decisions

The Review Queue itself does not modify the collection.

User decisions are external to this document.

Future versions of the project may implement interfaces allowing the user to:

* approve;
* reject;
* postpone;
* ignore;

individual Review Queue entries.

---

# 9. Storage Format

The Review Queue shall be exportable.

Recommended export formats:

* CSV
* JSON

CSV is recommended for manual inspection using spreadsheet software.

JSON is recommended for future integration with project tools.

---

# 10. Lifetime

Review Queue entries remain valid until one of the following occurs:

* the user resolves the issue;
* the affected file is removed;
* the associated database record no longer exists;
* the Review Queue is manually cleared.

The system shall never remove Review Queue entries automatically.

---

# 11. Logging

Creation of Review Queue entries shall also be recorded in the project log according to DOC-011.

The log should contain:

* module;
* file identifier;
* review identifier;
* reason.

The log shall not duplicate the full Review Queue contents.

---

# 12. Safety Principles

The Review Queue exists to protect the collection from incorrect automatic decisions.

Modules shall prefer creating a Review Queue entry over performing uncertain operations.

No module shall modify files, classifications or database records solely because a possible solution exists.

Only deterministic operations or explicit user approval may change collection data.

---

# 13. Future Extensions

Future project versions may extend the Review Queue with features such as:

* graphical review interface;
* batch approval;
* filtering and searching;
* module-specific review panels;
* automatic reopening of unresolved entries;
* integration with future workflow management tools.

These extensions shall remain compatible with the principles defined in this document.
