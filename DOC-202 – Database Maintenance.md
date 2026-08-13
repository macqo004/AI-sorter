# DOC-202 – Database Maintenance

## 1. Purpose

This document defines the rules and procedures for maintaining the project database.

The Database Maintenance module is responsible for:

* creating database backups;
* optimizing database storage;
* checking database integrity;
* managing archived records;
* rebuilding the database when required;
* verifying consistency between database records and the file collection.

The module is designed to preserve long-term reliability of the project database while ensuring that all potentially destructive operations remain under user control.

---

# 2. Maintenance Philosophy

The project database is an index of the image collection.

The database stores:

* file identity information;
* file locations;
* metadata;
* analysis results;
* processing history.

The original image files remain the primary source of binary data.

Database Maintenance shall never assume that the database is the only source of truth.

All maintenance operations shall follow these principles:

* no destructive operation shall run automatically;
* the user must explicitly start maintenance actions;
* the user must approve operations that may remove or modify stored data;
* every maintenance operation shall be logged according to DOC-011.

---

# 3. Database Backup

## 3.1 Purpose

Database Backup creates a recoverable copy of the current database state.

Backup is intended before:

* database rebuild;
* large cleanup operations;
* schema changes;
* manual maintenance.

---

## 3.2 Operation

The user manually starts the backup operation.

The module shall:

* create a backup file;
* verify that the backup was completed successfully;
* store backup information in the log.

Example:

```
Database Maintenance

Backup completed successfully.

Database size:
12.4 GB

Backup file:
backup_2026-07-22.db
```

---

# 4. Database Optimization

## 4.1 Purpose

Database Optimization improves database efficiency after large amounts of changes.

It may be useful after:

* deleting archived records;
* importing large amounts of data;
* extensive updates;
* rebuilding indexes.

---

## 4.2 Operation

Optimization may include:

* reclaiming unused database space;
* rebuilding indexes;
* compacting database storage;
* executing database-specific optimization commands.

Optimization does not modify image files and does not change analysis results.

---

## 4.3 User Control

Optimization is always started manually.

The module may suggest optimization when appropriate, but shall never execute it automatically.

Example:

```
Database Maintenance

Large amount of archived records was removed.

Database optimization is recommended.

Run optimization now?
```

---

# 5. Database Integrity Check

## 5.1 Purpose

Integrity Check verifies whether the database structure and stored relations are consistent.

The check shall identify problems such as:

* missing required fields;
* invalid file references;
* duplicated file_id values;
* invalid SHA512 records;
* analysis records without associated files;
* files marked ACTIVE but missing from storage.

---

## 5.2 Result

Integrity Check shall generate a readable report.

Example:

```
Database Integrity Check

Found problems:

1.
File record 58231 has no SHA512 value.

2.
Record 81222 references a missing file.

3.
Character analysis exists without a valid file record.

Recommended action:
Review the report before performing repairs.
```

---

## 5.3 Automatic Repair

Integrity Check shall not automatically repair database problems unless a future module explicitly defines safe repair rules.

The default behaviour is:

* detect;
* report;
* suggest action.

---

# 6. Archived Record Management

## 6.1 Purpose

Archived records represent files that were previously known but are no longer present in supported directories.

According to DOC-012:

* changing SHA512 creates a new file record;
* archived records will not become active again automatically.

---

## 6.2 Removal of Archived Records

Archived records may be permanently removed by the user.

The module shall:

* display the number of records to remove;
* require confirmation;
* recommend creating a backup before deletion.

Example:

```
Database Maintenance

Archived records found:
845321

Removing these records cannot be undone.

Create backup before continuing?
```

---

## 6.3 Automatic Cleanup

Archived records shall never be removed automatically.

Possible future automatic cleanup features must require explicit user configuration.

---

# 7. Database Rebuild

## 7.1 Purpose

Database Rebuild is a complete database reconstruction procedure.

It is intended for situations where:

* database corruption is detected;
* integrity checks fail beyond safe repair;
* database structure becomes unreliable.

---

## 7.2 Rebuild Principle

Database Rebuild does not attempt to repair the existing database.

Instead, it creates a new database based on the current file collection.

Process:

1. Create backup of the current database.
2. Remove or archive the existing database.
3. Create a new empty database structure.
4. Load current configuration.
5. Run Scanner on configured directories.
6. Recreate file records using SHA512 values.

---

## 7.3 Result

After rebuild:

* ACTIVE records are recreated;
* missing files are not restored;
* archived records are not recreated unless files exist again;
* file_id values may change.

Example:

Before:

```
file_id = 15231
SHA512 = AAAA
path = AI/Games/Genshin/Furina.jpg
```

After rebuild:

```
file_id = 1
SHA512 = AAAA
path = AI/Games/Genshin/Furina.jpg
```

SHA512 identity remains unchanged, but internal database identifiers may be regenerated.

---

# 8. Analysis Data After Rebuild

Database Rebuild restores the file database.

Analysis results may require separate processing.

After rebuild:

* Scanner recreates file records;
* analysis modules may be executed again;
* previous analysis results are not guaranteed to exist.

Future implementations may provide export/import of analysis results.

---

# 9. Collection Relationship Verification

Database Maintenance may verify relationships between database records and stored files.

Examples:

Database contains:

```
file_id = 123
path = AI/Genshin/Furina.jpg
```

but file does not exist.

Or:

File exists:

```
AI/Genshin/Furina.jpg
```

but no database record exists.

Such cases shall be reported for user review.

---

# 10. User Confirmation Requirements

The following operations require explicit user action:

| Operation               | Automatic execution |
| ----------------------- | ------------------- |
| Backup                  | No                  |
| Optimization            | No                  |
| Integrity Check         | No                  |
| Remove Archived Records | No                  |
| Database Rebuild        | No                  |

The module may suggest actions but shall never perform them without confirmation.

---

# 11. Logging

All Database Maintenance operations shall follow DOC-011 – Logging Standard.

Logs shall include:

* operation performed;
* start and completion time;
* result;
* number of affected records;
* encountered errors;
* suggested user actions.

---

# 12. Safety Principles

Database Maintenance is designed around the principle:

> Maintenance operations should preserve data integrity, not hide problems.

The module shall prefer:

* detection over automatic correction;
* reports over silent changes;
* user decisions over hidden actions.

All destructive operations require explicit user approval.
