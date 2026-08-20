# DOC - 008 – Configuration Manager

**Project:** AI Image Collection Management System  
**Document:** DOC - 008  
**Version:** 3.0  
**Status:** Design Specification

**Related:** DOC - 003, DOC - 005, DOC - 007, DOC - 010, DOC - 301, DOC - 302, DOC - 303

---

# 1. Purpose

Configuration Manager provides a common source for user-configurable application and module settings.

Its purpose is to prevent modules from depending on hard-coded project paths, folder names or settings.

Configuration Manager stores configuration. It does not own File identity, FileLocation state, analysis results or user decisions.

---

# 2. Architectural Principle

Modules obtain project-specific configuration through the common configuration system.

Modules must not hard-code physical names such as:

```text
TODO
AI
FINAL
Anime
Themes
```

or assume fixed paths.

Collection structure is defined by DOC - 301 / DOC - 302 and administered by DOC - 303.

Configuration Manager exposes the active validated configuration; it does not redefine Collection Definition.

---

# 3. Configuration versus Operational Data

### Configuration

Examples include:

* module settings;
* confidence thresholds;
* worker/thread limits;
* enabled/disabled options;
* logging preferences;
* UI preferences;
* processing limits;
* application paths;
* Collection Definition data.

### Operational Data

Examples include:

* Files;
* FileLocations;
* SHA512 values;
* image metadata;
* analysis results;
* classifications;
* Review Queue entries;
* history;
* ModuleExecutions.

Operational data belongs to the project database and is not duplicated into Configuration Manager merely for convenience.

---

# 4. Responsibilities

Configuration Manager is responsible for:

* loading configuration;
* validating configuration;
* exposing validated configuration to modules;
* saving configuration changes;
* applying safe defaults;
* importing/exporting configuration where supported;
* detecting invalid or incompatible configuration;
* providing a stable configuration snapshot to an execution.

Configuration Manager does not execute modules or orchestrate their order.

---

# 5. Configuration Scope

Configuration may exist at:

```text
Application level
Module level
Collection level
User-interface level
```

Each setting must have one logical source of truth.

---

# 6. Module Configuration

A module owns the semantics of its own settings.

Examples include:

```text
Scanner
    worker count
    supported extensions
    hash retry policy

Universe Analysis
    confidence thresholds
    model/resource selection
    AI workspace population threshold

Character Analysis
    candidate/assignment thresholds

AutoSort
    execution mode
    placement rules

File Renamer
    rule enablement and order
```

Configuration Manager validates types/ranges and persists the values but does not redefine their module-specific meaning.

---

# 7. Collection Definition

Collection Definition is defined by:

```text
DOC - 301 → Wizard/user editing workflow
DOC - 302 → formal data model and semantics
DOC - 303 → validation and administration
```

Configuration Manager may provide the active validated Collection Definition to modules.

It must not maintain a competing simplified model such as:

```text
AI path = X
FINAL path = Y
```

outside the authoritative Collection Definition.

---

# 8. Directory Access Policy

Directory Access Policy is defined by DOC - 302.

The current policy concepts are:

```text
PROTECTED
READ_ONLY
MODIFY
PLAYGROUND
```

Configuration Manager may store/expose the configured policy but does not define its operational meaning.

Modules must enforce the policy during their filesystem operations.

---

# 9. Validation

Configuration must be validated before activation.

Validation may include:

* type/range checks;
* enum/value checks;
* incompatible-option checks;
* Collection Definition validation through DOC - 303;
* path checks where appropriate;
* duplicate/conflicting setting detection;
* configuration-version compatibility.

An invalid configuration must not silently become active.

A path that does not currently exist is not necessarily invalid because some AI/workspace paths may intentionally be created later.

---

# 10. Defaults

Meaningful safe defaults should be provided where possible.

Explicit user configuration must not be silently overridden by defaults.

Where no safe universal default exists, explicit configuration should be required.

---

# 11. Configuration Versioning

Configuration data shall carry a format/schema version.

When the structure changes, Configuration Manager may migrate older configuration to the current format.

A failed migration must leave the previous valid configuration intact.

---

# 12. Runtime Configuration Snapshot

A module should obtain a stable validated configuration snapshot for each execution.

Preferred behaviour:

```text
load/validate
    ↓
start execution
    ↓
stable snapshot
    ↓
finish execution
```

A change made while a module is running normally applies to the next execution unless that module explicitly supports dynamic configuration.

---

# 13. Import and Export

Configuration should support safe import/export where practical.

Import must validate the complete configuration before replacing the active configuration.

A failed import must leave the previous valid configuration intact.

Collection Definition export/import is also defined by DOC - 302 and DOC - 206.

---

# 14. Storage

The physical storage format is an implementation decision.

Possible formats include JSON or SQLite-backed configuration.

The logical configuration model must remain independent from serialization details.

---

# 15. Separation from Database

The responsibilities are:

```text
Configuration Manager
    ↓
settings controlling operation

Project Database
    ↓
Files, FileLocations, SHA512, analysis, classifications,
Review Queue, execution state, history
```

Some configuration may be persisted in the database where required by the architecture, but each setting has one logical owner.

---

# 16. Security

Sensitive configuration values must not be written to normal logs in plaintext.

Future credentials/secrets require an appropriate protected mechanism.

---

# 17. Failure Handling

Configuration failure must be explicit and safe.

Examples:

```text
invalid configuration
corrupted configuration
unsupported format version
failed import
invalid Collection Definition
```

The last known valid configuration should be preserved where possible.

---

# 18. Relationship with Execution and Interface

DOC - 007 defines execution.

DOC - 010 defines the common module interface.

Configuration Manager supplies validated configuration snapshots but does not orchestrate execution.

---

# 19. Offline Operation

Configuration Manager must operate without Internet connectivity.

---

# 20. Acceptance Criteria

Configuration Manager is compliant when:

* modules obtain configuration from a common source;
* project paths and roles are not hard-coded;
* Collection Definition is not duplicated in competing stores;
* module-specific settings remain owned by their modules;
* configuration is validated before activation;
* running modules can use stable configuration snapshots;
* invalid imports do not destroy valid configuration;
* Access Policy semantics are taken from DOC - 302;
* normal operation does not require Internet access.

---

# End of DOC - 008
