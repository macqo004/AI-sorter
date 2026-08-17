# DOC-108

# Theme Analysis Module

**Project:** AI Image Collection Management System

**Document:** DOC-108

**Module:** Theme Analysis

**Version:** 2.2

**Status:** Draft

**Depends on:**

DOC-005
DOC-007
DOC-008
DOC-010
DOC-011
DOC-012
DOC-013
DOC-302

---

# 1. Purpose

Theme Analysis detects broad visual themes present within an image.

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

Theme Analysis is an information provider. It does not itself decide physical placement and does not move files.

Themes have a special architectural role: they are a **fallback organisational classification** used when an image cannot currently be placed into an appropriate higher-priority primary collection tree.

---

# 2. Design Philosophy

Themes answer the question:

> What visual theme or subject matter is present?

rather than:

> Who is shown?

or:

> Which primary collection does the image belong to?

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
* determine primary collection placement;
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

# 9. Primary Collection Trees

A **primary collection tree** is a user-defined collection root intended to be a main organisational destination for the collection.

Examples may include roots representing broad categories such as:

```text
Anime
Monster Girls
Western Animation
```

These examples are illustrative only. Their names, number and structure are defined by the user through Collection Definition and are not hard-coded by the system.

Primary collection trees have higher organisational priority than the Themes fallback.

The general rule is:

```text
Primary Collection Tree(s)
        ↓
Themes fallback
```

Where multiple primary collection trees are configured, the system uses their configured classification/placement rules to determine the appropriate primary destination.

---

# 10. Theme as Fallback Organisation

Theme-based physical organisation is appropriate when no applicable higher-priority primary collection destination is currently available.

Example:

```text
File
 ├── no sufficiently reliable primary classification
 └── Theme = Bikini 0.96
```

The file may therefore be eligible for:

```text
Themes/Bikini/
```

provided that destination is valid according to Collection Definition and AutoSort rules.

Theme is not an equal-priority alternative to a primary collection tree.

---

# 11. Promotion from Themes to a Primary Collection

If later analysis establishes a valid higher-priority primary classification, the file may be removed from its Theme fallback location and placed into the appropriate primary collection tree by the authorised processing workflow.

Example:

```text
Before:
Themes/Bikini/image.jpg

Later database state:
Primary classification = Anime
Universe = Genshin Impact
Character = Furina

After:
Anime/Genshin Impact/Furina/image.jpg
```

The physical file is moved, not copied.

Theme Analysis results remain in the database after the move.

Theme Analysis itself never performs the move.

The exact destination is determined by Collection Definition, AutoSort and user-decision rules.

---

# 12. No Primary Destination Available

A file may have a valid Theme result while no usable primary collection destination exists.

This is a normal state, not an analysis failure.

For example:

```text
Universe = Unknown
Primary category = Unknown
Theme = Bikini
```

The file may remain in a Theme fallback location until a better primary classification becomes available.

---

# 13. Manual Decisions

Theme Analysis may provide information used by Review Queue.

A user may reject or modify a Theme interpretation or select a different physical destination.

User decisions are stored separately from automatic analysis and must not be silently overwritten.

A manual placement decision has priority over later automatic placement suggestions for the relevant context until the user changes that decision.

---

# 14. Performance and Resource Usage

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

# 15. Logging

Each execution shall create a Module Execution record and summary log according to DOC-007 and DOC-011.

The summary should include where applicable:

```text
started
finished
processed
skipped
new/updated results
errors
duration
```

Detailed errors should identify the affected file identity/path where safe.

---

# 16. Interaction with Other Modules

Theme Analysis communicates through the shared database.

For example:

```text
Universe Analysis
        ↓
Database
        ↓
AutoSort
```

may use Universe and Theme results together when determining physical placement.

Theme Analysis does not invoke Universe Analysis, Character Analysis or AutoSort directly.

AutoSort is responsible for applying the configured priority between primary collection trees and Theme fallback when deciding physical placement.

---

# 17. FINAL and AI Handling

Theme Analysis does not create FINAL directories.

FINAL destinations are defined by the user through Collection Definition.

AI/transition workspaces may be dynamically extended by authorised processing workflows when configured thresholds are satisfied.

A Theme result may therefore exist before a primary collection classification, and a Theme fallback location may later be superseded by a valid primary collection location.

---

# 18. Future Extensions

Possible future additions include:

* Theme hierarchy;
* Theme groups;
* user-defined themes;
* theme synonyms;
* confidence calibration;
* voting across multiple AI models;
* improved interaction between Theme and primary collection classification.

Extensions should remain within this module while they remain logically part of Theme Analysis.

---

# 19. Acceptance Criteria

Theme Analysis is considered compliant when it can:

* detect broad visual themes;
* support multiple themes per image;
* store confidence values;
* associate results with the correct SHA512 identity;
* operate independently of other module processes;
* avoid direct module-to-module communication;
* keep Themes subordinate to all configured primary collection trees;
* support later promotion from Themes to an appropriate primary collection when authorised;
* integrate with AutoSort and Review Queue through the database;
* never create or modify FINAL directory structure as part of analysis;
* operate efficiently on large collections.

---

# End of DOC-108
