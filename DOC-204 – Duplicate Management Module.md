# DOC-204

# Duplicate Management Module

**Project:** AI Image Collection Management System

**Document:** DOC-204

**Module:** Duplicate Management

**Version:** 1.0

**Status:** Draft

**Depends on:**

DOC-005
DOC-007
DOC-009
DOC-010
DOC-011
DOC-012
DOC-013
DOC-101

---

# 1. Purpose

Duplicate Management is responsible for identifying files that contain identical binary content and for presenting those relationships to the user in a safe and understandable form.

The module is primarily based on **SHA512**, which is the project's logical identity for the binary content of a file.

The module may also import external duplicate information, particularly hash data produced by tools such as AllDup, and compare that information with the project database.

Duplicate Management does not perform image-similarity grouping. Visually similar but binary-different images belong to Set Detection and other analysis modules.

The module does not delete duplicate files automatically.

Its purpose is to detect, compare, report and prepare safe user decisions.

---

# 2. Core Principles

Duplicate Management follows these principles:

1. Identical SHA512 means identical binary content for the purposes of normal project operation.
2. Filename and path do not define whether two files are duplicates.
3. Duplicate detection and duplicate deletion are separate operations.
4. The database remains the source of project knowledge.
5. External tools such as AllDup are sources of imported evidence, not authoritative replacements for the project database.
6. Ambiguous cases go to Review Queue rather than being guessed.
7. No duplicate may be deleted merely because another file has been selected as a proposed master.
8. Manual user decisions take precedence over subsequent automatic duplicate suggestions for the protected context.

---

# 3. Definition of Duplicate

For this module, a **duplicate** is a distinct filesystem file whose calculated SHA512 is identical to the SHA512 of another known file.

Example:

```text
File A
SHA512 = AAAA
Path   = TODO/source/image.jpg

File B
SHA512 = AAAA
Path   = AI/imported/image.jpg
```

The two files are duplicate physical instances of the same binary object.

They do not represent two different image identities.

A filename match without matching SHA512 does not constitute a duplicate.

A perceptual or visual similarity match without matching SHA512 does not constitute a duplicate for this module.

---

# 4. Relationship with File Identity

Duplicate Management shall follow DOC-012.

The logical binary-content identity is SHA512.

An internal `file_id` identifies a database record but does not redefine file identity.

Example:

```text
file_id = 101
SHA512  = AAAA
path    = TODO/a.jpg

file_id = 248
SHA512  = AAAA
path    = AI/b.jpg
```

The database may contain two physical-file records with the same SHA512 when two physical instances are known to exist.

Those records represent two locations of the same binary object rather than two independent binary identities.

Duplicate Management is therefore concerned with the relationship between **physical file records sharing one SHA512**.

---

# 5. Duplicate Detection

The primary detection mechanism is database grouping by SHA512.

Conceptually:

```text
SHA512
  ↓
GROUP BY SHA512
  ↓
more than one active physical record
  ↓
duplicate group
```

The module should normally consider only records that represent currently existing physical files.

Archived, missing or deleted records may still be relevant for historical reporting, but they must be distinguished from active physical duplicates.

A duplicate group should contain enough information to allow the user to understand:

```text
SHA512
number of physical instances
locations
collection/root
status
file size
last verification
```

---

# 6. Duplicate Scope

Duplicate Management shall support several scopes.

## 6.1 Within One Root

Detect duplicates inside a selected configured root.

Example:

```text
TODO
└── source A
└── source B
```

## 6.2 Between Roots

Detect duplicate files stored in different configured roots.

Example:

```text
TODO/image.jpg
AI/image.jpg
```

## 6.3 Between Collections

Detect duplicates between different collection trees, including cases where one physical instance is already inside a primary or Theme tree.

## 6.4 Whole Database

Compare all eligible active physical records known to the database.

The selected scope is part of the execution configuration.

---

# 7. Primary Detection Using the Database

When the database already contains current SHA512 values, Duplicate Management should use those values rather than recalculating all hashes unnecessarily.

A new hash calculation may be required when:

* the file is not yet known to the database;
* the existing SHA512 is stale or invalid;
* the user explicitly requests verification;
* an external duplicate report identifies a file requiring verification.

The module must never replace a valid SHA512 with an unverified placeholder.

Hash calculation failures are logged and may enter Review Queue where appropriate.

---

# 8. AllDup Import

