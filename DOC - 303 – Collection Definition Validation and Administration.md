# DOC-303 – Collection Definition Validation and Administration

**Project:** AI Image Collection Management System

**Document:** DOC-303

**Version:** 1.0

**Status:** Design Specification

**Depends on:** DOC-301, DOC-302, DOC-005, DOC-008, DOC-011, DOC-013

---

# 1. Purpose

Collection Definition Validation and Administration provides maintenance operations for an already existing Collection Definition.

It does not create the initial definition and does not define the serialized format itself.

Its responsibilities are:

* validate an existing Collection Definition;
* detect structural and configuration inconsistencies;
* report problems in a form understandable to the user;
* provide controlled administrative corrections where permitted;
* preserve a known-valid definition when validation or correction fails;
* verify that the active definition remains usable by modules that depend on it.

The Collection Definition Wizard is specified by DOC-301.
The Collection Definition data model and serialized format are specified by DOC-302.

DOC-303 operates on an existing definition produced or maintained through those mechanisms.

---

# 2. Scope

Validation covers the active Collection Definition and its relationship with the configured filesystem locations.

It may inspect:

```text
Collection Definition
configured roots
configured paths
traversal rules
Classification Boundaries
roles
access policies
enabled/disabled state
parent/child relationships
filesystem existence/accessibility
```

It does not analyse image contents and does not replace Scanner, AutoSort, Analysis Modules, Review Queue, or Collection Consistency Checker.

---

# 3. Core Principle

The active Collection Definition must be internally consistent before destination-aware modules are allowed to rely on it.

A validation failure must not silently produce a partially modified active definition.

The preferred rule is:

```text
current valid definition
        ↓
validate proposed change
        ↓
VALID
        ↓
activate
```

and, on failure:

```text
current valid definition
        ↓
proposed change
        ↓
INVALID
        ↓
reject change
        ↓
retain previous valid definition
```

---

# 4. What the Validator Checks

At minimum, the validator shall check:

* required top-level fields are present;
* identifiers are unique where required;
* root roles are valid;
* root paths are syntactically valid;
* traversal rules are valid;
* parent/child references resolve correctly;
* Classification Boundaries reference valid nodes;
* boundaries do not create contradictory traversal behaviour;
* configured access policies are valid;
* enabled/disabled states are valid;
* configured PRIMARY trees do not conflict in ways prohibited by DOC-302;
* AI and TODO roots are not silently interpreted as PRIMARY structure;
* the definition can be serialized and loaded without loss of information.

The validator should also detect filesystem conditions that materially affect the usability of the active definition.

---

# 5. Filesystem Validation

Filesystem validation may report conditions such as:

```text
root does not exist
root is inaccessible
root is unexpectedly a file instead of a directory
configured path cannot be read
configured path is on an unavailable volume
```

A missing path is not automatically a definition-format error.

The distinction is:

```text
Definition error
= configuration itself is invalid

Filesystem condition
= configuration is valid but the referenced location
  is currently unavailable or changed
```

This distinction is important for removable disks, offline volumes and directories intentionally created later.

---

# 6. Root Role Validation

Configured roots shall have valid roles according to DOC-302.

Examples may include:

```text
PRIMARY
THEME_FALLBACK
TODO
AI
```

The concrete role enumeration is defined by DOC-302.

The validator must not hard-code physical names such as:

```text
Anime
Monster Girls
Western Animation
Themes
AI
TODO
```

Physical paths and logical roles are separate concepts.

---

# 7. Primary Tree Validation

Each configured PRIMARY tree must remain individually valid.

The validator shall detect, where applicable:

* duplicate root identities;
* conflicting root definitions;
* overlapping scopes prohibited by the active definition;
* impossible parent/child relationships;
* disabled nodes referenced by active destinations;
* destination nodes outside an enabled PRIMARY tree.

A PRIMARY tree is a user-defined structure. The validator does not assign semantic meaning to it based on its name.

