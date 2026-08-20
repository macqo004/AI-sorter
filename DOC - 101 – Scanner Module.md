# DOC-101

# Scanner Module

**Project:** AI Image Collection Management System

**Document:** DOC-101

**Module:** Scanner

**Version:** 2.1

**Status:** Draft

**Depends on:**

DOC-005
DOC-007
DOC-008
DOC-010
DOC-011
DOC-012
DOC-301
DOC-302

---

# 1. Purpose

Scanner is responsible for synchronizing the project database with the configured filesystem scope.

Scanner performs no semantic image analysis.

Scanner is the module responsible for discovering files that are in scope for the project and for detecting filesystem changes relevant to the database.

Scanner is the **base file-discovery module**: a newly added file must normally be discovered and assigned a valid SHA512 identity by Scanner before other analysis modules can process it through the shared database.

Scanner does not invoke other modules.

---

# 2. Responsibilities

Scanner shall:

* discover new supported image files within configured scan scope;
* detect files that disappeared from configured scan scope;
* detect renames and moves where the same binary identity can be established;
* detect binary-content changes;
* calculate SHA512 when required;
* create or update file records;
* update current filesystem state;
* create relevant file events;
* record Scanner executions;
* generate logs according to DOC-011.

Scanner shall not:

* classify images;
* perform semantic analysis;
* move files;
* rename files;
* create FINAL collection directories;
* execute AI models;
* modify user classifications or manual decisions;
* overwrite analysis results owned by other modules.

---

# 3. Module Independence

Scanner is operationally independent from the other processing and analysis modules, but it is the foundational source of file records in the database.

The normal relationship is:

```text
Filesystem
    ↓
Scanner
    ↓
Database
    ↓
Other modules
```

The other modules do not need Scanner to remain running.

After a file has a valid database record, other modules may be executed in any order and any number of times according to their own specifications.

If new files are added to a configured source/root after the last Scanner execution, those files are not available to database-driven analysis modules until Scanner discovers them.

---

# 4. Supported File Types

Initially supported image formats are:

```text
jpg
jpeg
png
webp
gif
bmp
pns
```

The project may extend this list through configuration or a future specification revision.

The Scanner shall ignore known non-image files including:

```text
mp4
webm
avi
mkv
mov
zip
rar
7z
```

Unknown extensions shall be ignored unless explicitly supported by a future revision.

---

# 5. Scan Scope

Scanner operates on filesystem roots and traversal scopes defined by collection/configuration documents.

Physical directory names such as `TODO`, `AI`, `FINAL`, `Anime` or `Themes` have no inherent meaning to Scanner.

The Scanner determines its scope from the configured Collection Definition and applicable root/access-policy settings.

A scan root may represent, for example:

```text
SOURCE
TRANSITION
FINAL
```

or another explicitly configured role.

Multiple roots may be configured.

---

# 6. Traversal and Scan Depth

Scanner shall not independently invent collection depth rules.

Directory traversal is governed by the configured traversal rules and boundaries defined by Collection Definition.

In particular, Scanner shall respect the distinction between:

* a directory that is part of the configured classification structure;
* a classification boundary after which subdirectories belong to user organization;
* a branch explicitly excluded from traversal.

This prevents organizational folders inside a classified directory from being interpreted as additional semantic levels merely because they exist physically.

Example:

```text
Furina          ← classification boundary
├── 001
├── 002
├── 003
└── Favorites
```

The existence of `001`, `002` or `Favorites` does not cause Scanner to redefine the classification hierarchy.

The exact traversal-rule definitions are owned by DOC-301 and DOC-302.

A module-specific scan mode may additionally limit the physical scope it processes, but such a limit must be explicitly configured.

---

# 7. Access Policy

Scanner may inspect files only within the filesystem scope permitted by the configured Directory Access Policy.

Scanner is primarily a read/discovery module.

It must not use scanning as a justification for modifying files.

The Scanner may write to the project database and logs even when the scanned filesystem root is read-only, provided the database and logging locations themselves are writable.

---

# 8. File Discovery

For every supported file within scope, Scanner should collect or verify, where available:

```text
current path
filename
extension
file size
filesystem modification time
image width
image height
SHA512
```

The database representation is defined by DOC-005 and the file identity by DOC-012.

---

# 9. SHA512 Strategy

SHA512 is the logical binary-content identity of the file.

Scanner should avoid unnecessary recalculation while maintaining a reliable identity model.

For a previously known file, Scanner may first compare inexpensive filesystem metadata such as:

```text
file size
modified time
```

against the stored state.

If the configured change-detection policy indicates that the binary content should be unchanged, the existing SHA512 may be reused.

If the metadata indicates a possible change, or if the file is new and no valid SHA512 exists, Scanner shall calculate SHA512.

A successful content change results in a new SHA512 identity according to DOC-012 rather than overwriting the old binary identity.

Metadata-based optimization is a performance optimization, not a replacement for the SHA512 identity model.

---

# 10. Hash Reliability

Scanner shall treat a successfully calculated SHA512 as valid only when the file was read successfully and the calculation completed without a detected error.

If a calculation fails, Scanner shall:

* log the failure;
* record an appropriate failure state where supported by the database model;
* not invent a placeholder SHA512;
* not expose the file as a successfully identified input to downstream analysis.

Transient or suspicious read conditions may justify a retry or verification pass according to implementation policy.

The project does not implement a normal workflow for theoretical SHA512 collisions. An apparent collision or internal inconsistency is an integrity error requiring investigation.

---

# 11. Change Detection

Scanner shall detect, where possible:

### New file

No current active record exists for the discovered SHA512.

Action:

