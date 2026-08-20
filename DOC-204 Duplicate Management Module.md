# DOC - 204 – Duplicate Management Module

**Project:** AI Image Collection Management System  
**Document:** DOC - 204  
**Module:** Duplicate Management  
**Version:** 2.0  
**Status:** Design Specification

**Depends on:** DOC - 005, DOC - 007, DOC - 009, DOC - 010, DOC - 011, DOC - 012, DOC - 013, DOC - 101

---

# 1. Purpose

Duplicate Management identifies multiple physical occurrences of identical binary content and presents those relationships to the user safely.

The module is based primarily on SHA512, which is the project's logical identity of binary content.

Duplicate Management does not create multiple logical File identities for identical SHA512 values. It operates on multiple `FileLocation` records associated with one `File` identity.

The module may also import external duplicate evidence, particularly hash data produced by tools such as AllDup.

The module does not perform perceptual/visual similarity grouping. Visually similar but binary-different images belong to Set Detection and other analysis modules.

Automatic deletion is outside the default authority of this module.

---

# 2. Core Principles

1. Identical verified SHA512 means identical binary content for normal project operation.
2. One SHA512 corresponds to one logical File identity.
3. Multiple physical copies of that content are represented by multiple FileLocation records.
4. Filename and path do not define duplicate identity.
5. Duplicate detection and duplicate deletion are separate operations.
6. External tools provide evidence; the project database remains authoritative.
7. Ambiguous cases use Review Queue.
8. User decisions have priority over later automatic duplicate suggestions for the protected context.

---

# 3. Duplicate Definition

A duplicate is an additional physical `FileLocation` whose verified SHA512 matches an existing logical File identity already represented by another active physical occurrence.

Example:

```text
File
SHA512 = AAAA

FileLocation #1
TODO/source/image.jpg

FileLocation #2
AI/import/image.jpg
```

Both locations represent the same binary content.

A filename match without matching SHA512 is not an exact duplicate for this module.

Visual or perceptual similarity without matching SHA512 is outside the exact-duplicate definition.

---

# 4. Database Model

Duplicate Management shall use the model defined by DOC - 005:

```text
File
  SHA512 = AAAA

  ├── FileLocation #1
  ├── FileLocation #2
  └── FileLocation #3
```

The module must not create:

```text
File #101 SHA512 = AAAA
File #248 SHA512 = AAAA
```

merely because two physical copies exist.

A duplicate-group identifier may be added as a management object, but it does not replace or redefine File identity.

---

# 5. Detection

The preferred detection mechanism is grouping active physical locations by SHA512.

Conceptually:

```text
FileLocation
    ↓
SHA512
    ↓
GROUP BY SHA512
    ↓
more than one relevant active location
    ↓
duplicate group
```

Historical or missing locations may be included in reports, but the module shall distinguish them from confirmed active duplicates.

---

# 6. Duplicate Scope

The module shall support configurable scopes such as:

```text
selected directory/root
selected collection tree
selected workspace
multiple configured roots
whole active database
external import scope
```

A limited-scope execution must identify its scope clearly.

---

# 7. Existing SHA512 Values

When current SHA512 values already exist in the database, Duplicate Management should reuse them.

It may request a fresh hash verification when:

* a file is new or not fully registered;
* the stored hash is suspected to be stale;
* an external report conflicts with the database;
* the user requests verification;
* filesystem state requires confirmation.

A failed hash calculation must never produce a fabricated identity.

---

# 8. AllDup Import

The module may import external results from AllDup or another compatible tool.

Imported evidence may contain:

```text
path
SHA512
file size
filename
```

The importer treats these values as external evidence.

The project database remains authoritative after verification.

The importer must not blindly:

* create a new logical File identity;
* change protected classification;
* select a master irreversibly;
* delete physical files.

---

# 9. AllDup Import Cases

The import shall distinguish at least:

### Exact match

External path and SHA512 match the current known physical location.

### Physical file not yet registered

The external report identifies a file that is not currently represented in the database.

The normal registration mechanism is Scanner. Duplicate Management may report the discrepancy but must not bypass the Scanner/File Identity rules.

### Database content absent from external report

The database knows a file/location that the external scan did not include. This is not automatically an error because scopes may differ.

### SHA512 conflict

The external tool reports a different SHA512 for a path than the database records.

This is an integrity condition requiring verification and must not be silently resolved.

---

# 10. Duplicate Group

A Duplicate Group is a management view over multiple relevant physical locations that share one SHA512 identity.

Example:

```text
Duplicate Group
SHA512 = AAAA

1. TODO/source/image.jpg
2. AI/import/image.jpg
3. Anime/Genshin/Furina/0007/image.jpg
```

The group does not create a new File identity.

---

# 11. Master / Preferred Location

A Duplicate Group may have a proposed preferred physical location.

The preference may consider:

* explicit user choice;
* protected/manual status;
* valid primary placement;
* valid Theme placement;
* AI/TODO status;
* access policy;
* accessibility and verification state;
* metadata completeness;
* configured user preference.

There is no universal requirement that the oldest, newest, shortest-path or first-discovered location wins.

If multiple locations are equally suitable, the module should use Review Queue instead of guessing.

Selecting a preferred location does not authorize deletion of any other location.

---

# 12. Duplicate States