---

# 8. Theme Fallback Validation

A configured Theme fallback has lower organisational priority than every configured PRIMARY tree.

The validator shall verify that the fallback is represented consistently with DOC-302.

It shall not promote Theme to PRIMARY merely because a directory contains many files.

Theme placement and Theme metadata are separate concerns.

---

# 9. AI and TODO Validation

AI and TODO are workspace roles, not proof of FINAL collection structure.

The validator shall ensure that:

```text
AI-created directories
```

do not become PRIMARY Collection Definition merely because they exist on disk.

Similarly, TODO subdirectories do not become approved FINAL destinations unless explicitly configured by the user through the appropriate administration workflow.

AI may contain dynamic directories such as:

```text
AI/Ben 10/
AI/Sets/0001/
```

without making those paths part of the approved PRIMARY definition.

---

# 10. Classification Boundary Validation

Each Classification Boundary must reference a valid logical node.

The validator shall check that the boundary is compatible with the node's traversal configuration.

Example:

```text
Anime
└── Genshin Impact
    └── Furina       ← boundary
        ├── 0001
        ├── 0002
        └── 0003
```

The existence of Set directories below `Furina` must not be reported as an error merely because they are not represented as classification nodes.

The validator should detect contradictions such as a definition simultaneously marking a node as terminal and requiring traversal through that same node for classification purposes.

---

# 11. Traversal Rule Validation

Traversal rules are validated according to DOC-302.

The validator shall reject unknown or malformed rules.

It shall also detect contradictory combinations, for example where a node is explicitly terminal but a child traversal rule requires the system to continue through that node in the same logical scope.

The validator does not decide which rule is semantically preferable. User intent is established by DOC-301 and administration operations.

---

# 12. Access Policy Validation

Every configured scope using Directory Access Policy shall contain a valid policy value.

Examples include:

```text
PROTECTED
READ_ONLY
MODIFY
PLAYGROUND
```

The validator does not infer access rights from filesystem permissions alone.

Filesystem permissions and project-level Directory Access Policy are related but distinct.

A root may therefore be syntactically valid while currently being inaccessible at the operating-system level.

---

# 13. Administrative Corrections

DOC-303 may provide controlled administrative operations for correcting an existing definition.

Examples include:

```text
change root path
change enabled state
change access policy
change traversal rule
change Classification Boundary
change parent relationship
remove obsolete configuration node
add an explicitly approved node
```

Administrative operations shall modify the Collection Definition, not image files.

Changing a Collection Definition does not automatically move, rename or delete files.

---

# 14. Validation Before Activation

Every administrative change shall be treated as a proposed definition until validation succeeds.

The tool shall not partially activate a set of interdependent changes.

Preferred workflow:

```text
load active definition
        ↓
create working copy
        ↓
apply administrative changes
        ↓
validate complete working copy
        ↓
if valid → activate
if invalid → reject and preserve active definition
```

The previously valid definition remains available if activation fails.

---

# 15. Versioning and Definition History

Collection Definition has its own format/versioning rules defined by DOC-302.

DOC-303 should preserve the ability to identify which definition version was active during an administrative operation.

A failed validation must not silently replace a previous valid definition.

Where history is retained, the system should preserve at least:

```text
definition version or revision
changed_at
reason for change
user-originated change information
validation result
```

The detailed persistence model belongs to DOC-302 and DOC-005.

---

# 16. No Image Changes

Collection Definition administration never directly performs:

```text
file move
file copy
file delete
file rename
image analysis
SHA512 recalculation for unrelated reasons
```

The only exception is any filesystem operation explicitly required to maintain the Collection Definition itself, such as an optional user-controlled path verification operation; such an operation must not silently reorganize image content.

---

# 17. Relationship with AutoSort

AutoSort uses the active validated Collection Definition as its source of valid FINAL destinations.

If the active definition is invalid, AutoSort must not assume that its previous configuration remains safely usable without checking the state defined by the execution architecture.