* if the SHA512 exists in an archived record that is still retained, reactivate that existing file identity rather than creating a second identity for the same binary content;
* otherwise create the new file record;
* assign an internal `file_id` if used;
* store current filesystem state;
* mark the record active.

### Rename

The binary content is unchanged but the filename changed.

Action:

* retain SHA512 identity;
* update current path/filename;
* create a relevant event.

### Move

The binary content is unchanged but the directory changed.

Action:

* retain SHA512 identity;
* update current path;
* create a relevant event.

### Binary modification

The resulting SHA512 differs from the previous binary identity.

Action:

* preserve the previous record/history;
* create the new SHA512 record;
* associate the new filesystem state with the new identity;
* allow affected analysis results to be re-established according to module rules.

### Missing file

A previously known active file is no longer found within the managed scan scope.

Action:

* update lifecycle state according to DOC-012 and maintenance rules;
* create a relevant event where applicable.

---

# 12. Duplicate Binary Files

If multiple physical filesystem entries contain identical binary content, they have the same SHA512 and therefore the same logical binary identity.

Scanner shall not create a different logical file identity solely because the binary content appears under another filename or directory.

Handling of duplicate physical copies is outside the Scanner's primary responsibility.

---

# 13. Database Operations

Scanner may create or update data belonging to filesystem discovery and synchronization, including:

```text
File
File Event
Module Execution
filesystem-state fields owned by Scanner
```

Scanner shall not create semantic analysis results owned by other modules.

Scanner shall write its persistent results to the shared database so that subsequent modules can use the discovered file state without direct communication with Scanner.

---

# 14. Transactions and Failure Isolation

Scanner is not a single all-or-nothing transaction.

Successfully processed files should be committed independently whenever safe to do so.

Example:

```text
File A → OK → saved
File B → ERROR → logged/skipped
File C → OK → saved
```

Failure processing one file must not roll back unrelated successfully processed files.

The exact transaction boundaries are implementation details, provided this failure-isolation rule is preserved.

---

# 15. Threading and Resource Usage

Scanner is designed for parallel execution.

A configurable worker count may be provided:

```text
0 = Automatic
1
2
4
8
16
...
```

Automatic mode selects a reasonable number based on available CPU and configured resource limits.

Scanner should use memory and CPU resources efficiently without exhausting the machine.

Parallel workers must not violate database or filesystem consistency.

---

# 16. Error Handling

Scanner should continue processing whenever safe.

Typical recoverable conditions include:

* access denied;
* unreadable/corrupted image;
* temporary I/O error;
* file locked by another process;
* failure to decode optional image metadata.

The affected item should be logged and skipped or marked appropriately while processing continues.

A database-level failure that prevents safe persistence may stop the Scanner execution because the core purpose of Scanner is database synchronization.

---

# 17. Repeated Execution

Scanner may be executed repeatedly.

Repeated scans are expected and should be optimized to avoid unnecessary SHA512 recalculation and redundant database work.

A later Scanner execution may discover files that did not exist during an earlier execution.

This is normal behaviour and does not imply that other modules failed simply because they previously had no record for those files.

---

# 18. Execution Record and Logging

Each Scanner invocation shall create a Module Execution record according to DOC-005 and DOC-007.

The execution log shall include, where applicable:

```text
start time
finish time
files discovered
new files
modified files
moved files
renamed files
missing/deleted files
files skipped
hash failures
other errors
duration
```

Logs shall comply with DOC-011.

---

# 19. Interaction with Other Modules

Scanner never invokes another module directly.

The communication model is:

```text
Scanner
   ↓
Database
   ↓
Analysis / Processing Modules
```

Analysis and processing modules may later read Scanner-produced file state from the database.

Scanner does not need to know which downstream modules will use the data.

---

# 20. Configuration

Scanner configuration shall obtain its behaviour from the common configuration system.

Configuration may include:

* selected collection/root scopes;
* applicable traversal scope;
* worker count;
* supported extensions;
* resource limits;
* logging options;
* hash verification/retry policy where exposed.

Physical paths must come from collection/configuration data, not hard-coded module logic.

---

# 21. Performance Requirements

Scanner is intended for collections containing millions of files.

Repeated scans should minimize unnecessary work by reusing valid filesystem state and SHA512 results when the configured change-detection policy permits it.

The Scanner should avoid requiring the entire collection to be loaded into memory.

Directory traversal and database operations should be designed for long-running scans over very large collections.

---

# 22. Design Philosophy

Scanner has one deliberately narrow responsibility:

> **Make the database aware of the files that exist within the configured scope and keep their filesystem identity/state synchronized.**

Scanner does not decide what an image means.

Scanner does not decide where an image belongs.

Scanner does not create semantic collections.

Those responsibilities belong to other modules and the collection configuration system.

---

# 23. Future Extensions

Possible future extensions include:

* filesystem event monitoring;
* incremental directory traversal;
* configurable exclusion patterns;
* additional file-integrity checks;
* optimized directory-change detection;
* alternate checksum strategies for specific operational purposes.

Such extensions must not change the fundamental SHA512-based file identity model.

---

# 24. Acceptance Criteria

Scanner is considered compliant when it can:

* discover supported files within the configured scan scope;
* create valid file identities using SHA512;
* reactivate an existing retained archived record when the same unchanged SHA512 is rediscovered;
* detect new, moved, renamed, modified and missing files where supported by the available filesystem information;
* preserve identity across rename and move;
* create a new identity when binary content changes;
* update the database incrementally;
* continue after recoverable per-file errors;
* avoid unnecessary SHA512 recalculation where the configured change-detection policy allows it;
* respect Collection Definition traversal/boundary rules;
* support very large collections without requiring the entire collection in memory;
* generate execution records and logs;
* communicate with other modules only through documented shared database state.

---

# End of DOC-101
