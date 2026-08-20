# DOC - 404 – Recovery and Rescan Procedures

**Project:** AI Image Collection Management System  
**Document:** DOC - 404  
**Version:** 1.0  
**Status:** Design Specification

---

## 1. Purpose

This document defines safe operational procedures for returning the project to a consistent working state after an interruption, failure, storage change, incomplete execution, or project restoration.

It describes **what should happen after an abnormal event and in what order**, while the detailed mechanisms for backup/restore, database maintenance, orphan handling and individual modules remain defined elsewhere.

DOC - 404 does not replace:

* DOC - 202 – Database Maintenance;
* DOC - 203 – File Renamer;
* DOC - 204 – Duplicate Management;
* DOC - 206 – Import / Export / Recovery Utility;
* DOC - 403 – Orphan and Missing File Management;
* DOC - 101 – Scanner.

---

## 2. Core Principle

After an abnormal event, the system must first establish a trustworthy view of the current filesystem and database state before normal automated processing resumes.

The project must not assume that an interrupted execution completed merely because the program process ended.

The safe recovery pattern is generally:

```text
stop automatic processing
        ↓
identify the failure/change
        ↓
verify database state
        ↓
verify affected filesystem roots
        ↓
reconcile file identity / locations
        ↓
resume Scanner if required
        ↓
resume individual modules as required
        ↓
resume AutoSort / other modifying operations
```

The exact sequence may be shortened when the failure is known to have affected only a non-destructive operation.

---

## 3. Definitions

### Interrupted execution

A module or tool was stopped before its normal completion state was recorded.

### Storage change

A root, disk, volume, mount point or physical storage location has changed while the project still contains database knowledge of the previous location.

### Database restore

The project database has been replaced or restored from an earlier backup.

### Configuration restore

Application configuration or Collection Definition has been restored from a previously exported state.

### Recovery state

A temporary operational state in which the project is being verified and normal automated modifications are restricted until consistency has been re-established.

---

## 4. Recovery Mode

Where a failure may have left the filesystem and database in an uncertain relationship, the application should enter a recovery-oriented operating mode.

While in recovery mode:

* destructive or bulk filesystem operations should be disabled;
* AutoSort should not continue blindly from an interrupted state;
* database cleanup should not be performed solely to hide inconsistencies;
* analysis modules may be run only when their input scope is known to be safe;
* Scanner, integrity validation and recovery utilities may be used to reconstruct the current state.

Recovery mode is an operational state, not a permanent database state for individual files.

---

## 5. Interrupted Scanner Execution

Scanner is the base mechanism for registering filesystem contents in the database.

If Scanner is interrupted:

```text
files already successfully committed
        ↓
remain valid

files not yet processed
        ↓
remain to be scanned
```

The next Scanner execution must be able to continue or repeat the scan safely.

The interruption must not require already verified files to be treated as corrupted merely because later files were not processed.

This follows the project's non-transactional scanning principle: successful file-level persistence is not rolled back because an unrelated file failed later.

---

## 6. Interrupted Analysis Module

If an analysis module stops unexpectedly:

```text
completed results
        ↓
remain valid

unfinished files
        ↓
remain NOT_PROCESSED / otherwise incomplete
```

The module may be restarted without rerunning unrelated modules.

A restart must rely on the current database state rather than assuming that the previous execution reached its final summary.

A partially completed module execution shall not automatically invalidate results from other modules.

---

## 7. Interrupted File Operation

If a file move or rename operation is interrupted, the recovery procedure must establish the actual filesystem state before applying any further action.

The system must not assume either of these outcomes without checking:

```text
operation failed
operation succeeded
```

For a file involved in a pending operation, verify:

* whether the source still exists;
* whether the destination exists;
* whether the filesystem object at the relevant path has the expected SHA512;
* whether the database still reflects the previous path;
* whether another file now occupies the destination.

Only after the physical state is known may the database and pending workflow be reconciled.

---

## 8. Database Restore

After restoring the database using DOC - 206, the database represents the state captured by the backup rather than necessarily the current filesystem state.

The recovery sequence is:

```text
restore database/configuration
        ↓
validate restored configuration
        ↓
verify configured roots
        ↓
scan/reconcile current filesystem
        ↓
resolve discrepancies
        ↓
resume normal module execution
```

The system must not assume that a restored database automatically describes the current contents of every storage root.

The user should expect that analysis results may refer to files that have moved, been renamed, been deleted, or appeared after the backup was created.

---

## 9. Configuration or Collection Definition Restore

If Collection Definition or application configuration is restored from an earlier snapshot, the restored definition becomes the active configuration only after validation.

The system should verify at minimum:

* configured roots are syntactically valid;
* required roots can be resolved where they are expected to exist;
* roles and access policies are valid;
* traversal rules are valid;
* no conflicting root or boundary definitions exist.

A restored Collection Definition must not cause immediate filesystem modifications merely because it differs from the previously active definition.

Changes to FINAL structure remain subject to the user-controlled Collection Definition workflow.

---

## 10. Storage Path Change

When a collection root moves from one path to another, for example:

```text
D:\Collection
        ↓
E:\Collection
```

the recovery process must treat the event as a path/configuration change, not as deletion of every file.

The correct sequence is:

```text
update/restore root configuration
        ↓
verify new root
        ↓
scan/reconcile filesystem
        ↓
match existing files by SHA512
        ↓
update physical locations
```

Moving a file or changing its root path does not change its SHA512 identity.

If the same SHA512 is found at a new location, it represents the same logical binary content.

---

## 11. Offline Disk or Unavailable Root

A temporarily inaccessible storage root must not be interpreted as mass deletion.

Example:

```text
Root: E:\Anime

E: drive temporarily unavailable
```

The system must not immediately delete thousands of database records merely because the root cannot currently be accessed.