Duplicate Management may import duplicate information produced by AllDup or another compatible external tool.

The external import may contain information such as:

```text
path
SHA512
file size
filename
```

The importer shall treat imported information as **external evidence**.

The project database remains authoritative after verification.

The importer must not blindly change file identity, classification, master status or delete files merely because an external report says that files are duplicates.

---

# 9. AllDup Import Workflow

A typical import workflow is:

```text
AllDup
   ↓
external result
   ↓
Duplicate Management Import
   ↓
path / SHA512 matching
   ↓
compare with database
   ↓
consistent records
   OR
inconsistency report / Review Queue
```

The importer shall identify at least the following situations:

### 9.1 Exact Match

The imported SHA512 and path correspond to the current database record.

No corrective action is required.

### 9.2 External File Missing in Database

AllDup reports a file that has no corresponding database record.

Possible reasons include:

* Scanner has not yet discovered the file;
* file is outside the currently indexed collection;
* database record was removed;
* path or collection configuration changed.

The module shall report the discrepancy and shall not invent a file record merely from the import.

### 9.3 Database File Missing from External Report

The database contains a file not present in the imported AllDup result.

This does not automatically indicate an error. The AllDup scan may have used a different scope.

The difference shall be reported in the import summary.

### 9.4 SHA512 Conflict

A path is associated with one SHA512 externally and another SHA512 in the database.

This is an integrity issue requiring verification and must not be silently resolved.

---

# 10. Duplicate Group

A **Duplicate Group** represents all currently relevant physical file records sharing the same SHA512.

Example:

```text
Duplicate Group

SHA512: AAAA

1. TODO/source/image.jpg
2. AI/import/image.jpg
3. Anime/Genshin/Furina/0007/image.jpg
```

The group is a management object, not a new file identity.

The database may assign a technical duplicate-group identifier for convenience.

The SHA512 remains the authoritative binary-content key.

---

# 11. Master File

A Duplicate Group may have a proposed **master file**.

The master file is the physical instance that the user would normally prefer to retain as the canonical representative of the duplicate group.

The master decision may consider:

* current collection status;
* location in a primary collection tree;
* location in AI or TODO;
* manual user protection;
* file accessibility;
* verification state;
* directory access policy;
* completeness of database metadata;
* historical/user preference;
* age or other configured preference.

There is no universal rule that the oldest, newest, shortest path or first discovered file must be the master.

The selection criteria must be configurable or documented and must remain reviewable by the user.

---

# 12. Master Selection Safety

Selecting a proposed master does not authorize deletion of the other physical instances.

Example:

```text
SHA512 = AAAA

Proposed master:
FINAL/Anime/Genshin/Furina/0007/image.jpg

Duplicates:
TODO/import/image.jpg
AI/review/image.jpg
```

The proposal means only that the first file is currently preferred as the retained physical instance.

Any deletion or other destructive operation requires a separate explicit user decision.

---

# 13. Preferred Master Rules

The initial implementation should prefer safe, predictable criteria.

A configurable preference order may be used, for example:

```text
manual protection / explicit user choice
        ↓
valid primary FINAL placement
        ↓
valid Theme placement
        ↓
AI workspace
        ↓
TODO/source
        ↓
other / unknown location
```

This is an example preference order, not a hard-coded universal taxonomy.

The exact rules belong to module configuration.

If two or more instances are equally suitable, Duplicate Management should not guess.

The group may be placed in Review Queue for user selection.

---

# 14. Duplicates Across Collection Trees

Duplicates may occur across different primary trees or fallback areas.

Example:

```text
Anime/Genshin/Furina/0001/image.jpg

Themes/Bikini/image.jpg
```

If both files have identical SHA512, they belong to the same duplicate group.

Duplicate Management does not decide whether the Theme copy or primary-tree copy is semantically correct solely from the duplicate relationship.

Classification and placement rules remain the responsibility of the relevant modules.

The master-selection process may nevertheless use current valid placement as one factor.

---

# 15. Duplicate States

Duplicate groups may be represented with states such as:

```text
DETECTED
VERIFIED
MASTER_PROPOSED
REVIEW_REQUIRED
USER_RESOLVED
PARTIALLY_RESOLVED
```

Exact state transitions are implementation details but must preserve the distinction between:

```text
detected duplicate
```

and:

```text
user-authorized cleanup decision
```

A duplicate group must never be treated as resolved merely because the module proposed a master.

