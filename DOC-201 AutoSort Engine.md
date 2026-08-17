# DOC-201

# AutoSort Engine

**Project:** AI Image Collection Management System

**Document:** DOC-201

**Module:** AutoSort Engine

**Version:** 2.2

**Status:** Draft

**Depends on:**

DOC-005
DOC-007
DOC-008
DOC-009
DOC-010
DOC-011
DOC-012
DOC-013
DOC-106
DOC-107
DOC-108
DOC-109
DOC-302

---

# 1. Purpose

AutoSort Engine is the decision and execution layer responsible for applying existing database information to the physical collection structure.

AutoSort does not perform image analysis and does not invent semantic classifications.

It evaluates existing Analysis Results, Classification Results, Collection Definition, Directory Access Policy and user decisions, then performs authorised filesystem operations.

---

# 2. Core Philosophy

```text
Analysis Modules
       ↓
    Database
       ↓
   AutoSort
       ↓
Physical Organisation
```

The database provides the classification knowledge.

Collection Definition provides the configured collection structure and eligible destinations.

User decisions provide authoritative overrides where applicable.

AutoSort applies these inputs; it does not replace the analysis modules that produced them.

---

# 3. Responsibilities

AutoSort shall:

* evaluate relevant database classifications and analysis results;
* determine an eligible destination according to configured priority rules;
* move files when authorised;
* create authorised AI workspace directories when the configured workflow permits them;
* create authorised Set directories inside AI or an already established primary collection path when required;
* maintain one canonical physical copy of each binary file;
* prevent repeated automatic moves from undoing protected user decisions;
* record performed actions;
* support repeated independent executions;
* identify files whose current location is superseded by a higher-priority valid classification;
* reconcile existing physical organisation with current database state.

AutoSort shall not:

* perform image analysis;
* calculate SHA512;
* rewrite another module's analysis results;
* create duplicate physical files;
* create shortcuts or hardlinks as alternative collection copies;
* automatically extend the primary collection definition;
* arbitrarily invent new FINAL collection branches.

---

# 4. Single Physical File Rule

The system follows:

```text
one binary object
    =
one canonical physical location
```

A file must not be intentionally duplicated across primary collection trees, Theme trees, AI workspaces or other classification trees.

The database may contain multiple classifications and analysis results for the same file, but the filesystem contains one canonical physical instance.

---

# 5. Database and Collection Definition

The database is the authoritative source of analysis and classification information.

Collection Definition is the authoritative source of configured collection structure.

The filesystem represents the current physical state.

AutoSort reconciles these three sources according to the rules of this document.

---

# 6. Physical Placement Priority

The current organisation model uses the following broad priority:

```text
Configured Primary Collection Tree
        ↓
Configured subordinate classification levels
        ↓
Theme fallback
        ↓
remain in current valid workspace / Review
```

Primary Collection Trees are configured by the user. Examples may include Anime, Monster Girls and Western Animation, but the actual names are not hard-coded by AutoSort.

Themes are a fallback organisation mechanism, not a peer of the primary trees.

Where a reliable classification identifies a valid destination inside a primary tree, that destination has priority over Theme fallback.

Universe and Character Analysis normally provide the semantic information used to determine where a file belongs inside a primary tree, but the exact hierarchy is defined by Collection Definition.

---

# 7. Primary Collection Placement

If a sufficiently reliable classification provides a destination inside a configured primary collection tree, AutoSort may propose or perform the move according to execution mode, access policy, thresholds and user-decision rules.

A primary tree may use deeper classification levels such as Universe and Character where configured.

Example:

```text
Anime
└── Genshin Impact
    └── Furina
        image.jpg
```

If Character confidence is insufficient for assignment, the file may remain at Universe level:

```text
Anime
└── Genshin Impact
    image.jpg
```

---

# 8. Theme Fallback Placement

Theme is a fallback organisation mechanism, not a peer of the primary collection trees.

Example:

```text
Primary classification: none / insufficient
Theme: Bikini 0.96
```

The file may be eligible for:

```text
Themes/Bikini/
```

provided that destination is valid according to Collection Definition and access policy.

A Theme destination should be used only when no appropriate higher-priority primary destination is currently available.

---

# 9. Promotion from Themes to a Primary Tree

If a file currently stored under a Theme fallback later receives a valid higher-priority primary classification, AutoSort shall consider the primary destination before keeping the file in Themes.

Example:

```text
Before:
Themes/Bikini/image.jpg

Later database state:
Primary = Anime
Universe = Genshin Impact
Character = Furina

After:
Anime/Genshin Impact/Furina/image.jpg
```

The same physical file is moved; no copy is created.

Theme analysis results remain stored in the database.

This promotion may occur because of newly produced analysis results, new configuration, or a newly created valid primary destination.

---

# 10. Universe and Character

Universe and Character are common classification layers, but their exact place in the physical hierarchy depends on the configured primary tree.

Universe classification may allow movement from Theme fallback into a primary tree.

Character classification may refine that destination when the configured assignment threshold is satisfied and an appropriate destination exists.

Character uncertainty does not invalidate a valid primary or Universe placement.

---

# 11. AI Workspace

AI is a working/transitional environment and may contain classifications that are not represented in FINAL.

Authorised workflows may create AI workspace directories when configured thresholds are satisfied.

