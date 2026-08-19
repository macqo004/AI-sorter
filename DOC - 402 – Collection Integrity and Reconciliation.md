# DOC - 402 – Collection Integrity and Reconciliation

**Project:** AI Image Collection Management System  
**Document:** DOC - 402  
**Version:** 1.0  
**Status:** Design Specification

---

## 1. Purpose

Collection Integrity and Reconciliation is a maintenance module responsible for reconciling the project's three principal sources of collection state:

```text
Filesystem
    ↕
Project Database
    ↕
Collection Definition
```

Its purpose is to detect and classify structural, identity and state discrepancies between these sources and provide a safe basis for reconciliation.

The module does not perform image classification and does not replace Collection Consistency Checker.

---

## 2. Relationship with DOC - 401

The responsibilities are intentionally separated.

```text
DOC - 401
Collection Consistency Checker
    ↓
Is this file's current FINAL placement consistent with
its known classification?

DOC - 402
Collection Integrity and Reconciliation
    ↓
Does the filesystem, database and Collection Definition
agree about what actually exists and how it is represented?
```

DOC - 401 is primarily a **classification/placement consistency** module.

DOC - 402 is primarily a **state reconciliation and integrity** module.

For example, DOC - 402 handles conditions such as:

```text
file exists on disk but has no valid database record
DB record says ACTIVE but the file is missing
Collection Definition references a root that no longer exists
DB path differs from the current filesystem path
multiple physical locations exist for the same SHA512
```

DOC - 401 handles a different case:

```text
file exists
DB record is valid
Collection Definition is valid
but current placement conflicts with current classification
```

---

## 3. Scope

DOC - 402 may inspect:

* configured filesystem roots;
* file records;
* file locations;
* SHA512 identities;
* Collection Definition;
* database lifecycle states;
* module metadata;
* selected historical records required for reconciliation.

The module does not perform image-content analysis.

It does not decide whether an image belongs to Anime, Monster Girls, Western Animation, a Universe, Character or Theme.

Those decisions belong to the relevant analysis and review workflows.

---

## 4. Sources of Truth

Different information has different authoritative sources.

### File content identity

```text
SHA512
```

is the authoritative identity of the binary content, according to DOC - 012.

### Physical existence

The filesystem is authoritative for whether a physical file currently exists at a path.

### Database operational state

The database is authoritative for the project's recorded state, history and module results.

### FINAL collection structure

Collection Definition is authoritative for which configured FINAL destinations are valid.

The physical existence of an arbitrary directory does not automatically make it an approved FINAL destination.

### User decisions

Explicit manual decisions recorded through Review Queue have priority over older automatic suggestions for the affected decision context.

---

## 5. Reconciliation Principle

The module must never silently choose one source as universally correct.

Instead it identifies the discrepancy and determines which type of reconciliation is possible.

The general workflow is:

```text
Inspect
   ↓
Compare
   ↓
Classify discrepancy
   ↓
Determine safe reconciliation path
   ↓
Apply only authorised state changes
   OR
Create Review Queue case
   OR
Report unresolved integrity problem
```

Where the correct interpretation cannot be established safely, the module must not guess.

---

## 6. File Identity Reconciliation

File identity follows DOC - 012 and DOC - 005.

SHA512 is the identity of binary content.

Two physical file locations containing the same SHA512 are treated as physical occurrences of the same binary content unless an integrity exception is explicitly detected.

Example:

```text
D:\Collection\image.jpg   SHA512 = ABC...
E:\Backup\image.jpg       SHA512 = ABC...
```

The database may therefore have one logical file identity with multiple physical locations/occurrences.

The presence of multiple locations is not by itself a database corruption condition. It is a duplicate/instance condition that may be handled by DOC - 204.

A mismatch between the expected SHA512 and the current filesystem content is an identity inconsistency.

---

## 7. Database ↔ Filesystem Reconciliation

The module shall detect at least the following conditions.

### 7.1 Database record without physical file

```text
DB:
SHA512 = ABC
location = D:\Collection\image.jpg
status = ACTIVE

Filesystem:
file not found
```

Possible result:

```text
mark for reconciliation
```

The module must not immediately delete the database record merely because the file is temporarily unavailable.

The appropriate lifecycle state may become `MISSING` according to DOC - 012 and DOC - 202.

### 7.2 Physical file without database identity

```text
Filesystem:
D:\Collection\new.jpg

DB:
no corresponding active record
```