DOC-303 does not perform AutoSort operations.

An administrative correction becoming active does not itself request file movement.

---

# 18. Relationship with Collection Consistency Checker

Collection Consistency Checker uses Collection Definition to decide whether a candidate FINAL destination is valid.

DOC-303 ensures that the definition itself is structurally usable.

The division is:

```text
DOC-303
= Is the Collection Definition itself valid?

DOC-401
= Is the current collection state consistent with that definition?
```

The two modules must not silently replace one another.

---

# 19. Relationship with Scanner

Scanner uses configured roots and access policies when determining what is eligible for scanning.

If a configured root is structurally invalid, Scanner should receive a clear configuration error rather than silently inventing a replacement path.

DOC-303 does not scan image content and does not create file records.

---

# 20. Relationship with Configuration Manager

DOC-008 manages application and module configuration.

DOC-303 manages the validity and administration of the Collection Definition specified by DOC-301 and DOC-302.

The system must not maintain a second competing Collection Definition in ordinary module configuration.

Where Configuration Manager exposes Collection Definition to the application, it shall expose the active validated definition rather than independently redefining it.

---

# 21. Validation Report

A validation run should produce a human-readable report.

Suggested categories:

```text
VALID
WARNING
ERROR
```

Examples:

```text
ERROR:
PRIMARY root has no valid path.

WARNING:
AI root is currently unavailable.

WARNING:
Configured FINAL branch exists but is empty.

ERROR:
Classification Boundary references an unknown node.
```

Warnings do not necessarily prevent activation. Errors do.

The precise severity of a condition should be defined by the validation rule producing it.

---

# 22. Dry Run

Administrative changes should support a dry-run or preview mode where practical.

Example:

```text
Proposed change:
Root path
D:\OldCollection
        ↓
E:\Collection

Validation:
PASS

No configuration has been activated yet.
```

This allows the user to review potentially broad configuration changes before applying them.

---

# 23. Recovery from Invalid Definition

If the active Collection Definition is found to be invalid after loading, the system should:

1. preserve the invalid definition as a diagnostic artifact where practical;
2. retain the last known valid definition when available;
3. prevent destination-sensitive operations from silently using the invalid definition;
4. provide the user with a validation report;
5. allow the user to repair or restore the definition.

The system must not silently fabricate missing structure to make validation pass.

---

# 24. Logging

Administrative and validation executions shall follow DOC-011.

Logs should identify:

```text
execution_id
definition version/revision
operation type
user change summary
validation outcome
errors
warnings
completion status
```

The log must not expose sensitive configuration values unnecessarily.

---

# 25. Safety Principles

DOC-303 follows these principles:

1. Existing valid configuration is preserved until a replacement is validated.
2. Validation does not invent missing structure.
3. AI directories do not become FINAL structure automatically.
4. Theme fallback remains below PRIMARY trees.
5. Set directories below a Classification Boundary are not treated as errors merely because they are absent from semantic classification nodes.
6. Administrative changes affect configuration, not image files.
7. A filesystem problem is distinguished from a malformed definition.
8. Invalid proposed changes are rejected as a whole rather than partially activated.
9. Destination-aware modules consume the active validated definition.
10. User-approved configuration remains authoritative until explicitly changed by the user.

---

# 26. Acceptance Criteria

DOC-303 is compliant when it can:

* load and validate an existing Collection Definition;
* detect invalid roots, roles, rules and relationships;
* distinguish definition errors from temporary filesystem availability problems;
* validate Classification Boundaries and traversal rules;
* validate access policies;
* verify the distinction between PRIMARY, Theme fallback, AI and TODO roles;
* preview administrative changes;
* reject invalid changes without destroying the previous valid definition;
* activate a validated replacement definition;
* provide readable diagnostics;
* record validation and administrative operations;
* operate without analysing image contents or moving image files.

---

# End of DOC-303
