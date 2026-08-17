# DOC-201

# AutoSort Engine

**Project:** AI Image Collection Management System

**Document:** DOC-201

**Module:** AutoSort Engine

**Version:** 2.1

**Status:** Draft

**Depends on:**

DOC-005
DOC-007
DOC-008
DOC-010
DOC-011
DOC-012
DOC-013
DOC-106
DOC-107
DOC-108
DOC-301
DOC-302

---

# 1. Purpose

AutoSort is the decision and filesystem-execution layer that applies existing database classifications and collection rules to the physical location of files.

AutoSort does not perform image analysis. It evaluates existing database information and performs authorised placement changes.

---

# 2. Core Philosophy

```text
Analysis Modules
      ↓
Database
      ↓
AutoSort
      ↓
Filesystem
```

AutoSort does not invent classifications. Its decisions are based on documented database results, configured thresholds, Collection Definition, Directory Access Policy and protected user decisions.

---

# 3. Responsibilities

AutoSort shall:

* evaluate database classifications and analysis results;
* determine an eligible destination according to configured placement rules;
* move files when authorised;
* maintain one canonical physical copy of each file;
* preserve manual decisions;
* prevent unwanted automatic loops;
* record performed actions;
* support repeated independent executions;
* identify files whose current location is superseded by a higher-priority valid classification.

AutoSort shall not:

* perform image analysis;
* calculate SHA512;
* rewrite analysis results owned by other modules;
* create duplicate copies, shortcuts or hardlinks;
* create arbitrary FINAL directories merely from analysis results.

---

# 4. Single Physical File Rule

The system follows:

```text
one binary object
    =
one canonical physical location
```

Multiple logical classifications may exist in the database, but the filesystem contains one canonical physical instance.

---

# 5. Database as Decision Source

The database is the authoritative source of classification information and user decisions.

The current filesystem path describes the physical state. AutoSort reconciles the physical state with the database and Collection Definition.

Example:

```text
Universe = Genshin Impact
Character = Furina
Theme = Bikini
```

The Theme result does not create a second physical copy when a valid primary collection destination exists.

---

# 6. Primary Collection Trees

A **primary collection tree** is a user-defined main organisational tree configured through Collection Definition.

Examples may include:

```text
Anime
Monster Girls
Western Animation
```

These names are illustrative only. The system must not hard-code them.

The user may define other primary trees or rename them without changing the AutoSort architecture.

All configured primary collection trees have higher organisational priority than the Theme fallback.

The general rule is:

```text
PRIMARY COLLECTION TREE(S)
            ↓
     THEMES FALLBACK
```

The exact selection between multiple primary trees is determined by Collection Definition and the applicable classification/placement rules.

---

# 7. Primary Tree Placement

AutoSort shall prefer a valid primary collection destination over Theme fallback when:

* the relevant classification confidence/status satisfies its configured threshold;
* a valid destination exists;
* the destination is permitted by the access policy;
* no protected user decision blocks the move;
* no unresolved Review Queue decision requires user input.

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

Character uncertainty does not invalidate a valid primary/Universe placement.

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

---

# 12. FINAL Directory Rules

AutoSort must not create arbitrary FINAL directories merely because a new classification is detected.

A FINAL destination must already exist in Collection Definition unless the user explicitly changes the Collection Definition through the approved configuration workflow.

A classification can therefore be valid even when no FINAL destination exists. It may be represented in AI/transition space or remain in a valid fallback location until the user defines a final destination.

---

# 13. Manual User Decisions

Manual decisions have priority over automatic placement for the relevant protected context.

This includes:

* manual classification;
* manual destination selection;
* manual rejection;
* manual correction;
* manual return to another workspace.

If the user explicitly selects a destination, that destination is considered valid for that decision context until the user changes the decision.

AutoSort must not repeatedly undo such a correction merely because a later model prediction differs.

---

# 14. Review Queue

AutoSort may consume Review Queue decisions, but an unresolved review case must not be treated as automatic acceptance.

Where user approval is required, AutoSort must wait for an applicable decision rather than performing the physical move prematurely.

The relevant decision may result in:

```text
ACCEPT
REJECT
MODIFY
DEFER
```

---

# 15. TODO Handling

TODO is a processing source/workspace defined by Collection Definition.

Files may be processed repeatedly by independent modules.

AutoSort uses currently available database information and must not invent missing classifications.

A previous rejection does not permanently disable analysis unless the user explicitly establishes such protection.

---

# 16. Execution Modes

### Preview Mode

Calculates planned actions without moving files.

### Execute Mode

Performs authorised filesystem operations.

### Audit Mode

Checks for mismatches such as:

* database state versus filesystem location;
* missing files;
* unexpected placement;
* files remaining in Theme fallback despite an available primary destination.

Audit mode does not automatically repair protected cases.

---

# 17. Repeated Independent Execution

AutoSort is independently executable and may be run repeatedly in any order relative to analysis modules.

Example:

```text
Day 1:  IRL Analysis
Day 2:  Screenshot Analysis
Day 3:  AutoSort
Day 4:  Universe Analysis
Day 5:  Theme Analysis
Day 6:  AutoSort
Day 7:  User creates a new primary destination
Day 8:  AutoSort
```

No other module process needs to remain running.

AutoSort reads the current database state at execution time.

---

# 18. File Identity

AutoSort follows DOC-012.

SHA512 is the logical binary-content identity.

A move or rename does not change SHA512.

If the binary content changes and a new SHA512 is produced, AutoSort treats it as the new binary object according to the file identity rules.

---

# 19. Access Policy

All physical operations must obey the applicable Directory Access Policy and Collection Definition.

For example:

```text
PROTECTED / READ_ONLY
    → no physical move

MODIFY
    → permitted operations according to module rules
```

A FINAL tree is not assumed to be permanently immutable, but automatic corrections must follow the configured safety and user-decision workflow.

---

# 20. Database / Filesystem Consistency

A move is considered successful only when the filesystem operation succeeds and the resulting state can be safely recorded.

If a move fails:

* the failure is logged;
* the database must not record the destination as successfully completed;
* processing of other files may continue where safe.

---

# 21. Logging

Every proposed or performed operation shall be logged according to DOC-011.

Useful information includes:

```text
execution_id
SHA512
source
destination
action
reason
result
timestamp
```

Example:

```text
Action: MOVE
Source: Themes/Bikini/image.jpg
Destination: Anime/Genshin Impact/Furina/image.jpg
Reason: higher-priority primary collection classification became available
Result: SUCCESS
```

---

# 22. No Direct Module-to-Module Communication

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

# 23. Acceptance Criteria

AutoSort is compliant when it can:

* apply database-backed classifications to physical organisation;
* maintain one canonical physical copy per binary file;
* treat every configured primary collection tree as higher priority than Theme fallback;
* use Theme when no appropriate primary destination is available;
* promote files from Theme fallback when a valid primary destination becomes available;
* support AI workspaces for classifications not yet represented in FINAL;
* avoid automatic creation of arbitrary FINAL directories;
* preserve manual user decisions;
* work with Review Queue;
* support Preview, Execute and Audit modes;
* preserve SHA512 identity during moves and renames;
* operate repeatedly and independently from analysis processes;
* exchange persistent information through the shared database;
* process large collections safely.

---

# End of DOC-201