The normal registration path is Scanner.

DOC - 402 may report the orphan condition and, where explicitly configured, request or recommend Scanner reconciliation. It must not fabricate a SHA512 record by itself without following the Scanner/File Identity rules.

### 7.3 Path mismatch

```text
DB:
current_path = D:\A\image.jpg

Filesystem:
image exists at D:\B\image.jpg
same SHA512
```

Because SHA512 is unchanged, the module may reconcile the physical location with the database record according to the permitted database update workflow.

A move or rename does not create a new file identity.

---

## 8. Collection Definition ↔ Filesystem Reconciliation

The module shall compare configured roots and structural rules with the actual filesystem.

Examples include:

```text
Collection Definition references root X
root X does not exist
```

or:

```text
Collection Definition expects a configured branch
branch is missing from filesystem
```

or:

```text
filesystem contains a directory
but that directory is not part of the approved Collection Definition
```

The last condition is not automatically an error.

It may be:

* user organisation below a Classification Boundary;
* a Set directory;
* an AI workspace directory;
* TODO content;
* an excluded branch;
* an unconfigured filesystem addition.

The module must interpret the path according to Collection Definition and Directory Access Policy before reporting a structural violation.

---

## 9. Classification Boundary Protection

DOC - 402 must respect Classification Boundaries defined by DOC - 301 and DOC - 302.

For example:

```text
Anime
└── Genshin Impact
    └── Furina        ← boundary
        ├── 0001
        ├── 0002
        └── Favorites
```

The module must not report `0001`, `0002` or `Favorites` as missing logical collections merely because they are not represented as classification nodes.

Set directories below the boundary are user/workflow organisation, not additional semantic hierarchy.

---

## 10. Primary Trees and Theme Fallback

Collection Integrity does not hard-code any primary tree names.

Configured PRIMARY trees are defined by Collection Definition.

Theme fallback is a configured role and remains below all configured PRIMARY trees in organisational priority.

The integrity module checks whether the paths and configured roles remain structurally valid. It does not decide whether a Theme classification should be replaced by a PRIMARY classification; that remains a classification/placement concern handled by DOC - 401, Review Queue and the relevant analysis modules.

---

## 11. AI and TODO

AI and TODO may contain directories that do not exist in FINAL Collection Definition.

Their existence is therefore not an integrity error merely because they are absent from the FINAL definition.

Example:

```text
AI/Ben 10/
AI/Sets/0001/
TODO/...
```

may be perfectly valid workspace state.

The module must use the configured root role before applying FINAL structural expectations.

---

## 12. Database State Reconciliation

The module may detect state contradictions such as:

```text
ACTIVE record with no valid location
MISSING record with verified physical file
ARCHIVED record whose content has reappeared
inconsistent lifecycle timestamps
invalid module references
invalid collection/root references
```

A state correction must follow the lifecycle rules of DOC - 012 and DOC - 202.

The module must preserve historical information where the architecture requires it.

It must not erase evidence merely to make the current state appear consistent.

---

## 13. Same-SHA512 Multiple Locations

Multiple physical locations with the same SHA512 shall normally be interpreted as multiple occurrences of the same logical binary content.

Example:

```text
File identity:
SHA512 = ABC...

Locations:
1. FINAL/Anime/A/image.jpg
2. FINAL/Backup/image.jpg
3. AI/Archive/image.jpg
```

DOC - 402 should report the locations and their configured roles when relevant.

Duplicate Management remains responsible for duplicate grouping and decisions about master/duplicate relationships.

DOC - 402 must not automatically delete any occurrence solely because the SHA512 is duplicated.

---

## 14. Safe Reconciliation Actions

DOC - 402 may perform low-risk database reconciliation actions when the evidence is deterministic and the operation is authorised.

Examples:

* update a verified current path for an unchanged SHA512;
* update `last_seen` after successful verification;
* transition a clearly missing record to the appropriate missing state according to lifecycle rules;
* record an integrity event.

It must not directly perform high-risk content or classification operations merely to remove an inconsistency.

Examples of actions outside its authority:

```text
create new FINAL classification tree
move a file because the model prefers another Universe
delete a suspected duplicate
rename files as part of classification correction
overwrite a protected manual decision
```

Such actions belong to their responsible modules and workflows.

---

## 15. Review Queue Integration

When reconciliation cannot be completed deterministically, DOC - 402 shall create a Review Queue case according to DOC - 013.

Examples:

