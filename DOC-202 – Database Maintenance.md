# DOC - 202 – Database Maintenance

**Project:** AI Image Collection Management System  
**Document:** DOC - 202  
**Module:** Database Maintenance  
**Version:** 3.0  
**Status:** Design Specification

**Depends on:** DOC - 005, DOC - 007, DOC - 009, DOC - 011, DOC - 012, DOC - 013, DOC - 101, DOC - 206

---

# 1. Purpose

Database Maintenance preserves long-term database reliability, integrity, recoverability and storage efficiency.

The module performs database-level maintenance. It does not perform image analysis or decide image classification.

Potentially destructive operations remain explicitly user-controlled.

---

# 2. Maintenance Philosophy

The database stores persistent project state. The filesystem stores the actual image bytes.

Maintenance must distinguish:

```text
DATABASE STATE
        and
FILESYSTEM / BINARY STATE
```

The module follows these principles:

* detect before correcting;
* do not silently hide inconsistencies;
* preserve SHA512 identity rules;
* protect user decisions;
* require explicit user control for destructive operations;
* preserve useful history where it is intentionally retained;
* log maintenance operations.

---

# 3. File Identity Compatibility

DOC - 012 defines the logical identity model.

The current model is:

```text
SHA512
    = logical binary-content identity

File
    = one logical SHA512 identity

FileLocation
    = physical occurrence of that content
```

Multiple active FileLocation records may reference one File.

A database maintenance operation must not create multiple logical File identities merely because one binary exists in multiple locations.

---

# 4. Backup

Backup creates a recoverable copy of the database state.

A backup is strongly recommended before:

* schema migration;
* database rebuild;
* permanent removal of retained archived identities;
* large-scale maintenance;
* other potentially destructive operations.

The module shall verify backup completion and report the resulting backup and status.

Backup does not automatically back up image bytes. Image backup is a separate storage responsibility.

---

# 5. Integrity Check

Integrity Check verifies structural and logical consistency.

Checks may include:

* missing or malformed SHA512 values;
* duplicate logical SHA512 identities;
* broken File → FileLocation references;
* broken foreign-key relationships;
* analysis results without valid File identity;
* classifications without valid File identity;
* invalid Collection Definition references;
* malformed Review Queue references;
* invalid lifecycle state combinations;
* impossible active FileLocation state.

Filesystem comparison may also be performed, but the module must distinguish an inaccessible root from an actually missing file.

Integrity Check produces a report and does not automatically perform ambiguous or destructive repairs.

---

# 6. Archived Identity Management

`ARCHIVED` is a deliberate historical retention state for a logical File identity that is no longer part of the active physical collection.

It is not the mandatory state for every file that disappears from disk.

Verified obsolete active records are handled by DOC - 403.

Retained archived identities may be permanently removed by an explicit user operation.

Before removal, the module should report:

* number of identities affected;
* related history potentially affected;
* estimated storage impact;
* backup recommendation.

Permanent removal is irreversible without an appropriate backup.

---

# 7. Database Optimization

Optimization may include engine-specific operations such as:

* reclaiming unused storage;
* rebuilding indexes;
* updating statistics;
* compacting the database.

Optimization must not change SHA512 identity, classification meaning or protected manual decisions.

It is normally user-initiated.

---

# 8. Database Rebuild

Database Rebuild reconstructs the database when the current database cannot be safely relied upon or when a deliberate rebuild is required.

Typical sequence:

```text
verified backup
    ↓
new schema/database
    ↓
validated Collection Definition/configuration
    ↓
Scanner against current physical roots
    ↓
File/FileLocation reconstruction
    ↓
integrity validation
    ↓
normal operation
```

A rebuild reconstructs current filesystem-derived state. It does not automatically recreate historical user decisions or analysis history unless these are restored separately through DOC - 206.

`file_id` values may change during a rebuild. SHA512 identity does not.

---

# 9. Analysis Results After Rebuild

A rebuild may lose analysis results unless they were explicitly restored from an export/backup package.

The absence of a result means that no current result is stored. It does not require creation of millions of placeholder `NOT_PROCESSED` rows.

The user may use DOC - 205 to clear/rebuild selected result sets when a full recalculation is desired.

Re-running one module does not require unrelated modules to be rerun.

---

# 10. Review Queue Integration

Ambiguous maintenance situations may create Review Queue cases according to DOC - 013.

The maintenance module must not create a separate maintenance/reconciliation decision queue.

Review Queue decisions are user decisions; maintenance executes only the authorised database-level consequence.

---

# 11. User Confirmation

These operations require explicit user initiation or confirmation under the current architecture:

| Operation | Automatic execution |
|---|---|
| Backup | No |
| Optimization | No |
| Integrity Check | No |
| Permanent archived-identity deletion | No |
| Database Rebuild | No |
| Ambiguous repair | No |

Safe read-only diagnostics may be automated where separately specified.

---

# 12. Failure Isolation

A maintenance failure must not silently invalidate unrelated completed database work.

Destructive operations should use safe transactions, staging or engine-supported recovery mechanisms appropriate to the operation.

A partial operation must not be reported as complete success.

---

# 13. Concurrency

Maintenance operations that can invalidate the assumptions of another database operation should not run concurrently with the conflicting operation.

The implementation may use a local maintenance lock or equivalent protection.

This does not make all ordinary analysis modules globally dependent on Database Maintenance.

---

# 14. Logging

Maintenance operations follow DOC - 011.

Logs should include:

```text
operation
execution_id where applicable
start/end time
result
records affected
warnings/errors
user confirmation where applicable
```

Destructive operations must be auditable.

---

# 15. Performance

The module must remain practical for databases representing millions of Files and potentially more FileLocations.

Operations should use indexes, batching and incremental checks where practical.

The entire image collection must not be loaded into memory for ordinary database maintenance.

---

# 16. Relationship with DOC - 402 and DOC - 403

Responsibilities are separated as follows:

```text
DOC - 202
    database maintenance

DOC - 402
    filesystem ↔ database ↔ Collection Definition reconciliation

DOC - 403
    verified missing record removal and physical-file registration workflow
```

DOC - 202 may inspect their results or invoke their documented mechanisms, but it must not duplicate their responsibilities.

---

# 17. Acceptance Criteria

Database Maintenance is compliant when it can:

* create and verify database backups;
* perform structural integrity checks;
* manage deliberately retained archived identities;
* optimize the database safely;
* rebuild the database when required;
* preserve SHA512 identity across rebuilds;
* treat `file_id` as a technical database-instance identifier;
* integrate with Review Queue for ambiguous maintenance decisions;
* require explicit user control for destructive operations;
* produce auditable logs;
* operate on multi-million-file datasets without requiring the entire collection in memory.

---

# End of DOC - 202
