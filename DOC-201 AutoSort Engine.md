# DOC-201

# AutoSort Engine

**Project:** AI Image Collection Management System

**Document:** DOC-201

**Module:** AutoSort Engine

**Version:** 2.0

**Status:** Draft

**Depends on:**

DOC-005
DOC-007
DOC-008
DOC-010
DOC-011
DOC-012
DOC-013
DOC-108
DOC-106
DOC-107
DOC-302

---

# 1. Purpose

AutoSort Engine is the decision and execution layer responsible for applying existing database information to the physical collection structure.

AutoSort does not perform image analysis.

It evaluates existing Analysis Results, Classification Results, Collection Definition and user decisions, then performs authorised filesystem operations.

---

# 2. Core Philosophy

The system follows:

```text
Analysis modules
    ↓
Database
    ↓
AutoSort
    ↓
physical organisation
```

AutoSort does not invent classifications.

Its decisions must be based on documented database information, configured thresholds, Collection Definition, Directory Access Policy and user-decision protections.

---

# 3. Responsibilities

AutoSort shall:

* evaluate relevant database classifications and analysis results;
* determine an eligible destination according to configured priority rules;
* move files when authorised;
* maintain one physical copy of each file;
* prevent repeated automatic moves from undoing protected user decisions;
* record performed actions;
* support repeated independent executions;
* identify files whose current location is superseded by a higher-priority valid classification.

AutoSort shall not:

* perform image analysis;
* calculate SHA512;
* rewrite another module's analysis result;
* create duplicate physical files;
* create shortcuts or hardlinks as an alternative collection copy.

---

# 4. Single Physical File Rule

The system follows:

```text
one binary object
    =
one canonical physical location
```

A file must not be intentionally duplicated across Universe, Theme, AI and other classification trees.

The database may contain multiple classifications for the same file, but the filesystem contains one canonical physical instance.

---

# 5. Database as Decision Source

The database is the authoritative source of analysis and classification information.

The current filesystem path records where the physical file is now located.

AutoSort must reconcile the two according to the rules defined here.

Example:

```text
SHA512 = ...
Universe = Genshin Impact, 0.98
Character = Furina, 0.94
Theme = Bikini, 0.97
```

A Theme result does not create a second physical copy if a valid higher-priority Universe/Character destination exists.

---

# 6. Physical Placement Priority

For the current workflow, the broad priority is:

```text
Universe
    ↓
Character, where sufficiently certain and applicable
    ↓
Theme fallback
    ↓
remain in current valid workspace / Review
```

Theme is a fallback organisation mechanism, not a peer of Universe.

A valid Universe destination supersedes a Theme destination.

---

# 7. Universe Placement

## 7.1 Existing Universe Destination

If:

```text
Universe confidence >= configured threshold
```

and a valid corresponding destination already exists in Collection Definition, AutoSort may propose or perform the move according to execution mode, access policy and user-decision rules.

Character placement may refine the destination when its own assignment threshold is satisfied and the character destination exists.

## 7.2 Universe Destination Does Not Exist

If a sufficiently confident Universe is detected but no matching FINAL destination exists, AutoSort must not create a new FINAL directory merely to satisfy the classification.

A separate AI/transition workspace may, however, be created when the configured AI workflow criteria are satisfied.

Those criteria may include:

```text
confidence threshold
AND/OR
minimum number of files assigned to the universe
```

The universe does not need to exist in FINAL for an AI workspace to be created.

Example:

```text
TODO
    ↓
Universe candidates:
Ben 10 = 0.97 for 2,500 files
    ↓
count threshold satisfied
    ↓
AI/Ben 10/
```

AI workspace creation is not equivalent to FINAL collection creation.

---

# 8. Theme Fallback Placement

Theme destinations are used when no sufficiently reliable higher-priority Universe destination is available.

Example:

```text
Universe = none / below threshold
Theme = Bikini, 0.96
```

If Collection Definition contains a valid Theme destination:

```text
FINAL/Themes/Bikini/
```

or the configured equivalent, AutoSort may use it according to execution mode and access policy.

Theme placement does not imply that the Theme is the permanent classification of the file.

---

# 9. Theme-to-Universe Migration

If a file is currently located in a Theme fallback location and a sufficiently reliable Universe classification later becomes available, AutoSort shall treat the Universe destination as higher priority.

Example:

```text
Current:
Themes/Bikini/image.jpg

Database after later analysis:
Universe = Genshin Impact, 0.98
Character = Furina, 0.94

Configured valid destination:
Universe/Genshin Impact/Furina/
```

AutoSort may move:

