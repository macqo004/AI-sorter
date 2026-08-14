# DOC-008
# Configuration Manager

**Project:** AI Image Collection Management System  
**Document:** DOC-008  
**Version:** 2.0  
**Status:** Design Specification

**Related:** DOC-003, DOC-005, DOC-007, DOC-010, DOC-301, DOC-302

---

# 1. Purpose

Configuration Manager provides a central source of user-configurable application and module settings.

Its primary purpose is to prevent modules from depending on hard-coded values or maintaining unrelated configuration files.

Configuration Manager stores configuration. It does not replace the project database and does not own image metadata, analysis results or user classification decisions.

---

# 2. Architectural Principle

Configuration Manager is shared infrastructure.

Modules obtain their configuration from the common configuration system rather than embedding project-specific values in their implementation.

In particular, modules must not hard-code concepts such as:

```text
TODO
AI
FINAL
Anime
Themes
```

or assume fixed filesystem paths.

Physical collection structure is defined by Collection Definition and is governed by DOC-301 and DOC-302.

Configuration Manager may provide access to that configuration, but must not redefine it.

---

# 3. Configuration vs Operational Data

The project distinguishes between configuration and operational data.

### Configuration

Examples:

* module settings;
* confidence thresholds;
* worker/thread limits;
* enabled/disabled options;
* logging preferences;
* UI preferences;
* database connection/storage settings;
* application paths;
* processing limits.

### Operational data

Examples:

* files;
* SHA512 values;
* image metadata;
* analysis results;
* classifications;
* Review Queue entries;
* file history;
* collection runtime state.

Operational data belongs to the project database and is not duplicated into Configuration Manager merely for convenience.

---

# 4. Responsibilities

Configuration Manager is responsible for:

* loading configuration;
* validating configuration;
* exposing configuration values to modules;
* saving configuration changes;
* applying defaults;
* importing and exporting configuration where supported;
* detecting invalid or incompatible configuration;
* providing a consistent configuration view to running modules.

Configuration Manager is not responsible for executing modules.

---

# 5. Configuration Scope

Configuration may exist at several logical levels.

### Application-level

Settings affecting the application as a whole.

### Module-level

Settings belonging to one module.

### Collection-level

Settings associated with a configured collection where appropriate.

The actual collection definition itself is not owned by Configuration Manager. It is defined by DOC-302.

### User-interface level

Settings affecting presentation and user preferences.

The system should avoid duplicating the same value at several levels unless a defined override mechanism exists.

---

# 6. Application Configuration

Possible application-level settings include:

* application language;
* temporary/work directory;
* default log location;
* default export location;
* global resource limits;
* application behaviour options.

These are examples, not a fixed mandatory list.

---

# 7. Module Configuration

Each module may define settings required for its operation.

Examples:

### Scanner

```text
worker/thread limit
supported extensions
scan behaviour
```

### Universe Analysis

```text
confidence threshold
model selection
processing limits
```

### Character Analysis

```text
confidence threshold
model selection
```

### Theme Analysis

```text
confidence threshold
```

### File Renamer

```text
enabled rule sets
collision behaviour
review behaviour
```

Configuration Manager stores and validates these values but does not interpret their module-specific meaning.

The module specification remains authoritative for the semantics of its settings.

---

# 8. Collection Configuration

Collection configuration is defined by:

```text
DOC-301 – Collection Definition Wizard
DOC-302 – Collection Definition Format
```

A collection may contain user-defined roots and associated properties such as:

```text
path
role
recursive
enabled
access policy
```

Configuration Manager must not introduce a second, competing definition of these properties.

For example, it must not separately store:

```text
AI path = X
FINAL path = Y
```

when those values are already part of the Collection Definition.

Instead, modules obtain the authoritative collection definition through the project's configuration/database architecture.

---

# 9. Directory Access Policy

Directory Access Policy is a collection/root-level architectural concept.

Proposed values include:

```text
PROTECTED
READ_ONLY
MODIFY
PLAYGROUND
```

The formal definition belongs to the dedicated Directory Access Policy specification.

Configuration Manager may store or expose the configured value, but must not redefine its semantics.

Modules must respect the policy applicable to the root they are operating on.

---

# 10. Validation

Configuration must be validated before it becomes active.

Validation may include:

* numeric range checks;
* enum/value checks;
* incompatible-option checks;
* existence or accessibility checks for paths where appropriate;
* duplicate configuration detection;
* module compatibility checks;
* configuration version compatibility.