---

# 16. Review Queue Integration

Duplicate Management shall use Review Queue when automatic handling would require a judgement that is not sufficiently deterministic.

Typical cases include:

* two equally suitable master candidates;
* conflict between user-protected files;
* inconsistent imported SHA512 information;
* uncertain relationship between active and archived records;
* requested cleanup would remove a file from a protected or final location;
* a duplicate exists in multiple important collection trees;
* external evidence and database state disagree.

Review Queue entries should contain sufficient information for the user to make a decision without manually reconstructing the duplicate group.

At minimum:

```text
SHA512
candidate files and paths
collection/root
status
proposed master where applicable
reason
source of evidence
```

---

# 17. User Decisions

Duplicate Management does not decide what the user ultimately keeps unless the user has explicitly configured a deterministic rule that is safe for the situation.

Possible user outcomes may include:

```text
ACCEPT
REJECT
MODIFY
DEFER
```

The exact physical operation resulting from the decision is handled according to the applicable workflow and access policy.

A user-selected master or protected file must not be silently replaced by a later automatic recommendation.

---

# 18. Deletion and Cleanup

Duplicate Management is primarily a detection and decision module.

Automatic permanent deletion is outside its default authority.

A future cleanup workflow may use Duplicate Management results to perform a user-approved deletion or archival operation, subject to Directory Access Policy and database-maintenance rules.

Before a destructive cleanup operation, the system should be able to show:

```text
master file
files to remove/archive
SHA512
locations
reason
user decision
```

No duplicate file should be deleted merely because it is not the proposed master.

---

# 19. Duplicate Management and File Identity Changes

If a file changes binary content:

```text
SHA512 A
   ↓
SHA512 B
```

it is no longer a duplicate of files with SHA512 A unless another physical copy also has SHA512 B.

The new binary identity participates in a new duplicate group.

Old duplicate relationships remain historical information associated with the previous SHA512 identity where required.

A rename or move without content change does not alter duplicate membership.

---

# 20. Archived Records and Duplicates

Archived records shall be treated according to DOC-012.

A currently active file may have the same SHA512 as an archived historical record.

This is not necessarily an active duplicate group of two physical files.

The module must distinguish:

```text
multiple active physical instances
```

from:

```text
one active instance + historical archived record
```

If an archived record is reactivated because the same SHA512 is discovered again, the relationship shall follow DOC-012.

---

# 21. Missing and Unverified Files

Files marked `MISSING`, unavailable or otherwise unverified must not be treated as confirmed physical duplicates merely because their database SHA512 matches an active file.

The database may still retain the historical relationship, but the execution summary shall distinguish confirmed active duplicates from historical or unverified instances.

---

# 22. Processing Scope

Duplicate Management supports configurable scopes such as:

```text
selected directory
selected collection root
selected primary tree
AI
TODO
all configured roots
whole database
AllDup import scope
```

The module must not assume that every run covers the entire collection.

A result from a limited scope must clearly identify that scope.

---

# 23. Repeated Execution

Duplicate Management is independently executable and may be run repeatedly.

It does not require another analysis module to be running.

Example:

```text
Day 1  Scanner
Day 2  Duplicate Management
Day 5  Scanner discovers new files
Day 6  Duplicate Management
Day 8  AllDup import
Day 9  Duplicate Management
```

The module reads the current database state at execution time.

Previous results may be reused where still valid.

---

# 24. Reprocessing and Verification

Duplicate detection may be reprocessed when:

* a new file enters the database;
* a file's SHA512 changes;
* a previously failed hash calculation succeeds;
* an external AllDup report is imported;
* database integrity is repaired;
* the user explicitly requests verification.

A path or filename change without a SHA512 change does not require duplicate recalculation solely for identity purposes.

---

# 25. Database Access

The module reads:

```text
File
Module
Collection Root / Collection Definition where required
File Events where relevant
Review / user decisions where applicable
```

The module writes:

```text
Duplicate Group information
Duplicate membership / relationship data
import records where applicable
Module Execution state
Review Queue items where required
File Events where explicitly required
```

It must not overwrite analysis results owned by other modules.

Persistent communication with other modules occurs through the shared database.

---

# 26. Performance Requirements

The initial target is approximately five million image files.

The implementation must avoid all-to-all comparison of every file whenever database SHA512 grouping is sufficient.

The preferred approach is hash-indexed grouping:

```text
SHA512 → list of file records
```

