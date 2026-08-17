# DOC-202

# Database Maintenance

**Project:** AI Image Collection Management System

**Document:** DOC-202

**Module:** Database Maintenance

**Version:** 2.0

**Status:** Draft

**Depends on:**

DOC-005
DOC-007
DOC-008
DOC-009
DOC-011
DOC-012
DOC-013
DOC-101
DOC-302

---

# 1. Purpose

Database Maintenance defines the procedures used to preserve the long-term reliability, integrity and recoverability of the project database.

The module may perform operations such as:

* database backup;
* database integrity checking;
* database optimization;
* archived-record management;
* database rebuild;
* consistency verification between database state and the physical collection.

The module does not perform image analysis or collection classification.

Potentially destructive maintenance operations remain explicitly user-controlled.

---

# 2. Maintenance Philosophy

The project database is the authoritative persistent store for file identity, metadata, analysis results, classifications, user decisions and processing history.

The original image files remain the source of binary content.

Database Maintenance must therefore distinguish between:

```text
DATABASE STATE
        and
FILESYSTEM / BINARY STATE
```

Maintenance must preserve information rather than conceal inconsistencies.

The module follows these principles:

* detect problems before correcting them;
* never silently discard information;
* require explicit user action for destructive operations;
* preserve SHA512-based file identity;
* preserve useful history where possible;
* record all maintenance operations according to DOC-011.

---

# 3. File Identity Compatibility

Database Maintenance follows DOC-012.

The logical identity of binary file content is:

```text
SHA512
```

`file_id` is an internal technical database identifier.

`current_path` represents the currently known physical location.

Therefore:

* changing a path does not create a new file identity;
* changing a filename does not create a new file identity;
* changing binary content and therefore SHA512 creates a new binary-file identity;
* an existing ARCHIVED record may be reactivated when the same SHA512 is encountered again, provided the identity record has not been permanently removed.

Maintenance must not replace a SHA512 with a fabricated placeholder value.

---

# 4. Database Backup

## 4.1 Purpose

Backup creates a recoverable copy of the database state.

A backup is strongly recommended before:

* database rebuild;
* schema migration;
* permanent removal of archived records;
* large-scale maintenance;
* other potentially destructive operations.

## 4.2 Operation

Backup is explicitly started by the user unless a separate documented backup system is introduced.

The module shall:

* create the backup;
* verify that the backup completed successfully;
* report the resulting backup location and status;
* log the operation.

The backup should contain the complete database state required for recovery.

---

# 5. Database Integrity Check

## 5.1 Purpose

Integrity Check verifies the structural and logical consistency of the database.

Checks may include:

* missing required SHA512 values;
* invalid SHA512 representation;
* duplicate active SHA512 identities;
* invalid or duplicated technical identifiers;
* broken foreign-key relationships;
* analysis results without a valid file identity;
* classification results without a valid file identity;
* invalid collection/root references;
* inconsistent lifecycle states;
* malformed Review Queue records;
* missing required current-path information where applicable.

## 5.2 Filesystem Consistency

Maintenance may compare database records against configured collection roots.

Examples:

```text
Database record exists
    but physical file is missing
```

or:

```text
Physical file exists
    but no database identity exists
```

Such discrepancies must be reported for review rather than silently repaired.

## 5.3 Result

The result shall be provided as a readable report and logged according to DOC-011.

## 5.4 Automatic Repair

Integrity Check shall not automatically perform destructive or ambiguous repairs.

Safe deterministic repairs may be introduced by a future explicitly documented maintenance operation, but the default behaviour is:

```text
DETECT
  ↓
REPORT
  ↓
USER DECISION / DOCUMENTED SAFE REPAIR
```

Review Queue may be used for ambiguous cases.

---

# 6. Database Optimization

Optimization may be useful after:

* large record deletions;
* extensive updates;
* index rebuilding;
* database rebuilds;
* other operations that materially change database storage.

Optimization may include database-engine-specific operations such as:

* reclaiming unused space;
* rebuilding indexes;
* compacting storage;
* updating statistics.

Optimization must not change file identity or analysis semantics.

It is normally user-initiated.

The module may recommend optimization but must not silently perform a potentially disruptive maintenance operation.

---

# 7. Archived Record Management

Archived records represent historical binary-file identities that are no longer current in the active collection state.

According to DOC-012:

* ARCHIVED records are not automatically deleted;
* archived history may remain useful for identity/history purposes;
* the same SHA512 may later reactivate an archived identity if that record still exists.

## 7.1 Permanent Removal

Archived records may be permanently removed by an explicitly initiated user operation.

Before removal, the module shall display at least:

* number of records affected;
* estimated database impact;
* whether related historical analysis or event information will also be affected;
* backup recommendation.

Permanent deletion is irreversible unless a suitable backup exists.

## 7.2 Automatic Cleanup

Archived records shall not be silently removed merely because they have reached a certain age unless a future documented maintenance policy explicitly enables such behaviour.