```text
multiple plausible physical locations
conflicting manual/history state
ambiguous missing-file situation
conflicting Collection Definition references
```

The Review Queue case shall identify the discrepancy and the information required for the user to decide.

The module must not create a separate reconciliation queue that competes with Review Queue.

---

## 16. Dry Run

The default administrative mode should support a dry run.

Dry run:

```text
inspect
compare
report proposed reconciliation
make no state changes
```

This is especially important before running reconciliation on very large collections.

A commit/apply mode may then perform only the changes explicitly authorised by the module's rules.

---

## 17. Repeated Execution

DOC - 402 may be executed repeatedly.

A successful reconciliation should not be reported as a new discrepancy during the next run.

Example:

```text
Run 1:
DB path = A
filesystem path = B

→ discrepancy detected

Reconcile:
DB path updated to B

Run 2:
DB path = B
filesystem path = B

→ no discrepancy
```

Repeated execution must remain independent from other module execution.

---

## 18. Failure Handling

A failure affecting one file or path should not unnecessarily invalidate successfully reconciled unrelated records.

Examples:

* inaccessible directory;
* permission failure;
* temporary network or filesystem failure where applicable;
* corrupted database record;
* invalid Collection Definition reference;
* unexpected filesystem state.

The module shall log the error and continue where safe.

A failed or incomplete reconciliation must not be presented as a successful complete repair.

---

## 19. Logging

Each execution shall follow DOC - 011 and record:

```text
execution_id
start/end time
roots inspected
files/locations inspected
identity mismatches
missing records
orphan records
structural discrepancies
actions proposed
actions applied
Review Queue cases
errors
```

Where large result sets are involved, summary statistics should be available without requiring the user to inspect every record manually.

---

## 20. Performance

The initial target is approximately:

```text
5,000,000 files
```

The module should support incremental and scoped reconciliation where possible.

It must avoid loading the entire collection into memory merely to compare state.

Operations should be performed in batches where practical.

The module must not assume that a full filesystem/database comparison can always complete as one giant transaction.

---

## 21. Safety Principles

DOC - 402 follows these rules:

1. SHA512 remains the identity of binary content.
2. Multiple locations with the same SHA512 normally represent the same logical content.
3. Filesystem existence and database state are compared, not blindly equated.
4. Collection Definition determines approved FINAL structure.
5. AI and TODO are not judged by FINAL structural rules.
6. Classification boundaries are respected.
7. Deterministic low-risk database reconciliation may be automated.
8. Ambiguous cases go to Review Queue.
9. No automatic duplicate deletion is performed.
10. No automatic classification correction is performed.
11. Protected user decisions are never overwritten.
12. Dry Run is available before applying reconciliation.
13. The module may be run repeatedly and independently.

---

## 22. Relationship with Other Documents

```text
DOC - 005  Database Schema
DOC - 008  Configuration Manager
DOC - 012  File Identity Model
DOC - 013  Review Queue
DOC - 014  Module Result Lifecycle
DOC - 101  Scanner
DOC - 201  AutoSort
DOC - 202  Database Maintenance
DOC - 204  Duplicate Management
DOC - 301  Collection Definition Wizard
DOC - 302  Collection Definition Format
DOC - 303  Collection Definition Validation and Administration
DOC - 401  Collection Consistency Checker
```

Responsibilities remain separated:

```text
DOC - 101 → register/discover filesystem files
DOC - 202 → database maintenance and integrity operations
DOC - 204 → duplicate management
DOC - 301/302/303 → define and administer collection structure
DOC - 401 → classification/placement consistency
DOC - 402 → filesystem/DB/definition reconciliation
```

---

## 23. Acceptance Criteria

DOC - 402 is compliant when it can:

* compare configured filesystem state with database state;
* verify SHA512 identity relationships;
* detect missing and orphan records;
* detect stale or incorrect paths;
* validate configured Collection Definition roots and structural references;
* respect Classification Boundaries and Set directories;
* distinguish FINAL, AI and TODO semantics;
* recognise multiple occurrences of the same SHA512 without treating them as different binary identities;
* perform safe deterministic database reconciliation where authorised;
* create Review Queue cases for ambiguous conditions;
* support Dry Run;
* operate repeatedly without recreating already resolved discrepancies;
* handle approximately 5 million files without requiring the whole collection in memory;
* avoid automatic classification, duplicate deletion and arbitrary FINAL structure creation.

---

# End of DOC - 402