The entire collection must not be loaded into RAM merely to detect exact duplicates.

AllDup imports should be streamed or processed incrementally where practical.

---

# 27. Threading and Resource Usage

Parallel processing may be used for:

* hash verification;
* external-report parsing;
* filesystem validation;
* duplicate-group preparation.

Worker count shall be configurable.

Concurrent workers must not create inconsistent duplicate-group state or duplicate Review Queue entries for the same execution context.

The module should use available system resources efficiently while respecting configured safety limits.

---

# 28. Error Handling

An individual file or imported record failing validation must not unnecessarily terminate processing of unrelated records.

Typical errors include:

```text
unreadable file
hash calculation failure
invalid external report
path no longer exists
SHA512 conflict
permission failure
database write failure
```

Errors shall be logged according to DOC-011.

Integrity-affecting failures may terminate the affected operation if continuing would create unsafe duplicate information.

---

# 29. Logging

Each execution shall create a Module Execution record and summary log according to DOC-007 and DOC-011.

The summary should include where applicable:

```text
scope
started
finished
files examined
hashes verified
duplicate groups found
physical duplicate instances
AllDup records imported
inconsistencies
Review Queue entries
master proposals
errors
duration
```

Detailed entries should include SHA512 and affected paths where safe.

---

# 30. External Tool Provenance

Imported duplicate information shall retain provenance.

For example:

```text
source = ALLDUP
imported_at = ...
report_id = ...
```

The database must distinguish:

```text
project-verified SHA512
```

from:

```text
external imported evidence
```

An external report must not silently become permanent truth without project verification where verification is required.

---

# 31. Relationship with Set Detection

Duplicate Management and Set Detection have different purposes.

```text
Duplicate Management
    ↓
identical binary content
    ↓
SHA512
```

```text
Set Detection
    ↓
visually related but potentially different content
    ↓
visual similarity / grouping evidence
```

Two files with different SHA512 may still belong to the same Set.

Two files with identical SHA512 are duplicates even if they have different filenames or locations.

Duplicate Management must not convert a visual similarity relationship into a duplicate relationship.

---

# 32. Relationship with AutoSort

Duplicate Management does not decide normal collection classification or placement.

AutoSort remains responsible for applying classification and collection rules to physical locations.

Duplicate information may be consumed by AutoSort or a later cleanup workflow as supporting information, but duplicate detection itself does not authorize relocation or deletion.

---

# 33. Relationship with Scanner

Scanner is responsible for discovering files and calculating/storing their SHA512 according to DOC-101.

Duplicate Management may rely on those stored results.

Duplicate Management may request verification or hash calculation through the documented infrastructure, but it must not bypass Scanner's file-identity rules by inventing a parallel identity system.

---

# 34. Relationship with Database Maintenance

Database Maintenance may remove archived records or rebuild the database according to DOC-202.

Duplicate Management results must therefore remain compatible with database rebuild and maintenance operations.

After a rebuild:

* internal `file_id` values may change;
* SHA512 remains the logical file identity;
* duplicate detection can be reconstructed from current SHA512 records.

Persistent external references should use SHA512 rather than relying solely on `file_id`.

---

# 35. Safety Rules

Duplicate Management shall never:

* assume that the first discovered file is the master;
* delete a file merely because another file has the same SHA512;
* overwrite files while resolving duplicates;
* modify image content;
* alter SHA512 values;
* treat filenames as proof of identity;
* silently resolve an integrity conflict;
* convert visual similarity into duplicate status;
* bypass Review Queue where user judgement is required.

The safe default for ambiguity is:

```text
preserve files
record the problem
ask the user
```

---

# 36. Acceptance Criteria

Duplicate Management is considered compliant when it can:

* detect active physical duplicates using SHA512;
* distinguish duplicate physical instances from one binary identity;
* import and compare AllDup hash information;
* detect discrepancies between external reports and database state;
* detect duplicates within and between configured collection roots;
* produce duplicate groups;
* propose a master file using configurable safe criteria;
* avoid deleting files merely because they are duplicate instances;
* integrate ambiguous cases with Review Queue;
* preserve manual user decisions;
* distinguish active, missing and archived records;
* remain compatible with SHA512-based file identity and database rebuild;
* operate repeatedly and independently;
* scale to multi-million-file collections without all-to-all binary comparison;
* communicate persistent results through the shared database.

---

# End of DOC-204