---

# 8. Database Rebuild

## 8.1 Purpose

Database Rebuild reconstructs the database when the existing database cannot be safely relied upon or when a complete rebuild is intentionally requested.

Typical reasons include:

* severe corruption;
* unrecoverable integrity violations;
* deliberate database reconstruction;
* migration to a new database structure where rebuilding is safer than in-place conversion.

## 8.2 Rebuild Principle

Rebuild produces a new database from the current physical collection and approved configuration.

The rebuild does not assume that the old database can be trusted as the source of current filesystem state.

Typical sequence:

1. Create a verified backup of the existing database.
2. Create the new database structure.
3. Load the applicable project configuration and Collection Definition.
4. Run Scanner against configured roots.
5. Recreate file identities from the files actually found.
6. Perform required integrity checks.
7. Mark the rebuilt database ready for normal module operation.

The exact rebuild orchestration may use the documented Scanner and execution mechanisms rather than directly embedding Scanner implementation into Database Maintenance.

## 8.3 Identity After Rebuild

`file_id` values may change because they are technical identifiers of the current database instance.

SHA512 remains the logical binary-content identity.

Example:

```text
Before rebuild:
file_id = 15231
SHA512 = AAAA

After rebuild:
file_id = 17
SHA512 = AAAA
```

The file identity represented by SHA512 remains the same.

External or long-term references must not rely solely on `file_id`.

## 8.4 Analysis Data After Rebuild

A rebuild restores the file database state based on the physical collection.

Existing analysis results are not automatically guaranteed to be restored unless an explicit export/import mechanism exists.

After rebuild, analysis modules may need to execute again according to their own reprocessing rules.

A future dedicated import/export mechanism may restore compatible analysis history without changing the file identity model.

---

# 9. Review Queue Integration

Database Maintenance may create Review Queue entries for ambiguous or potentially dangerous situations, including:

* uncertain database repairs;
* damaged relations where multiple repairs are plausible;
* inconsistencies requiring user interpretation;
* cases where the database and filesystem disagree in a way that cannot be safely resolved automatically.

Review Queue does not itself perform maintenance operations.

A Review Queue decision may authorize, reject, modify or defer a proposed maintenance action according to DOC-013.

---

# 10. User Confirmation Requirements

The following operations require explicit user initiation or confirmation unless another document explicitly defines a safe automatic policy:

| Operation | Automatic execution |
|---|---|
| Backup | No |
| Optimization | No |
| Integrity Check | No |
| Permanent archived-record deletion | No |
| Database Rebuild | No |
| Ambiguous repair | No |

The module may provide recommendations, previews or reports before execution.

---

# 11. Incremental and Failure-Safe Operation

Database Maintenance should preserve successfully completed work when practical.

A failure affecting one maintenance step must not silently invalidate unrelated successfully completed work.

For example, a failed integrity check report generation must not erase previously stored database records.

Destructive operations should use appropriate transaction or staging mechanisms for the selected database technology.

---

# 12. Logging

All Database Maintenance operations shall follow DOC-011.

Logs should contain:

```text
operation
execution_id where applicable
start time
completion time
result
records affected
errors
warnings
user-approved action where applicable
```

Destructive operations must have enough information recorded to make the action auditable.

---

# 13. Concurrency and Execution

Database Maintenance is user-initiated.

The module must respect the execution rules defined by DOC-007 and the database access rules defined by DOC-009.

Potentially conflicting maintenance operations should not run concurrently with another operation that could invalidate their assumptions.

The implementation may enforce a maintenance lock or equivalent protection where necessary.

This does not make other analysis modules globally dependent on Database Maintenance during normal operation.

---

# 14. Performance and Resource Usage

Database Maintenance should be appropriate for databases representing millions of files.

Operations should avoid unnecessary full-database scans where indexed or incremental approaches are practical.

Memory may be used to improve performance within configured system limits, but normal operation must not require loading the entire file collection into RAM.

---

# 15. Design Principles

Database Maintenance follows these principles:

* preserve data rather than hide errors;
* detect before correcting;
* user control over destructive operations;
* SHA512 remains the logical file identity;
* technical `file_id` may change across database rebuilds;
* successfully completed work should survive unrelated failures;
* database and filesystem consistency must be verified rather than assumed;
* maintenance is independent of image-analysis semantics.

---

# 16. Acceptance Criteria

Database Maintenance is considered compliant when it can:

* create and verify database backups;
* perform integrity checks;
* report database/filesystem inconsistencies;
* manage archived records safely;
* rebuild the database from the current collection when required;
* preserve SHA512-based file identity across rebuilds;
* treat `file_id` as a technical database-instance identifier;
* integrate with Review Queue for ambiguous maintenance decisions;
* require explicit user control for destructive operations;
* maintain readable maintenance logs;
* operate safely on a database representing millions of files.

---

# End of DOC-202
