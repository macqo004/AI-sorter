# DOC - 402 – Collection Integrity and Reconciliation

**Project:** AI Image Collection Management System  
**Document:** DOC - 402  
**Version:** 2.0  
**Status:** Design Specification

---

# 1. Purpose

Collection Integrity and Reconciliation compares the project's three principal state sources:

```text
Filesystem
    ↕
Project Database
    ↕
Collection Definition
```

Its purpose is to detect and safely reconcile discrepancies between them.

It does not perform image classification and does not replace DOC - 401.

---

# 2. Relationship with DOC - 401

```text
DOC - 401
    classification / placement consistency

DOC - 402
    filesystem / database / Collection Definition consistency
```

Example for DOC - 401:

```text
file exists
DB identity exists
Collection Definition is valid
classification says Genshin
current FINAL placement says Winx Club
```

Example for DOC - 402:

```text
file exists on disk but no DB identity exists
DB location is stale
Collection Definition root no longer exists
physical content SHA512 differs from recorded identity
```

---

# 3. Sources of Truth

Different information has different authoritative sources.

### Binary identity

SHA512, according to DOC - 012, is the authoritative identity of binary content.

### Physical existence

The filesystem is authoritative for whether a physical object currently exists at a reachable location.

### Recorded application state

The database is authoritative for recorded module results, user decisions, execution history and current registered identity/location state until reconciliation establishes a different physical fact.

### Approved collection structure

Collection Definition is authoritative for configured roots, approved FINAL structure, traversal and access policy.

### User decisions

Explicit user decisions recorded through Review Queue take priority over automatic suggestions for the protected decision context.

The module must not treat any source as universally authoritative for every kind of information.

---

# 4. Reconciliation Workflow

The general process is:

```text
Inspect
   ↓
Compare
   ↓
Classify discrepancy
   ↓
Determine deterministic resolution
   ↓
Apply safe authorised state update
   OR
Use Scanner / another responsible module
   OR
Create Review Queue case
   OR
Report unresolved integrity error
```

When the correct interpretation cannot be determined safely, the module must not guess.

---

# 5. File Identity Model

The module follows DOC - 005 and DOC - 012:

```text
File
    = one logical SHA512 identity

FileLocation
    = one physical occurrence
```

Two physical locations with the same SHA512 normally represent one logical binary content identity with multiple occurrences.

This is not a schema corruption condition by itself and may be passed to DOC - 204 for duplicate handling.

---

# 6. Database ↔ Filesystem Reconciliation

The module shall detect at least:

### 6.1 Registered physical occurrence missing

A registered FileLocation points to a path that cannot currently be verified.

The module must distinguish:

```text
root temporarily inaccessible
```

from:

```text
file actually absent
```

If absence cannot yet be established, the record is left unchanged and the root/path is reported as unavailable.

If permanent absence is verified, DOC - 403 governs removal of the obsolete active database record/location.

### 6.2 Physical file without database identity

A physical file exists in configured scope without a corresponding File identity.

The normal registration path is Scanner. DOC - 402 may report the discrepancy but should not implement a second hashing/registration mechanism.

### 6.3 Path mismatch

A known SHA512 is found at a different valid location from the current recorded location.

If the SHA512 is verified and the new location is within scope, the location state may be reconciled according to the responsible database operation.

This does not create a new File identity.

### 6.4 Content mismatch

A registered physical occurrence is found, but its current SHA512 differs from the recorded File identity.

This is an identity-changing event and must be handled according to DOC - 012 and Scanner. The module must not simply overwrite the recorded SHA512.

---

# 7. Collection Definition ↔ Filesystem

The module compares configured roots and approved structure against actual filesystem state.

Examples:

```text
configured root does not exist
configured root is inaccessible
approved node is missing
filesystem contains a directory not represented in the approved structure
```

An unrepresented directory is not automatically an integrity error because it may be:

* a Set directory below a Classification Boundary;
* user organisation below a configured boundary;
* an AI workspace directory;
* TODO content;
* an excluded branch;
* an otherwise permitted workspace object.

The module must interpret the path according to Collection Definition before reporting a structural violation.

---

# 8. Classification Boundaries

Classification Boundaries defined by DOC - 301 / DOC - 302 must be respected.

Example:

```text
Anime
└── Genshin Impact
    └── Furina        ← Classification Boundary
        ├── 0001
        ├── 0002
        └── Favorites
```

The module must not expect `0001`, `0002` or `Favorites` to be represented as semantic classification nodes.

Physical Set folders below the boundary are valid organisation structures.

---

# 9. PRIMARY and Theme Fallback

DOC - 402 does not hard-code tree names.

Configured `PRIMARY` roots are approved main collection trees.

`THEME_FALLBACK` is a configured fallback organisation role below all PRIMARY trees.

The module validates structure and role consistency only. It does not decide whether a Theme placement should be promoted to PRIMARY.