A duplicate-group management object may use states such as:

```text
DETECTED
VERIFIED
MASTER_PROPOSED
REVIEW_REQUIRED
USER_RESOLVED
PARTIALLY_RESOLVED
```

The implementation may use another state model, provided it distinguishes detection from user-authorised cleanup.

---

# 13. Review Queue Integration

Review Queue is used when duplicate handling is not deterministic.

Examples include:

* equally suitable preferred locations;
* conflicts with user-protected files;
* SHA512 inconsistencies;
* duplicate occurrences across important collection trees;
* destructive cleanup involving a protected location;
* unclear external evidence.

A review case should identify:

```text
SHA512
candidate locations
root/collection role
verification status
proposed preferred location
reason
source of evidence
```

---

# 14. User Decisions

User decisions may include:

```text
ACCEPT
REJECT
MODIFY
DEFER
```

A selected preferred location becomes authoritative for the relevant protected context.

Later automatic execution must not silently replace that decision.

---

# 15. Deletion and Cleanup

Duplicate Management is primarily a detection/decision module.

It must not permanently delete duplicate physical files merely because one location is preferred.

A separate authorised cleanup operation may act on an explicit user decision, subject to access policy and the applicable filesystem/database consistency rules.

Before destructive cleanup, the system should show:

```text
SHA512
preferred location
locations to remove/archive
current statuses
reason
user decision
```

Deleting a physical duplicate location must not delete the File identity when another active location still exists.

---

# 16. Duplicates Across Collection Trees

Duplicates may legitimately occur across:

```text
PRIMARY trees
THEME_FALLBACK
AI
TODO
other configured roots
```

The duplicate relationship itself does not determine semantic correctness.

Classification and placement remain the responsibility of the relevant modules and user workflow.

---

# 17. Missing and Archived Locations

The module shall distinguish:

```text
multiple active physical locations
```

from:

```text
one active location + historical/missing location
```

A missing or unavailable FileLocation is not a confirmed active duplicate.

Retained historical File identities and FileLocation history are handled according to DOC - 012 and DOC - 202.

---

# 18. File Identity Changes

If a physical file changes from:

```text
SHA512 A
```

to:

```text
SHA512 B
```

it leaves the duplicate group for A and becomes an occurrence of B where another B identity exists.

A rename or move without SHA512 change does not change duplicate membership.

---

# 19. Repeated Execution

Duplicate Management is independently executable and may be run repeatedly.

Example:

```text
Day 1   Scanner
Day 2   Duplicate Management
Day 5   Scanner
Day 6   Duplicate Management
Day 8   AllDup import
Day 9   Duplicate Management
```

Each execution reads current database state.

The module may reuse valid existing duplicate information where appropriate, but it must not assume that previous execution was the final run.

---

# 20. Database Access

The module reads:

```text
File
FileLocation
Collection Definition/root context where required
File Events where relevant
Review/User Decisions where applicable
```

It writes:

```text
Duplicate Group information
Duplicate relationships
external import information where applicable
ModuleExecution state
Review Queue items
relevant File Events where applicable
```

It must not overwrite analysis results owned by other modules.

---

# 21. Performance

The project targets approximately 5,000,000 image files.

Exact duplicate detection should use indexed SHA512 grouping rather than all-to-all image comparison.

The entire collection must not be loaded into application memory.

External imports should be processed incrementally where practical.

---

# 22. Threading and Resource Usage

Parallel work may be used for:

* optional hash verification;
* external report parsing;
* filesystem validation;
* preparation of duplicate reports.

Worker counts may be configurable.

Concurrent workers must not create inconsistent duplicate state or repeated review cases for the same execution context.

---

# 23. Error Handling

Per-file or per-record errors should not unnecessarily terminate unrelated processing.

Typical errors include:

```text
unreadable file
hash failure
invalid external report
path unavailable
SHA512 conflict
permission failure
database write failure
```

Errors are logged according to DOC - 011.

Integrity-threatening failures may stop the affected operation when continued processing would create unsafe state.

---

# 24. Logging

Each execution shall create a ModuleExecution record and log according to DOC - 007 and DOC - 011.

The summary should include where applicable:

```text
scope
files examined
physical duplicate locations
duplicate groups
verified hashes
AllDup records imported
inconsistencies
Review Queue entries
preferred-location proposals
errors
duration
```

---

# 25. Relationship with Scanner and Reconciliation

Scanner establishes File and FileLocation records.

DOC - 402 reconciles filesystem, database and Collection Definition state.

DOC - 403 handles verified missing records and registration of physical files without records through the Scanner workflow.

Duplicate Management consumes the resulting consistent identity/location state rather than replacing those mechanisms.

---

# 26. Acceptance Criteria

Duplicate Management is compliant when:

* one SHA512 corresponds to one logical File identity;
* multiple physical copies can be represented by multiple FileLocation records;
* exact duplicates can be detected efficiently by SHA512;
* AllDup evidence can be imported without bypassing project identity rules;
* master/preferred-location selection is distinguishable from deletion;
* ambiguous cases use Review Queue;
* user decisions are protected;
* duplicate cleanup never silently deletes physical files;
* duplicate detection remains independent of visual Set grouping;
* repeated executions are safe for multi-million-file collections.

---

# End of DOC - 204
