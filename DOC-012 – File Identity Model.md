# DOC - 012 – File Identity Model

**Project:** AI Image Collection Management System

**Document:** DOC - 012

**Version:** 3.0

**Status:** Design Specification

---

# 1. Purpose

This document defines how binary image content is identified and tracked throughout the project, independently of filename and physical location.

The central rule is simple:

```text
SHA512
    = logical identity of the binary content
```

An internal `file_id` may be used as a technical database surrogate, but it is not the logical identity of the file.

Physical occurrences of the same binary content are tracked separately from the binary-content identity.

---

# 2. Identity Model

The project distinguishes three concepts:

```text
SHA512
    = identity of binary content

File
    = database entity representing one SHA512 identity

FileLocation
    = one physical filesystem occurrence of that File
```

This distinction is mandatory because the same binary content may legitimately exist at multiple physical locations.

Example:

```text
SHA512 = ABC...

File
└── FileLocation #1 → D:\Collection\image.jpg
└── FileLocation #2 → E:\Backup\image.jpg
```

The two locations do not represent two different image identities.

---

# 3. SHA512 as File Identity

SHA512 is the logical primary key of binary-content identity.

The project assumes that identical SHA512 values represent identical binary content.

The theoretical probability of two intentionally different files producing the same SHA512 is treated as negligible for normal project operation. An apparent collision or inconsistent hash result is therefore an integrity error, not a normal duplicate-resolution case.

The system must never resolve such an event by silently substituting another hash.

---

# 4. Internal `file_id`

An implementation may assign an internal:

```text
file_id
```

It is a technical relational identifier used for efficient database relationships where appropriate.

It is:

* unique within the database instance;
* independent of filename and path;
* not a replacement for SHA512 as logical file identity;
* not guaranteed to remain stable after a database rebuild or migration.

Long-term or cross-database references must not depend solely on `file_id`.

---

# 5. File Entity

`File` represents one unique binary-content identity.

Its logical key is:

```text
SHA512
```

A `File` record may remain in the database while it has no currently active physical location only when the project deliberately retains that identity for historical or recovery purposes.

The retention of such a record does not mean that a physically missing file is still part of the active collection.

---

# 6. FileLocation Entity

`FileLocation` represents one physical occurrence of a `File`.

Typical information includes:

```text
location_id
file_id / SHA512 reference
current_path
filename
extension
size_bytes
modified_time
root_id
first_seen
last_seen
state
```

A physical rename or move changes the location state/path, not the SHA512 identity.

Several active `FileLocation` records may reference the same `File` when duplicate physical copies exist.

---

# 7. Duplicate Physical Occurrences

If multiple physical files have the same SHA512:

```text
same SHA512
→ same File identity
→ multiple FileLocation records
```

This is an expected state and is handled operationally by Duplicate Management.

The existence of multiple locations does not create multiple logical `File` entities.

Duplicate Management may determine which location should be considered preferred or canonical, but that decision does not change the SHA512 identity.

---

# 8. Filename Changes

Changing a filename does not change file identity.

Example:

```text
AI/Furina (1).jpg
        ↓
AI/Furina.jpg
```

provided the binary content is unchanged:

```text
SHA512 = unchanged
File    = unchanged
```

Only the physical location/name state changes.

All analysis and classification results remain associated with the same `File` identity.

---

# 9. Physical Relocation

Moving a file between configured locations does not change its identity when the binary content is unchanged.

Examples include:

```text
SOURCE → AI
AI → FINAL
FINAL → AI
AI → SOURCE
Themes → PRIMARY
```

The operation may change:

* `current_path`;
* filename;
* Collection Root;
* FileLocation state.

It does not change SHA512 or create a new `File` identity.

---

# 10. Binary Content Modification

If the binary content changes, the SHA512 changes.

Examples include:

* image editing;
* resizing;
* recompression;
* metadata modifications that alter file bytes;
* pixel changes;
* replacing the file with another binary object.

The resulting SHA512 represents a new binary identity.

The database must not silently change:

```text
File(AAAA)
```

to:

```text
File(BBBB)
```

Instead:

```text
old binary
SHA512 = AAAA

new binary
SHA512 = BBBB
```

are represented as separate logical identities.

---

# 11. Lifecycle of a File Identity

The identity lifecycle is separate from the physical-location lifecycle.

A typical active identity is:

```text
File(AAAA)
    ↓
one or more active FileLocations
```

If all physical occurrences are deliberately removed and the project retains the identity for historical/recovery purposes, the `File` identity may remain archived.

However, this is not the normal representation of an ordinary missing file. Verified obsolete records are handled by DOC - 403 according to the current project policy.

---

# 12. Archived Identity

`ARCHIVED` is reserved for a retained historical `File` identity that is no longer part of the active physical collection state.

It is **not** a mandatory intermediate state for every file that temporarily or permanently disappears from disk.

The distinction is:

```text
verified obsolete active record
    → DOC - 403 may remove it

historical identity deliberately retained
    → File may be ARCHIVED
```

An archived identity retains its original SHA512 and may retain historical metadata/events.

If the same unchanged SHA512 is later discovered and the archived identity still exists, Scanner may reactivate that identity rather than creating another logical `File`.

---

# 13. Verified Missing File

A database record whose physical file has been verified as absent from the managed filesystem is handled by DOC - 403.

