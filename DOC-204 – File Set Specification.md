# DOC-401

# Collection Consistency Checker

**Project:** AI Image Collection Management System

**Document:** DOC-401

**Version:** 1.0

**Status:** Design Specification

---

# 1. Purpose

Collection Consistency Checker is a maintenance module responsible for auditing the user's existing collection.

Unlike AutoSort, this module does **not** process new images.

Its purpose is to detect images that, according to the current knowledge base and analysis modules, should now belong to a different location within the collection.

The module never performs automatic file operations.

---

# 2. Scope

The module analyses only the **FINAL** collection.

It never analyses:

* TODO
* AI

The FINAL collection is treated as read-only.

---

# 3. Input

Input consists of:

* image files stored in FINAL Collection Trees,
* database observations,
* Collection Definition,
* results produced by previously executed analysis modules.

No new AI analysis is required if valid observations already exist in the database.

---

# 4. Output

The module produces:

* migration suggestions stored in the database,
* an exportable migration report.

The module never moves files.

---

# 5. Typical Use Case

Example:

Current location:

```text
Monster Girls
└── Kemono
    └── Raphtalia.jpg
```

Database:

* Universe = Shield Hero (0.99)
* Character = Raphtalia (0.98)

Collection Definition:

```text
Anime
└── Shield Hero
    └── Raphtalia
```

Result:

Migration suggestion generated.

---

# 6. Migration Logic

A migration suggestion is created when:

* the recognised destination exists inside Collection Definition;
* the suggested destination differs from the current location;
* confidence exceeds the configured threshold;
* no active user rejection exists.

---

# 7. Confidence Threshold

The module uses configurable confidence thresholds.

Default values:

Universe

0.95

Character

0.75

Species

0.90

Theme

0.90

Values may be changed in future versions.

---

# 8. Migration Report

The module exports the Migration Queue.

Preferred formats:

* CSV
* TXT

CSV is recommended.

Example:

```csv
CurrentPath;SuggestedDestination;Universe;Character;Confidence;Reason;SHA512

Monster Girls\Kemono\Raphtalia.jpg;
Anime\Shield Hero\Raphtalia;
Shield Hero;
Raphtalia;
0.98;
Universe detected;
3EAB...
```

---

# 9. Database Storage

Every suggestion is stored inside the database.

Suggested table:

MigrationSuggestion

Recommended fields:

* SuggestionID
* ImageID
* SHA512
* CurrentLocation
* SuggestedLocation
* Universe
* Character
* Confidence
* Reason
* Status
* CreatedAt
* ReviewedAt

---

# 10. Suggestion Status

Possible statuses:

Pending

Suggestion has not been reviewed.

Accepted

The user accepted the suggestion.

Rejected

The user permanently rejected the suggestion.

Resolved

The file has already been moved to the suggested destination.

---

# 11. User Decisions

The module never changes the collection automatically.

Only the user may:

* accept,
* reject,
* ignore

a migration suggestion.

---

# 12. Permanent Rejection

Rejected suggestions remain stored.

Future executions of Collection Consistency Checker do not recreate identical suggestions.

This prevents repeatedly reporting the same image.

---

# 13. Automatic Resolution

If a previously reported image is manually moved by the user to the suggested destination, the module automatically marks the suggestion as:

Resolved

No user interaction is required.

---

# 14. Collection Definition Verification

Suggestions are generated only when the destination exists inside Collection Definition.

If the destination does not exist:

* no migration suggestion is generated;
* only the database observations are retained.

This prevents suggestions pointing to non-existent folders.

---

# 15. Relationship with Other Modules

Collection Consistency Checker depends on:

* Scanner
* Analysis Modules
* Collection Definition
* Database

It is independent from:

* AutoSort
* TODO processing
* AI workspace

---

# 16. Workflow

```text
FINAL

↓

Read database observations

↓

Compare with Collection Definition

↓

Generate migration suggestions

↓

Store suggestions

↓

Export migration report
```

No files are modified during this process.

---

# 17. Design Principles

Collection Consistency Checker:

* analyses FINAL only;
* never modifies FINAL;
* never creates directories;
* never deletes files;
* never performs automatic migration;
* always reports suggestions only.

---

# 18. Future Extensions

Possible future improvements:

* batch approval interface;
* graphical migration review;
* duplicate migration detection;
* migration statistics;
* prioritisation by confidence;
* filtering by Collection Tree.

---

# 19. Acceptance Criteria

The module is considered complete when it:

* detects outdated classifications;
* generates migration suggestions;
* stores suggestions in the database;
* exports a migration report;
* supports Accepted, Rejected and Resolved states;
* never performs automatic modifications of FINAL.

---

# End of DOC-401
