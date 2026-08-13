DOC-007
Module Architecture

Project: AI Image Collection Management System

Document: DOC-007

Version: 1.0

Status: Approved

1. Purpose

This document defines the architectural principles shared by every module in the project.

It specifies how modules interact with the rest of the system and establishes the design rules that all current and future modules must follow.

2. Design Philosophy

The project is based on independent modules.

Each module performs one clearly defined task.

Modules never communicate directly with one another.

The database is the only shared communication layer.

3. Module Independence

Every module shall:

run independently;
be executable without starting other modules;
perform only its own task;
terminate after completing its work.

Modules are not permanently resident in memory.

4. User-Controlled Execution

Modules are started exclusively by the user.

The project contains:

no scheduler;
no automatic execution engine;
no workflow manager.

The user decides:

which module to run;
when to run it;
how often to run it.
5. Execution Order

Modules may be executed in any order.

Some modules naturally produce more useful results when previous modules have already populated the database.

Example:

Scanner

↓

Universe Analysis

↓

Character Analysis

However, the system never enforces this sequence.

6. Shared Database

Modules exchange information exclusively through the project database.

Modules never:

call other modules;
exchange files;
communicate through memory;
communicate through sockets.

All persistent information is stored in the database.

7. Reading Existing Data

Before performing work, a module should use existing database information whenever possible.

Example:

Scanner:

checks stored file metadata;
reuses existing SHA512 values when valid.

Universe Analysis:

reads image information already stored by Scanner.

Character Analysis:

reads Universe observations from the database.
8. Writing Results

Each module is responsible only for writing its own observations.

A module shall never overwrite data owned by another module unless explicitly designed to update its own previous results.

9. Repeated Execution

Modules may be executed repeatedly.

The system does not prevent repeated execution.

Whether a module should be executed again is entirely the user's decision.

10. Parallel Execution

The project assumes a single user operating the application.

Simultaneous execution protection is not required.

Future versions may introduce optional safeguards if necessary.

11. User Feedback

Every module should provide visible execution status.

Minimum requirements:

starting indication;
running indication;
completion indication;
error indication.

A progress bar is recommended when measurable progress is available.

Otherwise, an activity indicator (spinner) is sufficient.

The purpose is to assure the user that the module has started successfully.

12. Error Handling

Failure of one module must not prevent execution of any other module.

Modules are isolated.

Errors are logged.

Successfully completed work is preserved.

13. Extensibility

Adding a new module should require:

implementing the module itself;
registering its configuration;
defining its database fields if required.

Existing modules should not require modification.

14. Module Categories

Modules currently belong to three groups.

Infrastructure

Examples:

Scanner
Collection Definition Wizard
AutoSort
Analysis

Examples:

B&W
Screenshot
Meme
IRL
Universe
Character
Theme
Set Filter
Maintenance

Examples:

Collection Consistency Checker

Additional categories may be introduced in future versions.

15. Design Principles

Every module should:

perform one task only;
remain independent;
communicate only through the database;
be started manually by the user;
produce reproducible results;
log its activity;
avoid modifying data outside its responsibility.
16. Acceptance Criteria

The module architecture is considered correctly implemented when:

every module runs independently;
no module depends on another process being active;
all communication occurs through the database;
the user controls execution;
new modules can be added without redesigning the existing architecture.
End of DOC-007