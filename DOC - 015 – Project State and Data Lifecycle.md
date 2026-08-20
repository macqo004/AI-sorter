# DOC-015 – Project State and Data Lifecycle

**Project:** AI Image Collection Management System  
**Document:** DOC-015  
**Version:** 1.0  
**Status:** Design Specification

**Related:** DOC-005, DOC-007, DOC-008, DOC-012, DOC-013, DOC-014, DOC-301, DOC-302

---

# 1. Purpose

This document defines how the project distinguishes persistent project state, configuration, derived module results, user decisions, and historical information.

Its purpose is to establish clear ownership and lifecycle rules so that the application knows:

* which information is authoritative;
* which information can be regenerated;
* which information may be cleared and recalculated;
* which information must survive module cleanup;
* which information belongs to configuration rather than the database;
* which information represents an explicit user decision.

This document does not define the detailed SQL schema. The logical database representation belongs to **DOC-005**. Application configuration belongs to **DOC-008**. Module result cleanup is governed by **DOC-014**.

---

# 2. Project State Layers

The project separates information into the following logical layers:

```text
CONFIGURATION
    ↓
COLLECTION DEFINITION
    ↓
FILE IDENTITY / CURRENT FILE STATE
    ↓
MODULE RESULTS
    ↓
USER DECISIONS
    ↓
HISTORY / EVENTS
```

These layers are related but are not interchangeable.

A derived analysis result must not become the authority for configuration simply because it has high confidence.

A physical directory must not become an approved FINAL destination merely because it exists on disk.

A previous automatic result must not override an explicit user decision.

---

# 3. Authoritative Sources

The project uses different authoritative sources for different kinds of information.

| Information | Authoritative source |
|---|---|
| Application/module configuration | DOC-008 configuration system |
| Approved collection structure | Collection Definition from DOC-301/DOC-302 |
| Binary file identity | SHA512 according to DOC-012 |
| Current database file state | Project database |
| Analysis result | Result produced by the responsible module |
| User review decision | Review Queue / user decision state from DOC-013 |
| Historical event | Event/history records |

No single source is authoritative for every kind of project state.

---

# 4. Configuration

Configuration controls how the application and modules operate.

Examples include:

```text
module settings
confidence thresholds
worker limits
logging settings
paths and general application options
```

Configuration is not an analysis result and must not be cleared as part of Module Result Cleanup.

Configuration storage and migration are defined by DOC-008.

---

# 5. Collection Definition

Collection Definition describes the configured directory environment in which files are processed and organised.

It includes concepts such as:

```text
configured roots
root roles
primary trees
Theme fallback
AI and TODO roots
traversal rules
Classification Boundaries
access policies
logical collection nodes
```

Collection Definition is configuration/state describing the collection environment.

It does not contain per-file analysis results.

It is not recreated merely because an analysis module is rerun.

Its creation and modification are governed by DOC-301 and DOC-302.

---

# 6. File Identity

File identity is based on SHA512 as defined by DOC-012.

A file's identity is independent from:

```text
filename
extension
physical path
collection placement
analysis result
```

Moving or renaming a file does not change its identity when the binary content remains unchanged.

If the binary content changes and therefore the SHA512 changes, the resulting content has a different identity.

The project should not normally design around two different binary contents producing the same SHA512. Such an event is treated as an integrity problem rather than an ordinary duplicate lifecycle event.

---

# 7. Multiple Physical Instances

Multiple physical locations may contain the same binary content.

For example:

```text
D:\Collection\Anime\...\image.jpg
E:\Backup\image.jpg
```

may reference the same SHA512 identity.

In such a case the database may retain separate physical-location records while treating the SHA512 as the common logical identity.

This supports Duplicate Management without inventing multiple logical file identities for the same content.

---

# 8. Current State vs Derived State

The project distinguishes between facts about the current file and information derived by analysis.

### Current file state

Examples:

```text
current location
filename
size
modified time
last seen state
file lifecycle state
```

### Derived analysis state