A configuration error must produce an understandable diagnostic.

Invalid configuration must not silently become active.

A path that does not currently exist is not necessarily an invalid configuration. Some configured directories may intentionally be created later by the system.

---

# 11. Defaults

Every configurable option should define a default where a meaningful default exists.

Defaults must not silently override explicit user configuration.

If an option has no safe universal default, the system should require explicit configuration instead of inventing one.

---

# 12. Configuration Versioning

Configuration should contain a format/schema version.

When configuration structure changes, the Configuration Manager may migrate older configuration to the current format.

A failed migration must not silently destroy the previous configuration.

Backward compatibility should be maintained where practical.

---

# 13. Module Registration

Modules may register their configuration definitions with Configuration Manager.

A registration should identify at least:

```text
module identifier
configuration keys
value types
allowed ranges/values where applicable
default values where applicable
```

Configuration Manager does not need to understand the internal implementation of a module.

This permits new modules to introduce configuration without redesigning the entire configuration subsystem.

---

# 14. Runtime Configuration

A module should obtain a consistent configuration snapshot for an execution.

A configuration change made while a long-running module is executing should not cause unpredictable changes halfway through an operation unless the module explicitly supports dynamic configuration.

The preferred default behaviour is:

```text
load/validate configuration
        ↓
start execution
        ↓
use stable configuration snapshot
        ↓
finish execution
```

---

# 15. Configuration Changes

Configuration changes are user-controlled unless a future specification explicitly defines another mechanism.

A change should be validated before becoming active.

Where a change affects a running module, the new value normally applies to the next execution rather than silently changing the current execution.

---

# 16. Import and Export

Configuration should support, where practical:

* export;
* import;
* backup;
* restore.

Exported configuration should contain configuration data rather than transient operational data.

Import must validate the complete configuration before replacing the active configuration.

A failed import must leave the previous valid configuration intact.

---

# 17. Storage

The physical configuration-storage format is an implementation decision.

Possible approaches include:

```text
JSON
SQLite
XML
YAML
```

The chosen mechanism must provide reliable persistence and must not require Internet connectivity.

The logical configuration model must remain independent from the storage format.

---

# 18. Separation from Database

Configuration Manager and the project database have different responsibilities.

```text
Configuration Manager
    ↓
settings controlling how the application/modules operate

Project Database
    ↓
files, SHA512, metadata, analysis, classifications, history, review data
```

The database may contain configuration-related entities where required by the architecture, but Configuration Manager remains the logical owner of application configuration.

The same setting must not have two competing sources of truth.

---

# 19. Security

Configuration may contain sensitive information depending on future modules.

Sensitive values must not be written to ordinary logs in plaintext.

If credentials or other secrets are ever required, their storage must use an appropriate protected mechanism rather than relying on ordinary readable configuration text alone.

---

# 20. Failure Handling

Configuration Manager must fail safely.

Examples:

```text
invalid configuration
missing configuration file
corrupted configuration
unsupported configuration version
failed import
```

The system should preserve the last known valid configuration where possible.

Configuration failure must produce an understandable diagnostic and must not silently fall back to unsafe values.

---

# 21. Relationship with Module Execution

DOC-007 defines module execution.

Before execution, a module should obtain a validated configuration snapshot.

Configuration Manager does not decide whether a module should run. Execution remains under the rules defined by DOC-007 and the individual module specification.

---

# 22. Relationship with Module Interface

DOC-010 defines the module interface.

Configuration access should be available to modules through the common application infrastructure rather than through undocumented module-specific configuration files.

The module interface should expose configuration access only to the extent necessary for module operation.

---

# 23. Offline Operation

Configuration Manager must support normal operation without Internet connectivity.

No configuration operation may require an online service unless a future optional integration explicitly introduces such a dependency.

---

# 24. Acceptance Criteria

Configuration Manager is architecturally acceptable when:

* modules can obtain configuration from a common source;
* modules do not require hard-coded project paths or folder names;
* collection definitions are not duplicated outside DOC-301/DOC-302;
* module-specific settings remain owned by the relevant module specifications;
* configuration is validated before becoming active;
* safe defaults exist where appropriate;
* configuration format changes can be versioned or migrated;
* import/export can be performed safely;
* invalid imports do not destroy the previous valid configuration;
* running modules can use a stable configuration snapshot;
* operational image data remains in the project database;
* normal configuration operation does not require Internet access.

---

# End of DOC-008
