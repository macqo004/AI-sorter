# DOC-401

# Collection Consistency Checker

**Project:** AI Image Collection Management System

**Document:** DOC-401

**Module:** Collection Consistency Checker

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
DOC-106
DOC-107
DOC-108
DOC-201
DOC-302

---

# 1. Purpose

Collection Consistency Checker is a validation and maintenance module for the user's existing **FINAL** collection.

Its purpose is to detect cases where the current physical location of a file is inconsistent with the classification information currently stored in the database and the active Collection Definition.

The module does not perform normal TODO processing, does not act as an AutoSort replacement, and does not automatically modify FINAL.

The central principle is:

> FINAL is user-approved organisation, but it is not assumed to be permanently free of historical classification errors.

The module therefore performs read-only validation and produces cases for user review when a possible inconsistency is detected.

---

# 2. Scope

The normal validation scope is configured FINAL collection roots and their permitted descendants according to Collection Definition and Directory Access Policy.

The module does not use TODO or AI as its primary validation target.

The exact validation scope may be restricted to selected FINAL trees when configured.

FINAL is always treated as a **read-only validation source** by this module.

The module may inspect:

* current filesystem paths;
* file identities;
* database classifications;
* analysis results;
* Collection Definition;
* user decisions and protected manual corrections.

The module shall not directly move, rename, delete, or create files or directories in FINAL.

---

# 3. Relation to AutoSort

AutoSort is the normal placement/execution mechanism for authorised filesystem changes.

Collection Consistency Checker has a different responsibility:

```text
AutoSort
    = apply authorised placement decisions

Collection Consistency Checker
    = detect possible inconsistencies in FINAL
```

The Checker shall not silently convert a detected inconsistency into an AutoSort operation.

Instead, it creates a Review Queue case when user intervention is appropriate.

---

# 4. Input

The module reads:

```text
current FINAL filesystem state
file identity / SHA512
current_path
Collection Definition
analysis results
user decisions
manual-correction history
```

The module should prefer already valid analysis results stored in the database.

It may identify that a required analysis result is absent or outdated, but it shall not assume that absence itself proves that the current FINAL location is wrong.

Expensive new analysis may be performed by the appropriate analysis module in a separate user-initiated execution.

---

# 5. File Identity and Validation

File identity follows DOC-012.

The checker shall use SHA512 as the binary-content identity and `file_id` as the internal database identifier.

A rename or move does not change file identity.

If the filesystem object now has a different SHA512 from the database record, the checker shall treat this as a file-identity inconsistency rather than silently applying an old classification to the new binary object.

Such a case may require Review Queue handling or Scanner/database reconciliation before classification validation can continue.

---

# 6. Primary Collection Structure

The checker shall not hard-code names such as:

```text
Anime
Monster Girls
Western Animation
Themes
```

These are examples only.

Actual primary collection trees and Theme fallback are defined by Collection Definition.

The checker evaluates the current location against the configured role of the relevant tree.

All configured primary collection trees have higher organisational priority than Theme fallback.

---

# 7. Consistency Rules

A possible inconsistency may exist when:

* the file is physically located in a valid FINAL tree;
* current database classifications indicate a different valid higher-priority placement;
* the proposed destination exists in Collection Definition;
* no protected manual decision explains the current placement;
* the evidence is sufficiently strong to justify user review.

Example:

```text
Current:
FINAL/Winx Club/image.jpg

Database:
Universe = Ben 10, confidence 0.99

Potential result:
Review Queue case
```

The Checker does not move the file.

---

# 8. Theme Fallback Validation

Theme is a fallback below the configured primary collection trees.

The checker may identify a file currently located under a Theme fallback when a sufficiently reliable primary classification is now available.

Example:

```text
Themes/Bikini/image.jpg

Database:
Primary tree = Anime
Universe = Genshin Impact
Character = Furina
```

If the corresponding destination exists in Collection Definition, the Checker may create a Review Queue case proposing validation of the current placement.

Theme analysis information remains valid metadata even when the physical Theme placement is no longer appropriate.

---

# 9. Existing FINAL Errors

FINAL may contain historical errors.

Example:

```text
FINAL
└── Winx Club
    └── ben10_image.jpg
```

The image may be correctly identified by later analysis as belonging to another universe.

The checker shall report the discrepancy instead of assuming that the existing FINAL location is authoritative evidence of classification.

The existing location remains physically unchanged until the user decides otherwise.

---

# 10. Review Queue Integration

Detected inconsistencies shall normally become Review Queue cases according to DOC-013.

The case should contain at minimum:

```text
file_id
SHA512
current_path
suggested destination or correction context
reason
relevant analysis results
confidence
source module
```

Review Queue is the common user-decision mechanism.

The checker shall not maintain a separate independent Migration Queue as a second decision system.

Where a migration-like action is suggested, it is represented as a Review Queue case with the relevant proposed destination.

---

# 11. User Decisions

The Review Queue supports the project's common decision model:

```text
ACCEPT
REJECT
MODIFY
DEFER
```

For a consistency case, these decisions may result in a physical move or other approved correction performed through the authorised workflow.