Examples:

```text
monochrome = true
IRL = false
Universe = Genshin Impact
Character = Furina
Theme = Bikini
Set = 001
```

Derived state may be recalculated.

Current file identity must not be replaced by an analysis result.

---

# 9. Module Results

Each module maintains its own result state.

For example:

```text
IRL           = processed
Screenshot    = processed
Universe      = not processed
Character     = processed
Set Detection = processed
```

Such a mixed state is valid.

Module results are derived data. Their storage and lifecycle are defined by DOC-005 and DOC-014 together with the individual module specifications.

Modules do not share ownership of one another's results.

---

# 10. Module Result Versioning Policy

The project does not require every result record to retain a separate generation of the model or algorithm that produced it.

Changing a model, algorithm, threshold system, or module implementation does not automatically invalidate all existing results.

When the user wants a complete recalculation using a new implementation, the user explicitly clears the relevant module's results and reruns that module according to DOC-014.

This is a deliberate design choice.

The project prefers:

```text
one current result set per module
+
explicit user-controlled cleanup
+
optional historical execution/event records
```

rather than storing many generations of results for normal operation.

---

# 11. User Decisions

User decisions are stronger than ordinary automatic observations for the decision context to which they apply.

Examples include:

```text
manual Universe correction
manual Character correction
manual destination selection
manual rejection of an automatic placement
```

A later automatic module execution may produce a new observation, but must not silently replace a protected user decision.

The detailed workflow is defined by DOC-013.

---

# 12. Manual Decision vs Current Location

A user's explicit placement decision is a statement about the accepted destination.

Once the authorised workflow applies that decision successfully:

```text
current location = user's chosen location
```

The system must not treat the new location as suspicious solely because it differs from a previous automatic suggestion.

A later materially different analysis may create a new review context, but it must not silently undo the previous decision.

---

# 13. Review Queue State

Review Queue cases are operational decision state, not ordinary module results.

A review case may reference:

```text
file identity
current path
analysis evidence
suggested result
user decision
status
```

A module result cleanup operation must not automatically erase unrelated resolved or protected user decisions.

Review Queue lifecycle is defined by DOC-013.

---

# 14. Historical Information

Historical events exist to explain what happened without redefining the current state.

Examples include:

```text
file scanned
file moved
file renamed
analysis completed
user corrected classification
review resolved
module results cleared
```

Historical events should not be silently rewritten to make old operations appear to have been different operations.

History is useful for diagnostics, auditing, recovery and future maintenance.

---

# 15. Rebuildable vs Non-Rebuildable State

The project should distinguish information that can safely be regenerated from information that is authoritative and must be preserved.

### Normally rebuildable or recalculable

```text
analysis results
module-derived classifications
set detection results
other derived observations
```

subject to user decisions and module-specific rules.

### Must be preserved as authoritative state

```text
SHA512 file identity
current approved user decisions
active Collection Definition
application configuration
historical information required for audit/recovery
```

This distinction is important for backup, recovery and maintenance operations.

---

# 16. Database Rebuild

A future database rebuild or repair process must not assume that every database field is equally disposable.

At minimum it must distinguish:

```text
file identity
physical location state
analysis results
user decisions
review state
history
configuration references
```

Rebuilding a derived result table must not be treated as equivalent to rebuilding the File Identity model.

Detailed rebuild procedures belong to Database Maintenance and Recovery documentation.

---

# 17. Module Cleanup

Module Result Cleanup is an explicit user operation.

Example:

```text
User installs a new IRL model
        ↓
old IRL results remain stored
        ↓
user selects Clear IRL Results
        ↓
IRL result state becomes NOT_PROCESSED
        ↓
other module results remain intact
        ↓
user runs IRL
```

Cleanup does not:

* delete physical files;
* alter SHA512 identity;
* remove Collection Definition;
* clear unrelated module results;
* silently erase protected user decisions.

The exact cleanup rules are defined in DOC-014.

---

# 18. Module Execution History