The operator must first establish whether the root is:

* temporarily unavailable;
* disconnected;
* mounted under another path;
* damaged;
* intentionally removed.

Only after the physical state is known should DOC - 403 be used to remove records for genuinely missing files.

---

## 12. Orphan and Missing File Recovery

After recovery or rescan:

```text
DB record + file absent
        ↓
DOC - 403 handling
        ↓
remove the record after confirmed absence
```

and:

```text
physical file + no DB record
        ↓
Scanner
        ↓
create the file record
```

If a newly discovered file has a SHA512 that already exists in the database, the system must treat it as another physical occurrence of the same logical content rather than creating a second binary identity.

---

## 13. Recovery After Partial Database Corruption

If the database itself is known to be damaged, normal modules should not be used to guess the missing state.

The preferred sequence is:

```text
stop normal processing
        ↓
backup the damaged database if feasible
        ↓
restore a known-good database using DOC - 206
        ↓
validate restored database
        ↓
rescan/reconcile current filesystem
        ↓
re-run only the modules whose results are missing
```

A complete rebuild may be performed when recovery from an existing database is not trustworthy.

The exact rebuild procedure belongs to Database Maintenance.

---

## 14. Recovery After Backup Restoration

Restoring a project backup does not imply restoring the physical images.

DOC - 206 may restore:

```text
Database
Collection Definition
Configuration
```

while the current image files remain on their existing storage.

The recovery process must therefore compare the restored project state with the actual current filesystem.

Existing analysis results may still be usable when they refer to the same SHA512 content.

---

## 15. Recovery of Module Results

A recovery process must distinguish between:

```text
file identity survived
```

and:

```text
module result survived
```

If a file's SHA512 is still known and unchanged, its valid existing module results may remain usable even if its physical path changed.

If module results were lost during database recovery, the user may use DOC - 205 or rerun the affected module.

The system must not require unrelated modules to be re-executed merely because one module's results were lost.

---

## 16. Manual Decisions During Recovery

Protected user decisions defined through DOC - 013 must not be silently replaced simply because a database restore, rescan or module rerun produced older or conflicting automatic results.

When manual decision history is missing because the restored backup predates the decision, the restored database represents the earlier known state. The system should not fabricate a later manual decision that is no longer present in the restored data.

Where a recovery process creates uncertainty about an existing manual correction, the case should be reported rather than guessed.

---

## 17. Review Queue During Recovery

Recovery-generated discrepancies that require user judgement may be represented through the common Review Queue.

Examples include:

* uncertain destination after a restore;
* conflicting current and restored paths;
* ambiguous ownership of a physical file occurrence;
* a restored Collection Definition that no longer matches user intent.

Review Queue remains the user-decision mechanism. Recovery does not create a separate recovery decision queue.

---

## 18. Recovery and FINAL

Recovery procedures must not use recovery itself as permission to create or restructure FINAL.

If the restored state differs from the current FINAL filesystem, the discrepancy must first be identified.

A recovery process may restore the **definition** of FINAL, but it must not silently create missing FINAL directories or move images merely because the restored definition contains them.

Any approved physical correction must pass through the normal authorised workflow and directory policies.

---

## 19. Recommended Recovery Order

For a general project-wide incident, the preferred sequence is:

```text
1. Stop automated filesystem modifications.
2. Identify the incident and affected roots/modules.
3. Preserve logs and, where possible, the current database state.
4. Restore database/configuration only when required.
5. Validate restored configuration and Collection Definition.
6. Verify physical storage availability.
7. Rescan/reconcile affected roots.
8. Resolve missing/orphan records according to DOC - 403.
9. Validate collection consistency where appropriate.
10. Resume required analysis modules.
11. Resume AutoSort or other filesystem-modifying modules only after state is trustworthy.
```

Not every incident requires every step.

The principle is to perform the smallest safe recovery operation that restores a trustworthy state.

---

## 20. Recovery After Computer or Application Restart

A normal operating-system or application restart is not automatically a recovery incident.

On restart, the application should inspect incomplete Module Execution records and pending Review Queue work as normal persisted state.

The user may resume the affected module without rebuilding the database.

Only evidence of an inconsistent filesystem/database relationship should trigger the stronger recovery procedures defined here.

---

## 21. Logging and Recovery Records

Recovery actions should be logged according to DOC - 011.

Where applicable, the recovery record should contain:

```text
incident/recovery identifier
start time
reason
affected roots
affected modules
restore action, if any
rescan action
reconciliation result
unresolved issues
final recovery status
```

Recovery logs should not be deleted merely because normal processing resumed.

---

## 22. Safety Rules

The following rules are mandatory:

1. A failed process must not automatically imply failed file processing for unrelated files.
2. A temporarily unavailable disk must not be treated as mass deletion.
3. Database restore must be followed by filesystem verification when the filesystem may have changed since the backup.
4. A storage path change does not change SHA512 identity.
5. A file without a database record is registered by Scanner.
6. A confirmed missing file record is handled according to DOC - 403.
7. Recovery must not create new FINAL structure merely because a restored definition contains it.
8. Protected user decisions must not be silently overwritten.
9. Recovery discrepancies requiring user judgement use Review Queue.
10. Automatic filesystem modifications resume only after the affected state is sufficiently trustworthy.

---

## 23. Acceptance Criteria

DOC - 404 is satisfied when the project has documented procedures for:

* interrupted Scanner execution;
* interrupted analysis execution;
* interrupted move/rename operations;
* database restore;
* Collection Definition/configuration restore;
* storage path changes;
* temporarily unavailable storage roots;
* orphan files and missing records;
* partial database corruption;
* recovery of module results;
* preservation of manual decisions;
* safe return to normal AutoSort and module execution.

---

# End of DOC - 404