That is a classification/placement responsibility.

---

# 10. AI and TODO

AI and TODO are configured workspaces and may contain dynamic subdirectories that do not exist in PRIMARY Collection Definition.

Examples:

```text
AI/Ben 10/
AI/Sets/0001/
TODO/...
```

Such directories are not integrity errors merely because they are absent from FINAL structure.

---

# 11. Multiple Locations with the Same SHA512

Multiple active FileLocation records sharing one SHA512 are valid.

Example:

```text
File
SHA512 = ABC...

Location A
FINAL/Anime/A/image.jpg

Location B
AI/Archive/image.jpg
```

The module reports these occurrences and their configured roles where useful.

DOC - 204 remains responsible for duplicate grouping, preferred-location decisions and duplicate cleanup.

DOC - 402 must not delete a location merely because the SHA512 occurs elsewhere.

---

# 12. Deterministic Reconciliation Actions

DOC - 402 may perform low-risk database updates when the evidence is deterministic and the operation is authorised.

Examples:

* update a verified FileLocation path for unchanged SHA512;
* update `last_seen` after successful verification;
* record an integrity/reconciliation event;
* refresh verified filesystem metadata.

The module shall not:

```text
change classification
create PRIMARY destinations
move files because of model disagreement
delete duplicates
rename files as classification correction
overwrite protected user decisions
```

Those actions belong to other responsible components.

---

# 13. Review Queue

Ambiguous reconciliation cases use the common Review Queue from DOC - 013.

Examples include:

* multiple plausible new physical locations;
* conflicting Collection Definition references;
* ambiguous restore state;
* unresolved protected/manual state.

No separate reconciliation queue is created.

---

# 14. Dry Run and Apply

The module should provide two administrative modes:

### Dry Run

```text
inspect
compare
report
no state changes
```

### Apply

Perform only deterministic and authorised reconciliation updates.

High-risk or ambiguous changes remain for Review Queue/user action.

---

# 15. Repeated Execution

DOC - 402 may be run repeatedly.

Once a deterministic discrepancy has been reconciled, a later run should not recreate the same discrepancy unless the physical state changes again.

Example:

```text
DB path = A
filesystem path = B
    ↓
reconcile
    ↓
DB path = B
    ↓
next run: consistent
```

The module remains independent from other module processes.

---

# 16. Failure Handling

A per-file or per-root error should not invalidate unrelated successful reconciliation.

Examples include:

```text
permission failure
unavailable drive
corrupt record
invalid definition reference
unexpected filesystem state
```

The module logs the error and continues where safe.

An incomplete run must not be reported as a complete repair.

---

# 17. Logging

Each execution follows DOC - 011.

The summary should include:

```text
execution_id
roots inspected
locations inspected
missing/inaccessible roots
identity mismatches
orphan physical files
structural discrepancies
actions proposed
actions applied
Review Queue cases
errors
completion status
```

---

# 18. Performance

The module targets approximately 5,000,000 files.

It should support scoped and incremental reconciliation and use batching where practical.

The entire collection must not be loaded into application memory merely to compare state.

---

# 19. Relationship with Other Documents

```text
DOC - 005  Database Schema
DOC - 012  File Identity Model
DOC - 013  Review Queue
DOC - 101  Scanner
DOC - 201  AutoSort
DOC - 202  Database Maintenance
DOC - 204  Duplicate Management
DOC - 301  Collection Definition Wizard
DOC - 302  Collection Definition Format
DOC - 303  Collection Definition Validation and Administration
DOC - 401  Collection Consistency Checker
DOC - 403  Orphan and Missing File Management
DOC - 404  Recovery and Rescan Procedures
```

Responsibilities remain separated:

```text
DOC - 101 → discover/register files
DOC - 202 → database maintenance
DOC - 204 → duplicate management
DOC - 301/302/303 → collection configuration/validation
DOC - 401 → classification/placement consistency
DOC - 402 → cross-source reconciliation
DOC - 403 → verified missing/orphan-file handling
DOC - 404 → recovery procedures
```

---

# 20. Acceptance Criteria

DOC - 402 is compliant when it can:

* compare filesystem state, database state and Collection Definition;
* validate SHA512 identity relationships;
* detect missing/inaccessible locations without causing mass deletion;
* detect physical files without registered identities and route them to Scanner;
* detect stale paths and content mismatches;
* respect Classification Boundaries and Set directories;
* distinguish AI/TODO workspace structure from FINAL structure;
* represent multiple occurrences of one SHA512 correctly;
* apply only deterministic low-risk database reconciliation;
* create Review Queue cases for ambiguous situations;
* provide Dry Run and Apply behaviour;
* run repeatedly without recreating resolved discrepancies;
* scale to multi-million-file collections without loading the entire collection into memory.

---

# End of DOC - 402