```text
Themes/Bikini/image.jpg
        ↓
Universe/Genshin Impact/Furina/image.jpg
```

The Theme result remains stored in the database.

No second copy is created.

The physical move is subject to:

* Collection Definition;
* Directory Access Policy;
* confidence and assignment thresholds;
* manual-decision protections;
* Review Queue requirements where applicable.

A manual user decision about destination has priority over this automatic move for the protected context.

---

# 10. Existing Universe Destination Created Later

If a Universe classification already exists in the database but no valid FINAL destination previously existed, the file may remain in Theme fallback or another valid workspace.

When the user later creates the corresponding FINAL destination through Collection Definition, a later AutoSort execution may locate matching files and move them from Theme fallback into the new Universe destination.

No new Universe analysis is required merely because the destination was created.

---

# 11. Character Placement

Character placement is subordinate to Universe placement.

Automatic character placement requires:

```text
character confidence >= configured assignment threshold
```

and a valid configured destination.

If the character confidence is insufficient, the file remains at the Universe level where a valid Universe destination exists.

Character analysis failure does not invalidate Universe placement.

---

# 12. AI Workspace Handling

AI is a working/transitional area and may contain classifications not yet represented by FINAL.

Authorised workflows may create AI subdirectories such as:

```text
AI/Ben 10/
AI/Pokemon/
AI/New Universe/
```

when configured confidence/count thresholds are satisfied.

AI workspace directories are not automatically copied into Collection Definition.

Moving a completed AI workspace into FINAL remains a controlled user workflow.

---

# 13. FINAL Directory Rules

AutoSort must never create an arbitrary new FINAL directory merely because an analysis module produced a new classification.

FINAL destinations must already be represented by Collection Definition unless the user explicitly performs a configuration change.

The fact that a Universe does not currently exist in FINAL does not make its classification invalid. It may instead be represented in AI/transition space or remain in a fallback location until the user defines an appropriate destination.

---

# 14. Manual Override Principle

Manual user actions have priority over automatic sorting actions for the protected decision context.

This includes:

* manual destination selection;
* manual classification;
* manual rejection;
* manual return to another workspace.

AutoSort must not continuously undo a user correction merely because an analysis model produces a different suggestion.

If the user explicitly selects a destination for a file, that destination is considered valid for that decision context until the user changes the decision.

---

# 15. TODO Handling

TODO is an unclassified/processing workspace.

Files in TODO may be analysed repeatedly by independent modules.

AutoSort must use current database state and valid classification results when deciding whether a file is ready to leave TODO.

A previous rejected automatic suggestion does not permanently disable future analysis, but the recorded user decision must be respected according to Review Queue/manual override rules.

---

# 16. Execution Modes

### Preview Mode

No files are moved.

The module produces planned operations.

### Execute Mode

Authorised filesystem actions are performed.

### Audit Mode

The module checks for mismatches such as:

* database location versus filesystem location;
* missing files;
* unexpected placement;
* files remaining in fallback locations despite a valid higher-priority destination.

Audit mode does not automatically repair protected cases.

---

# 17. Repeated Execution

AutoSort is independently executable and may be run repeatedly.

It should process only files whose current state requires an action.

A later execution may discover new information produced by analysis modules or new destinations added to Collection Definition.

Example:

```text
Day 1: Theme = Bikini
Day 4: Universe = Genshin Impact
Day 5: User creates valid Universe destination
Day 6: AutoSort moves file from Theme fallback to Universe destination
```

No module process needs to remain running between these executions.

---

# 18. Database and Filesystem Consistency

A move must be considered complete only when the physical operation succeeds and the database can safely record the resulting state.

If a move fails:

* the database must not report the destination as completed;
* the failure must be logged;
* other independent files may continue processing.

---

# 19. Logging

Every performed or proposed operation shall be logged according to DOC-011.

Example:

```text
SHA512: ...
Action: MOVE
Source: Themes/Bikini/image.jpg
Destination: Universe/Genshin Impact/Furina/image.jpg
Reason: higher-priority Universe classification became available
```

---

# 20. Acceptance Criteria

AutoSort is considered compliant when it can:

* apply database-backed classifications to physical organisation;
* maintain one canonical physical copy per binary file;
* respect Universe priority over Theme;
* use Theme as fallback when no sufficiently reliable Universe destination exists;
* move files from Theme fallback to Universe when a valid higher-priority Universe destination becomes available;
* support AI workspaces for universes that do not yet exist in FINAL;
* avoid automatic creation of arbitrary FINAL directories;
* respect manual user decisions;
* support repeated independent executions;
* operate safely in Preview, Execute and Audit modes.

---

# End of DOC-201