The checker itself does not execute the move.

If the user chooses a destination different from the system's suggestion, the user's selected destination becomes the accepted placement for that decision context.

The file's new location must not be treated as suspicious merely because it differs from the original automated suggestion.

Manual correction should be recorded so that later automatic checks do not immediately propose undoing it.

---

# 12. Validation of Manual Corrections

A manually corrected file may later be revalidated.

The checker should distinguish between:

```text
current user-approved placement
```

and:

```text
old automatic suggestion
```

A manual correction has priority over the old suggestion unless the user later changes the placement or explicitly requests reevaluation.

This does not prevent the system from identifying a completely new and materially different inconsistency in the future.

---

# 13. Collection Definition Validation

A suggested destination is valid only when the relevant path is represented by Collection Definition and permitted by its rules.

The checker shall not invent new FINAL destinations.

If analysis identifies a new universe that has no corresponding FINAL destination, the checker shall not propose an arbitrary new FINAL path merely because the model produced that universe.

Such a classification may instead be handled by the AI/transition workflow defined elsewhere.

---

# 14. AI and TODO

AI and TODO are outside the normal validation target of this module.

A file already undergoing transitional processing should be handled by the normal analysis and AutoSort workflow rather than being treated as a FINAL consistency problem.

The checker may record that a FINAL file should be considered for further analysis, but the actual analysis remains the responsibility of the relevant analysis module.

---

# 15. Validation Levels

The checker may operate in several validation modes.

### Location Validation

Checks whether the current path is compatible with the current classification and Collection Definition.

### Identity Validation

Checks whether the filesystem object matches the expected SHA512 identity.

### Classification Validation

Checks whether strong current analysis suggests a different primary placement.

### Structural Validation

Checks whether the current directory path remains represented correctly by Collection Definition.

A run may enable one or more validation levels.

---

# 16. Confidence and Thresholds

The checker shall use configurable thresholds appropriate to the classification being validated.

It shall not hard-code project-wide confidence values from older specifications.

The checker should prefer strong evidence for automatic creation of a Review Queue case and should avoid generating large numbers of low-value suggestions.

Confidence is evidence for review, not permission to modify FINAL.

---

# 17. Duplicate and Set Considerations

The checker does not replace Duplicate Management or Set Detection.

Duplicate Management is responsible for identical binary content relationships.

Set Detection is responsible for visual grouping.

The checker may use their results as supporting information where appropriate, but classification consistency remains its primary purpose.

---

# 18. Repeated Execution

Collection Consistency Checker is independently executable and may be run repeatedly.

A run should consider the current database state and current FINAL filesystem state.

Example:

```text
Day 1: FINAL contains historical placement
Day 5: Universe Analysis is updated
Day 6: Consistency Checker is run
Day 6: Review Queue case created
Day 7: User chooses MODIFY
Day 8: authorised workflow performs the correction
Day 20: Checker is run again
```

The old case should not be recreated as a new unresolved problem after the correction has been accepted and recorded.

---

# 19. Database Storage

The checker stores execution information and Review Queue cases through the shared database.

Persistent communication with analysis and execution modules occurs through the database.

The checker shall not directly invoke AutoSort or analysis modules.

---

# 20. Reporting and Export

The module shall provide a readable execution summary and may export unresolved cases for external review.

Possible export formats include:

```text
TXT
CSV
```

For FINAL cases, a text export containing current paths and suggested destinations is a valid supplementary workflow.

Export is a report, not a command to modify files.

---

# 21. Error Handling

An error affecting one file shall not stop validation of unrelated files where safe.

Examples include:

* unreadable file;
* missing filesystem object;
* stale database path;
* SHA512 mismatch;
* missing analysis result;
* invalid Collection Definition reference.

The error shall be logged according to DOC-011.

Where the problem prevents a safe conclusion, the checker should create an appropriate Review Queue case or report the condition without guessing.

---

# 22. Logging

Each execution shall create the standard Module Execution record and a readable summary log.

The summary should include where applicable:

```text
started
finished
files examined
identity mismatches
possible placement inconsistencies
Review Queue cases created
skipped items
errors
duration
```

---

# 23. Safety Principles

Collection Consistency Checker follows these principles:

1. FINAL is validated read-only.
2. Existing placement is not assumed to be infallible.
3. Analysis results are evidence, not direct filesystem commands.
4. The user remains the authority over correction.
5. Manual corrections have priority over old automatic suggestions.
6. No arbitrary FINAL destination is invented.
7. Uncertainty is reported rather than guessed.
8. The module never performs the physical correction itself.

---

# 24. Acceptance Criteria

Collection Consistency Checker is compliant when it can:

* inspect configured FINAL trees without modifying them;
* compare physical location with current database knowledge;
* detect possible historical classification errors;
* recognise when Theme fallback is superseded by a valid primary destination;
* detect identity mismatches between filesystem and database;
* use Collection Definition to validate candidate destinations;
* create Review Queue cases instead of an independent migration decision mechanism;
* preserve and respect manual user corrections;
* export readable reports;
* operate repeatedly and independently;
* avoid automatically modifying FINAL.

---

# End of DOC-401
