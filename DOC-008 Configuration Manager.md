# DOC-008

# Configuration Manager

**Project:** AI Image Collection Management System

**Document:** DOC-008

**Version:** 1.0

**Status:** Design Specification

---

# 1. Purpose

Configuration Manager provides a central location for all user-configurable settings used by the project.

Its purpose is to eliminate hardcoded values from modules while allowing the user to customise the system without modifying source code.

Configuration Manager stores only application settings.

It never stores image metadata or analysis results.

---

# 2. Design Philosophy

Configuration is shared across the entire project.

Modules should read their configuration from Configuration Manager instead of maintaining separate configuration files whenever practical.

The goal is to provide one consistent source of settings.

---

# 3. Responsibilities

Configuration Manager is responsible for:

* loading configuration;
* validating configuration;
* saving configuration;
* providing configuration values to modules;
* restoring default values.

---

# 4. Configuration Categories

Configuration is divided into logical groups.

Examples:

General

Scanner

Analysis Modules

AutoSort

Collection Definition

Maintenance Modules

Database

Logging

User Interface

Future modules may introduce additional categories.

---

# 5. General Configuration

Examples:

* application language;
* default working directories;
* logging level;
* temporary directory;
* automatic backup options.

---

# 6. Scanner Configuration

Examples:

* maximum worker threads;
* supported file extensions;
* recursive scan options;
* SHA512 behaviour;
* logging verbosity.

---

# 7. Analysis Module Configuration

Each analysis module may expose its own settings.

Examples:

Universe Analysis

* confidence threshold

Character Analysis

* confidence threshold

Theme Analysis

* confidence threshold

Set Filter

* similarity threshold

B&W Analysis

* monochrome tolerance

The Configuration Manager does not interpret these values.

It only stores and provides them.

---

# 8. Collection Definition Configuration

Examples:

* Collection Tree locations;
* Classification Boundary options;
* update behaviour.

---

# 9. AutoSort Configuration

Examples:

* AI workspace location;
* directory creation behaviour;
* reporting options.

AutoSort configuration never contains FINAL paths generated automatically.

Those are provided by Collection Definition.

---

# 10. Maintenance Configuration

Examples:

Collection Consistency Checker

* migration confidence thresholds;
* report output directory;
* export format;
* CSV delimiter.

---

# 11. Database Configuration

Examples:

* database location;
* connection parameters;
* backup settings;
* cache behaviour.

Sensitive information should be protected appropriately.

---

# 12. Logging Configuration

Examples:

* log directory;
* maximum log size;
* log retention period;
* verbosity level.

---

# 13. User Interface Configuration

Examples:

* theme;
* language;
* window layout;
* progress display;
* default export locations.

---

# 14. Configuration Storage

The physical storage format is intentionally unspecified.

Possible implementations include:

* JSON
* SQLite
* XML
* YAML

The storage mechanism may change without affecting module behaviour.

---

# 15. Validation

Configuration Manager validates configuration before it becomes active.

Examples:

* missing directories;
* invalid numeric ranges;
* duplicate Collection Trees;
* unsupported values.

Invalid configuration should never crash the application.

---

# 16. Default Values

Every configurable option shall define a default value.

The system must remain usable immediately after installation.

---

# 17. Import and Export

Configuration should support:

* export;
* import;
* backup;
* restore.

This allows migration between installations.

---

# 18. Module Registration

Each module registers its configurable parameters with Configuration Manager.

Configuration Manager itself does not require knowledge of module internals.

This allows future modules to be added without redesigning the configuration system.

---

# 19. Separation of Responsibilities

Configuration Manager stores:

* application settings;
* module settings;
* user preferences.

Configuration Manager does **not** store:

* image metadata;
* analysis observations;
* Collection Definition;
* migration suggestions;
* SHA512 values;
* image tags.

Those belong to the project database.

---

# 20. Design Principles

Configuration Manager:

* provides one central configuration source;
* remains independent of analysis modules;
* validates user input;
* supports future expansion;
* separates configuration from operational data.

---

# 21. Acceptance Criteria

Configuration Manager is considered complete when:

* modules obtain configuration from a common source;
* configuration can be validated;
* default values exist for every option;
* configuration can be exported and imported;
* operational image data remains stored exclusively in the project database.

---

# End of DOC-008