The default project rule is:

```text
physical absence confirmed
        ↓
remove obsolete active File record/location
```

A temporary inability to inspect a root is **not** sufficient evidence of absence.

Examples:

```text
Drive disconnected
≠
file deleted

Permission denied
≠
file deleted
```

The Scanner/reconciliation workflow must establish actual absence before the record is removed.

Historical events may remain when required for auditability, but the obsolete active record does not remain merely as a missing-file archive.

---

# 14. Reappearance of Retained Historical Identity

If a retained archived `File` identity is encountered again and its SHA512 matches exactly, the existing logical identity may be reactivated.

Example:

```text
File(AAAA)
    ARCHIVED
        ↓
Scanner finds SHA512 AAAA
        ↓
File(AAAA)
    ACTIVE
```

No second logical identity is created for the same SHA512.

---

# 15. SHA512 Calculation Failure

If SHA512 cannot be calculated reliably, the system must not:

* invent a placeholder hash;
* create a valid `File` identity from an incomplete calculation;
* reuse an unrelated existing identity.

The failure is logged according to DOC - 011 and the file remains outside the set of successfully identified binary objects until a valid SHA512 is obtained.

---

# 16. Identity and Analysis Results

Analysis results belong to the binary-content identity represented by `File`.

Therefore:

```text
path changed
    → results remain valid

filename changed
    → results remain valid

SHA512 changed
    → previous results do not apply to the new identity
```

A change of physical location does not require re-analysis merely because the path changed.

A new SHA512 requires the new binary identity to establish its own current analysis state.

---

# 17. Identity and Manual Decisions

A manual decision is associated with the relevant `File` identity and decision context according to DOC - 013.

Moving or renaming the same binary object does not by itself erase a protected user decision.

If binary content changes and therefore SHA512 changes, the new binary identity must not silently inherit a manual decision belonging to a different binary object unless a separate documented migration mechanism explicitly authorises that transfer.

---

# 18. Identity and Review Queue

Review Queue cases involving files should reference the current SHA512 identity and, where used, the internal `file_id` and `location_id`.

A review case created for:

```text
SHA512 = AAAA
```

must not be silently applied to:

```text
SHA512 = BBBB
```

when binary content has changed.

Physical path changes require revalidation of the current location before a filesystem action is performed, but do not change binary identity.

---

# 19. Identity and Duplicate Management

Duplicate Management operates on physical occurrences sharing the same SHA512.

Its logical model is:

```text
File(AAAA)
├── FileLocation A
├── FileLocation B
└── FileLocation C
```

Duplicate management may select one preferred location, but:

* the preferred location is not a new identity;
* deleting a duplicate location does not delete the `File` identity if another active location remains;
* the same SHA512 at a newly discovered location is associated with the existing `File` identity.

---

# 20. Relationship with Scanner

Scanner is responsible for establishing and updating file identity from the physical filesystem.

Its standard process is:

```text
filesystem
    ↓
calculate SHA512
    ↓
lookup File by SHA512
    ↓
create/reactivate File if required
    ↓
create/update FileLocation
```

Scanner must not create multiple logical `File` identities for the same verified SHA512 merely because the content appears at multiple locations.

---

# 21. Relationship with Database Schema

DOC - 005 implements this identity model.

The schema shall preserve the distinction between:

```text
File
FileLocation
```

and shall enforce the uniqueness of SHA512 within the logical `File` entity.

`file_id`, where retained, is a technical surrogate only.

---

# 22. Relationship with Database Maintenance and Recovery

DOC - 202 defines database maintenance operations.

DOC - 403 defines verified missing/orphan-file handling.

DOC - 404 defines recovery/rescan procedures after abnormal events.

These documents must preserve the SHA512 identity rules defined here.

A database rebuild may recreate different `file_id` values while preserving the same SHA512 identities.

---

# 23. Integrity Principles

The following are architectural invariants:

1. SHA512 is the logical identity of binary content.
2. Identical verified SHA512 values represent the same binary content.
3. Multiple physical occurrences of the same SHA512 use one logical `File` identity and multiple `FileLocation` records.
4. Filename and path do not define binary identity.
5. Moving or renaming a file does not change SHA512.
6. Changing binary content and therefore SHA512 creates a distinct binary identity.
7. SHA512 is never overwritten to convert one binary identity into another.
8. A SHA512 calculation failure never creates a fabricated identity.
9. A temporary inability to access storage is not proof that a file was deleted.
10. Verified obsolete records are removed according to DOC - 403; historical identities may be retained separately as `ARCHIVED` where explicitly required.
11. A retained archived identity may be reactivated when the same unchanged SHA512 is rediscovered.
12. User decisions and review cases must remain tied to the correct binary identity.

---

# 24. Acceptance Criteria

The File Identity Model is correctly implemented when:

* SHA512 uniquely identifies each logical binary-content identity;
* multiple physical copies with one SHA512 do not create multiple logical `File` identities;
* physical locations are represented separately;
* renames and moves preserve identity;
* binary modifications create new identities;
* stale/obsolete active records can be removed after verified absence;
* temporary storage unavailability does not cause mass deletion;
* retained historical identities can be reactivated when the same SHA512 reappears;
* module results and user decisions remain attached to the correct binary identity;
* database rebuilds may change technical `file_id` values without changing SHA512 identity.

---

# End of DOC - 012