Module execution records describe what the application attempted or completed.

Execution history may contain:

```text
module
module version
execution time
status
files processed
files skipped
files failed
```

This information is historical/diagnostic and does not replace current module-result state.

The existence of an execution record does not guarantee that all results from that execution remain current.

---

# 19. Partial Execution

A module may process a large collection incrementally.

A partially completed execution must not cause already persisted successful results for unrelated files to disappear merely because later files failed.

After interruption, the next execution may continue or retry according to the module's execution rules.

This is consistent with the project's non-transactional large-scale scanning and analysis model.

---

# 20. State Transitions

A typical analysis result lifecycle is:

```text
NOT_PROCESSED
      ↓
RUNNING / execution in progress
      ↓
PROCESSED
```

Possible exceptional states include:

```text
FAILED
SKIPPED
```

When the user clears the result according to DOC-014:

```text
PROCESSED
      ↓
NOT_PROCESSED
```

The cleanup transition does not alter the underlying File Identity record.

---

# 21. File Lifecycle vs Module Lifecycle

These are separate concepts.

A file may be:

```text
ACTIVE
```

while one module's result is:

```text
NOT_PROCESSED
```

or:

```text
FAILED
```

Likewise, a file may be:

```text
MISSING
```

while its historical analysis results remain stored.

Modules must not use their own result state as a substitute for the file lifecycle state.

---

# 22. Independence and Database Communication

Modules do not call one another as part of normal data exchange.

A module writes its results to the shared database.

Another module may later read those results if useful.

Example:

```text
Universe Analysis
        ↓
DATABASE
        ↓
Character Analysis
```

Character Analysis may benefit from Universe results, but Universe Analysis does not become a runtime prerequisite simply because its results are useful.

If Universe results are absent, Character Analysis may still execute according to its own specification.

---

# 23. No Automatic Global Reprocessing

The project must not automatically interpret one changed module as a reason to rerun all other modules.

For example:

```text
IRL module updated
```

must not automatically trigger:

```text
Screenshot
Universe
Character
Theme
Set
```

unless a future explicit specification introduces such a dependency and the user authorises it.

Independent module execution is a core project principle.

---

# 24. Cleanup and Large Collections

The collection target is approximately 5,000,000 files.

Operations that affect module results at this scale must therefore be explicit and bounded.

A cleanup operation should be able to target one module/result set without requiring the entire database or all other analysis modules to be rebuilt.

User confirmation should clearly show the scope of the operation before potentially affecting millions of records.

---

# 25. Recovery Principles

Recovery tools shall prefer rebuilding derived information from authoritative information where practical.

For example:

```text
File identity retained
       ↓
module results cleared
       ↓
modules rerun
```

is preferable to inventing a second file identity simply because derived results are missing.

Recovery must preserve user decisions unless an explicit recovery operation is intentionally restoring an earlier project state.

Detailed backup and recovery procedures belong to the appropriate maintenance/recovery documents.

---

# 26. Design Philosophy

The project follows these principles:

* each kind of state has one clear owner;
* derived analysis is disposable and reproducible where practical;
* user decisions are explicit and protected;
* file identity is independent from analysis;
* Collection Definition is independent from per-file analysis;
* module execution is independent across modules;
* expensive reprocessing is user-controlled;
* history records what happened without becoming a substitute for current state;
* the database is the shared state layer between modules;
* configuration is not duplicated unnecessarily between Configuration Manager and the database.

---

# 27. Acceptance Criteria

DOC-015 is satisfied when the architecture clearly distinguishes:

* configuration from operational data;
* Collection Definition from analysis results;
* SHA512 file identity from physical location;
* current state from history;
* module results from user decisions;
* module execution history from current analysis state;
* rebuildable derived data from authoritative project state;
* independent module execution from runtime module dependencies;
* explicit result cleanup from automatic global reprocessing.

The system must be able to clear and regenerate one module's results without requiring deletion or reconstruction of unrelated project state.

---

# End of DOC-015
