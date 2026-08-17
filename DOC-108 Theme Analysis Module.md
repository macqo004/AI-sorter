# DOC-108

# Theme Analysis Module

**Project:** AI Image Collection Management System

**Document:** DOC-108

**Module:** Theme Analysis

**Version:** 2.1

**Status:** Draft

---

# 1. Purpose

Theme Analysis detects broad visual themes present within an image.

The module does not determine:

* Universe
* Character
* Species

Those responsibilities belong to dedicated modules.

Theme Analysis focuses on general visual content and provides information that may be used as a **fallback organisation mechanism** when no sufficiently reliable higher-priority universe classification is available.

Examples include:

```text
Bikini
Christmas
Halloween
Maid
Beach
School Uniform
Kimono
```

The module stores analysis results in the database.

It does not itself move files or decide physical placement.

---

# 2. Design Philosophy

Themes answer the question:

> What visual theme or subject matter is present?

rather than:

> Who is shown?

or:

> Which fictional universe does the image belong to?

Examples of valid themes:

```text
Bikini
Beach
Christmas
School Uniform
```

Examples outside the primary responsibility of Theme Analysis:

```text
Furina
Genshin Impact
Demon Girl
```

A theme is metadata. It is not, by itself, a final filesystem placement command.

---

# 3. Responsibilities

Theme Analysis shall:

* analyse visual themes;
* assign confidence values where meaningful;
* support multiple themes per file;
* write results to the shared database;
* preserve the distinction between automatic analysis and user decisions.

Theme Analysis shall not:

* move files;
* rename files;
* create FINAL directories;
* identify a Universe as its primary responsibility;
* identify Characters as its primary responsibility;
* analyse Monster Girl species as its primary responsibility;
* directly invoke another module.

---

# 4. Input

The module reads the current database state for eligible files and may access the corresponding image from the filesystem when visual analysis requires it.

Required information includes:

```text
SHA512
current filesystem state
image format where available
image dimensions where available
```

Supporting information from other analysis modules may be consumed through the database when useful.

Theme Analysis does not require another module process to be running.

---

# 5. Output

The module produces **Analysis Results** as defined by DOC-005.

Each detected theme creates an analysis result containing at least:

```text
file identity / SHA512
module
module version
theme value
confidence where applicable
timestamp
analysis/model/rule version
```

An image may have multiple valid themes.

Example:

```text
Bikini     0.97
Beach      0.92
Christmas  0.83
```

Each result remains independent in the database.

---

# 6. Theme Categories

Themes are intentionally broad and expandable.

### Clothing

```text
Bikini
Maid
Kimono
School Uniform
```

### Seasonal

```text
Christmas
Halloween
Valentine's Day
```

### Environment

```text
Beach
Swimming Pool
Forest
```

### General Concepts

```text
Winter
Summer
Festival
```

The list is not a hard-coded project taxonomy.

Theme definitions may evolve through configuration/model updates.

---

# 7. Theme Confidence

Each classification-like theme result should include a confidence value where meaningful.

Confidence describes the strength of evidence that the theme is present.

A low-confidence theme may still be retained as analysis information, but it must not automatically cause physical sorting.

The exact calculation method is implementation-defined.

---

# 8. Processing Rules

Theme Analysis may be executed repeatedly and independently.

For a given SHA512 and module/analysis version, an existing valid current result should normally be reused where applicable.

Reprocessing may occur when:

* the file has a different SHA512;
* the module version changes;
* the theme catalogue, model or rule set changes in a way that affects the result;
* the result is invalid or superseded;
* the user or reprocessing system explicitly requests recalculation.

A rename or move without a SHA512 change does not by itself invalidate theme results.

If the SHA512 changes, results belonging to the previous binary identity remain associated with that previous identity.

---

# 9. Theme as Fallback Organisation

Theme is a **fallback**, not an equal-priority alternative to Universe.

The intended classification hierarchy is broadly:

```text
Universe
   ↓
Character, where sufficiently certain and applicable
   ↓
Theme fallback
```

Theme-based physical organisation is appropriate when the system does not have a sufficiently reliable Universe classification that can provide a better destination.

For example:

```text
File
 ├── Universe: none / insufficient confidence
 └── Theme: Bikini 0.96
```

The file may therefore be eligible for a configured Theme destination such as:

```text
Themes/Bikini/
```

provided that destination is valid according to Collection Definition and AutoSort rules.

---

# 10. Universe Supersedes Theme as Physical Organisation

If a file is currently organised under a Theme fallback and later receives a sufficiently reliable Universe classification, the Universe classification takes precedence over Theme for physical organisation.

Example:

