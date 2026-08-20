# DOC-206 – Import / Export / Recovery Utility

**Project:** AI Image Collection Management System

**Document:** DOC-206

**Version:** 1.0

**Status:** Design Specification

---

## 1. Purpose

Import / Export / Recovery Utility is a project-administration tool for creating portable backups of the project's persistent state and restoring that state when required.

Its purpose is to provide a controlled way to:

* export project database state;
* export Collection Definition;
* export application/module configuration;
* create a consistent recovery package;
* validate a package before restore;
* restore a project to a known previous state;
* migrate the project configuration and database to another installation where supported.

This utility does not perform normal database maintenance, optimization, repair or retention cleanup. Those responsibilities belong to DOC-202 and the database-specific implementation.

---

## 2. Scope

A recovery package may contain three logically separate components:

```text
PROJECT DATABASE
COLLECTION DEFINITION
APPLICATION CONFIGURATION
```

The package may also contain metadata required to identify the package itself, such as:

```text
package format version
creation timestamp
application version
database schema version
Collection Definition format version
configuration format version
checksums
source environment information
```

The package does not need to contain image binaries by default.

Image files remain in the configured filesystem trees and are restored by their own storage/backup mechanisms if the user requires a complete physical backup.

---

## 3. Separation of Responsibilities

DOC-206 is responsible for **export, import and recovery orchestration for project state**.

It is not responsible for:

* routine database cleanup;
* database index optimization;
* database compaction;
* deleting old database records according to retention policy;
* repairing arbitrary database corruption without a valid recovery source;
* scanning the filesystem for missing files;
* recalculating SHA512 values for the entire collection;
* rebuilding analysis results;
* moving collection files as part of ordinary restore.

These operations belong to other components and specifications.

---

## 4. Recovery Package

The preferred unit of backup and restore is a single **Recovery Package**.

A Recovery Package logically contains:

```text
manifest
project database backup
Collection Definition
application configuration
integrity metadata
```

The physical container format is an implementation decision. A ZIP-like archive is a suitable example, but the logical specification must remain independent from a specific archive library.

---

## 5. Manifest

Every Recovery Package shall contain a manifest describing its contents.

At minimum the manifest should identify:

```text
package_id
package_format_version
created_at
application_version
database_schema_version
collection_definition_version
configuration_version
included_components
integrity information
```

The manifest must be readable before a restore is attempted.

A package with an invalid or missing manifest must not be restored automatically.

---

## 6. Database Export

The database component contains persistent project state required for recovery.

Depending on the database implementation, this may be represented as:

```text
native database backup
logical database dump
portable database file
```

The selected method must preserve the logical data required by DOC-005.

The export must include, where applicable:

* file identity records;
* physical file locations;
* analysis results;
* classification results;
* module definitions and execution history where retained;
* file events/history;
* Review Queue data;
* manual decisions and protected corrections;
* duplicate information;
* Set information and other persistent project metadata.

The export must not silently omit data required to restore the project to a functionally equivalent state.

---

## 7. Collection Definition Export

The Collection Definition is exported as a separate logical component even when it is also represented in the database.

This makes the recovery package independently understandable and allows validation before database restore.

The exported definition follows DOC-302.

It may contain:

```text
roots
roles
paths
access policies
traversal rules
Collection nodes
Classification Boundaries
version information
```

The exported definition must not contain image-analysis results.

---

## 8. Configuration Export

Application and module configuration is exported according to DOC-008.

Examples include:

```text
module settings
confidence thresholds
worker limits
logging settings
application preferences
database connection/storage settings
```

Collection Definition properties must not be duplicated into ordinary configuration merely for convenience when DOC-302 is the authoritative source.

Sensitive configuration values shall be handled according to the security rules of the configuration system.

---

## 9. Physical Image Files

By default, DOC-206 backs up project **state**, not the physical image collection itself.

The package therefore does not normally contain:

```text
5,000,000 image files
```

This keeps project-state backup manageable and avoids duplicating the user's primary image backup system.

A future implementation may offer an optional physical-file backup mode, but that is outside the mandatory DOC-206 scope.

A successful project-state restore does not imply that every physical image file is present on disk.

---

## 10. Export Modes

The utility should support at least:

### Full Project Export

Includes database, Collection Definition and configuration.

### Database-Only Export

Exports the project database without application configuration and Collection Definition.

### Configuration Export

Exports configuration and Collection Definition without the project database.

### Recovery Package

Creates the preferred complete project-state package containing all required components.

The exact availability of these modes may depend on implementation maturity.

---

## 11. Consistency at Export Time

A Recovery Package must represent a coherent project state.

The utility should establish a consistent export boundary before copying the individual components.

At minimum:

```text
read current configuration
read current Collection Definition
create consistent database backup
record versions
calculate package integrity information
```

The utility should avoid creating a package where the database belongs to one configuration version and the exported Collection Definition belongs to another without explicitly recording that difference.

Running modules should not be silently corrupted by an export operation.

Where the database engine requires a native consistent-backup mechanism, the implementation should use that mechanism rather than copying live database files unsafely.

---

## 12. Package Integrity

The utility shall verify the integrity of exported package components.

The package should include checksums for relevant files, for example:

```text
manifest
 database backup
Collection Definition
configuration
```

SHA512 may be used for package-component integrity verification.

This use of SHA512 concerns package integrity and does not replace the file identity model of DOC-012.

---

## 13. Import Validation

Import must validate the complete package before altering the active project state.

Validation should include:

* package format compatibility;
* manifest validity;
* component checksums;
* database schema compatibility;
* Collection Definition format compatibility;
* configuration compatibility;
* required components are present;
* obvious path/configuration conflicts are reported.