Thresholds may include:

```text
confidence threshold
and/or
minimum population/count threshold
```

Example:

```text
TODO contains many images classified as:
New Franchise

count threshold reached
        ↓
AI/New Franchise/
```

The universe or other classification does not need to exist in FINAL for the AI workspace to be created.

AI workspace creation does not change Collection Definition and does not create a FINAL destination.

AI is disposable/reconstructable working space. Removing AI does not change the database, Collection Definition or FINAL organisation.

---

# 12. Set Directory Handling

Sets are physical collections of visually related files.

An authorised workflow may create Set directories:

### Inside AI

```text
AI/Sets/0001/
AI/Sets/0002/
```

### Inside an already established primary tree

```text
Anime/Genshin Impact/Furina/0001/
Anime/Genshin Impact/Furina/0002/
```

Set directory creation must not be confused with creation of a new primary semantic branch.

AutoSort or the authorised Set workflow may create the Set-level directory only when its parent collection path is already established and permitted by Collection Definition.

The Set's logical identity is stored in the database; a numeric folder name is only a physical representation.

Set directories must not be used as evidence that their numeric names represent characters, universes or other semantic classifications.

---

# 13. FINAL Directory Rules

FINAL structure is controlled by Collection Definition and the user.

AutoSort must not automatically create arbitrary new FINAL primary collection branches because an analysis module produced a new classification.

A new FINAL destination becomes available only when the user/configuration explicitly establishes it in Collection Definition.

An AI workspace may therefore contain a universe or other classification that has no FINAL counterpart yet.

---

# 14. Existing Destination Created Later

If a classification already exists in the database but no valid FINAL destination previously existed, the file may remain in Theme fallback, AI or another valid workspace.

When the user later creates the corresponding destination through Collection Definition, a later AutoSort execution may identify the affected files and move them to the newly valid destination.

No new analysis is required merely because the destination was created.

---

# 15. User Verification and Manual Decisions

AI placement represents proposed or working organisation unless and until the user establishes a final destination through the normal workflow.

The user may:

* accept the proposed organisation;
* reject it;
* select another destination;
* move a file or Set manually;
* return it to another workspace.

A manually selected destination is considered valid for that protected decision context.

Later automatic processing must not repeatedly move the file away from that user-selected destination merely because the model produces another suggestion.

The user may later change the decision explicitly.

---

# 16. TODO Handling

TODO is an unclassified/processing workspace.

Files in TODO may be analysed repeatedly by independent modules.

AutoSort uses current database state and valid classification results when deciding whether a file is ready to leave TODO.

A previous rejected automatic suggestion does not permanently disable future analysis, but the recorded user decision must be respected according to Review Queue/manual override rules.

---

# 17. Execution Modes

## Preview Mode

No files are moved.

The module produces planned operations.

## Execute Mode

Authorised filesystem actions are performed.

## Audit Mode

The module checks for mismatches such as:

* database location versus filesystem location;
* missing files;
* unexpected placement;
* files remaining in fallback locations despite a valid higher-priority primary destination;
* Set directories inconsistent with their logical database parent.

Audit mode does not automatically repair protected cases.

---

# 18. Repeated Execution

AutoSort is independently executable and may be run repeatedly.

It should process only files whose current state requires an action.

A later execution may discover new information produced by analysis modules, newly configured destinations, or newly created valid parent paths for Set placement.

Example:

```text
Day 1: Theme = Bikini
Day 4: Universe = Genshin Impact
Day 5: User creates valid Anime/Genshin Impact/Furina/
Day 6: AutoSort moves file from Theme fallback to primary tree
Day 7: Set Detection creates/updates Set 0007 inside Furina
```

No module process needs to remain running between these executions.

---

# 19. Database and Filesystem Consistency

A filesystem operation is considered complete only when the physical operation succeeds and the resulting state can safely be persisted to the database.

If a move or directory operation fails:

* the database must not report the operation as completed;
* the failure must be logged;
* unrelated independent work may continue where safe.

---

# 20. Logging

Every performed or proposed operation shall be logged according to DOC-011.

Example:

```text
SHA512: ...
Action: MOVE
Source: Themes/Bikini/image.jpg
Destination: Anime/Genshin Impact/Furina/image.jpg
Reason: valid higher-priority primary-tree classification became available
```

---

# 21. No Direct Module-to-Module Communication

AutoSort does not invoke analysis modules directly.

The communication model is:

```text
Analysis Modules
       ↓
    Database
       ↓
    AutoSort
       ↓
   Filesystem
```

Persistent information shared between analysis modules is exchanged through the database.

---

# 22. Acceptance Criteria

AutoSort is considered compliant when it can:

* apply database-backed classifications to physical organisation;
* maintain one canonical physical copy per binary file;
* treat all configured primary collection trees as higher priority than Theme fallback;
* use Theme as fallback when no sufficiently reliable primary destination exists;
* move files from Theme fallback into a valid primary destination when one becomes available;
* support AI workspaces for classifications that do not yet exist in FINAL;
* support Set directories inside AI and inside already established primary-tree parent paths;
* avoid automatic creation of arbitrary FINAL primary branches;
* respect manual user decisions;
* support repeated independent executions;
* operate safely in Preview, Execute and Audit modes.

---

# End of DOC-201