```text
Themes/Bikini/image.jpg
        ↓
Universe Analysis
        ↓
Genshin Impact / Furina
```

The database still retains the Theme result:

```text
Theme = Bikini
```

but the physical file should no longer remain in the Theme fallback location when a valid higher-priority Universe destination is available.

An authorised processing module such as AutoSort may therefore **take the file out of the Theme tree and move it into the appropriate Universe tree**.

This is not a new classification of the Theme result. It is a change in physical organisation because a higher-priority classification became available.

The move must obey:

* Collection Definition;
* applicable Directory Access Policy;
* confidence thresholds;
* manual-decision protections;
* Review Queue rules where user approval is required.

---

# 11. Theme Does Not Override Universe

Example:

```text
Universe: Genshin Impact 0.98
Character: Furina 0.94
Theme: Bikini 0.97
```

The physical organisation is determined by the higher-priority Universe/Character structure, not by `Themes/Bikini`.

The Theme result remains stored as metadata and can still be used for search, filtering, statistics or later workflows.

---

# 12. Unknown Universe / Future Universe Case

Theme fallback is particularly useful when the system cannot currently identify a reliable Universe.

Later, Universe Analysis may identify a Universe that was previously unknown or not yet represented in FINAL.

In that case, the Universe result may enter an AI/transition workflow.

For example:

```text
Themes/Bikini/image.jpg
        ↓
Universe Analysis
        ↓
Universe = New Franchise
        ↓
AI/New Franchise/
```

The AI workspace may be created when the relevant configured confidence/count threshold is met, even when the Universe does not yet exist in FINAL.

When the user later approves the organisation, the content may be moved into the appropriate FINAL tree.

---

# 13. Future Collection Expansion

Theme Analysis does not itself change Collection Definition.

If a user later creates a dedicated Universe destination in FINAL, existing database Universe results may allow AutoSort to identify files that were previously stored under Theme fallback and move them into the new Universe location during a later authorised execution.

Example:

```text
Previously:
Themes/Fairy/image.jpg

Database:
Universe = Winx Club
```

Later the user defines:

```text
FINAL/.../Winx Club/
```

AutoSort may then relocate the affected file, subject to the configured rules and user-decision protections.

Theme Analysis itself performs no filesystem movement.

---

# 14. Manual Decisions

Theme Analysis may provide information used by Review Queue.

A user may reject or modify a Theme interpretation.

User decisions are stored separately from automatic analysis and must not be silently overwritten.

A manual placement decision has priority over a later automatic placement suggestion for the relevant context until the user changes that decision.

---

# 15. Performance and Resource Usage

Theme Analysis should balance speed and accuracy.

The module should support:

* GPU acceleration when available;
* CPU fallback;
* batch processing;
* multi-threading;
* incremental processing;
* efficient reuse of valid existing results.

The module should not require the entire collection in memory.

---

# 16. Logging

Each execution shall create a Module Execution record and a summary log according to DOC-007 and DOC-011.

The summary should include where applicable:

```text
started
finished
processed
skipped
new results
errors
duration
```

Detailed errors should identify the affected file identity/path where safe.

---

# 17. Interaction with Other Modules

Theme Analysis communicates through the shared database.

For example:

```text
Universe Analysis
        ↓
Database
        ↓
Theme-aware workflow / AutoSort
```

Theme Analysis does not invoke Universe Analysis, Character Analysis or AutoSort directly.

AutoSort is responsible for applying the hierarchy between Universe and Theme when deciding physical placement.

---

# 18. FINAL and AI Handling

Theme Analysis does not create FINAL directories.

FINAL destinations are defined by the user through Collection Definition.

AI/transition workspaces may be dynamically extended by authorised processing workflows when configured thresholds are satisfied.

A Theme result therefore may exist before a Universe result, and a Theme fallback location may later be superseded by a valid Universe location.

---

# 19. Future Extensions

Possible future additions include:

* Theme hierarchy;
* Theme groups;
* user-defined themes;
* theme synonyms;
* confidence calibration;
* voting across multiple AI models;
* improved interaction between Theme and Universe classification.

Extensions should remain within this module while they remain logically part of Theme Analysis.

---

# 20. Acceptance Criteria

Theme Analysis is considered compliant when it can:

* detect broad visual themes;
* support multiple themes per image;
* store confidence values;
* associate results with the correct SHA512 identity;
* operate independently of other module processes;
* avoid direct module-to-module communication;
* preserve Theme information when Universe classification supersedes it physically;
* support Theme as a fallback when no sufficiently reliable Universe classification is available;
* expose results to AutoSort through the shared database;
* never create or modify FINAL directory structure as part of analysis;
* support future expansion without unnecessary redesign.

---

# End of DOC-108