A failed validation must not partially replace the active project.

---

## 14. Dry Run Restore

Before an actual restore, the utility should provide a validation or dry-run mode.

The dry run may report:

```text
package valid
schema compatible
configuration compatible
Collection Definition compatible
path conflicts detected
missing referenced roots
```

A dry run must not modify the active database or configuration.

---

## 15. Restore Modes

The utility should support two conceptual restore modes.

### Full Restore

Replace the current project state with the state represented by the Recovery Package.

### Selective Restore

Restore one or more selected components, for example:

```text
Database
Collection Definition
Configuration
```

Selective restore must clearly warn that the selected components may no longer match the remaining current state.

A selective restore should therefore require explicit user confirmation.

---

## 16. Restore Safety

The utility must not overwrite the active state blindly.

Before modifying the active project it should:

1. validate the package;
2. show the restore scope;
3. identify incompatible versions or conflicts;
4. create a safety backup of the current state where practical;
5. request explicit user confirmation;
6. perform the restore;
7. verify the restored state.

If restore fails part-way through, the utility should provide a controlled recovery path rather than leaving the system in an undocumented mixed state.

---

## 17. Database and Collection Definition Relationship

The database and Collection Definition are related but not interchangeable.

The database contains operational and historical project state.

Collection Definition describes the configured collection structure.

A recovery package contains both because restoring one without the other may produce an inconsistent project.

Example:

```text
Database:
    file classifications refer to a configured destination

Collection Definition:
    destination path and structure
```

Both are required for a complete project-state recovery.

---

## 18. Paths and Machine Migration

A Recovery Package may be restored on another computer or another storage layout.

Absolute paths therefore require special handling.

The utility should detect when an imported path no longer exists and allow the user to map configured roots to new physical locations.

Example:

```text
Source machine:
D:\Collection

Target machine:
E:\Images
```

The user may explicitly map:

```text
D:\Collection  →  E:\Images
```

The restore process must not silently substitute unrelated paths.

After path remapping, the Collection Definition remains the authoritative logical structure.

---

## 19. File Identity During Restore

Restore must preserve SHA512-based file identity stored in the database.

The utility must not generate a new identity merely because a physical root path changes.

Example:

```text
Old path:
D:\Collection\Anime\image.jpg

New path:
E:\Images\Anime\image.jpg

SHA512:
unchanged
```

The path is different, but the file identity remains the same.

If the physical file is absent on the target system, the database may restore its record while the file remains missing according to the normal file lifecycle rules.

The recovery utility does not fabricate image binaries.

---

## 20. Restore and Duplicate Files

Where multiple physical locations for the same SHA512 are represented in the database, the restore operation must preserve those relationships as database state.

The recovery utility must not interpret matching SHA512 values as independent binary identities merely because they appear in different folders.

Physical files themselves are not recreated by the metadata restore unless an explicit physical-file backup mechanism is used.

---

## 21. Review Queue and Manual Decisions

A full project restore must preserve Review Queue history and user decisions stored in the database.

A restore must not silently convert:

```text
manual correction
```

into:

```text
automatic result
```

Protected user decisions must remain distinguishable after restore.

---

## 22. Analysis Results

Analysis results are restored as database state.

The utility does not automatically recalculate them during restore.

If the user later decides that results are outdated because a module/model changed, the user follows DOC-014 and DOC-205 to clear and recalculate the selected module's results.

Restore therefore preserves the project state at the point of backup rather than implicitly initiating reprocessing.

---

## 23. Version Compatibility

The utility must distinguish at least:

```text
package format version
database schema version
Collection Definition format version
configuration format/version
```

A compatible package may be migrated to a newer supported version.

An incompatible package must not be restored as though it were compatible.

Version migration must be explicit and must preserve a safe fallback whenever practical.

---

## 24. Backup Retention

DOC-206 defines how a backup is created and restored.

It does not define long-term retention policy for old backups.

Retention, rotation and cleanup of backup files may be configured elsewhere or performed by the user's existing backup infrastructure.

This prevents DOC-206 from duplicating the maintenance responsibilities of DOC-202.

---

## 25. Logging

Each export, import, validation and restore execution shall be logged.

The execution summary should include:

```text
operation type
package id
start time
finish time
source/target environment
components included
components restored
validation results
warnings
errors
final status
```

Sensitive configuration contents must not be written to ordinary logs.

---

## 26. Safety Principles

DOC-206 follows these rules:

1. Project-state backup and restore is separate from routine database maintenance.
2. A Recovery Package should contain database, Collection Definition and configuration for complete project-state recovery.
3. Physical image files are not included by default.
4. Packages are validated before restore.
5. Failed validation must not partially replace the active state.
6. Full restore requires explicit user confirmation.
7. A safety backup of the current state should be created before destructive replacement where practical.
8. SHA512 file identity is preserved during path remapping.
9. Restore does not automatically recalculate analysis results.
10. Review Queue and manual decisions remain preserved.
11. Selective restore must clearly warn about possible component inconsistency.
12. Normal operation remains offline.

---

## 27. Acceptance Criteria

DOC-206 is compliant when the utility can:

* create a complete project-state Recovery Package;
* export the database;
* export Collection Definition;
* export application/module configuration;
* validate package integrity;
* perform a dry-run restore;
* restore the project after explicit confirmation;
* preserve SHA512-based file identity;
* detect and handle root-path changes during migration;
* preserve Review Queue and manual-decision state;
* restore analysis results without automatically reprocessing them;
* distinguish compatible and incompatible package versions;
* avoid mixing ordinary database maintenance responsibilities into the recovery workflow;
* operate without Internet access.

---

# End of DOC-206
