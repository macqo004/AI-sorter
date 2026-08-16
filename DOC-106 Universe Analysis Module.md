# DOC-106

# Universe Analysis Module

**Project:** AI Image Collection Management System

**Document:** DOC-106

**Module:** Universe Analysis

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
DOC-302

---

# 1. Purpose

The Universe Analysis module determines which fictional universe, franchise or other identifiable fictional setting is most strongly represented by an image.

The module is an analysis provider. It writes candidate classifications to the shared database and does not itself perform physical sorting or filesystem placement.

The module may produce multiple ranked candidates for the same file.

---

# 2. Responsibilities

The module shall:

* analyse images for evidence of fictional-universe membership;
* produce one or more candidate universes where evidence supports them;
* assign confidence values;
* rank candidates;
* record the version of the module/rules/model used;
* write results to the shared database;
* preserve the distinction between automatic analysis and later user decisions.

The module shall not:

* identify individual characters as its primary responsibility;
* move, rename or delete files as part of analysis;
* create or modify FINAL directory structure;
* silently overwrite user decisions;
* directly invoke another module.

---

# 3. Scope

The module recognises fictional universes and franchises represented by images.

Examples may include:

```text
Genshin Impact
Honkai: Star Rail
Zenless Zone Zero
Fate
Touhou
Azur Lane
Blue Archive
Kantai Collection
Girls' Frontline
```

This list is illustrative and not a hard-coded project taxonomy.

The supported universe catalogue may evolve independently from the module specification.

A universe may represent a game, anime, manga, visual novel, franchise, fictional setting or another identifiable fictional body of work.

The module may analyse content even when the image belongs to a universe not currently represented by a FINAL collection.

---

# 4. Module Independence

Universe Analysis is independently executable once the relevant file has a valid database identity.

Scanner must have discovered the file first, but Scanner does not need to be running while Universe Analysis executes.

Universe Analysis does not require Character Analysis, IRL Analysis or any other module to be running.

Existing results from other modules may be consumed through the database as supporting evidence.

For example:

```text
Screenshot Analysis
        ↓
Database
        ↓
Universe Analysis
```

is valid, but the producing module does not create a runtime dependency.

---

# 5. Input

The module reads the current database state for eligible files and may access the corresponding image from the filesystem when visual analysis is required.

Required information includes:

```text
SHA512
current filesystem state
image format where available
image dimensions where available
```

Optional supporting information may include Analysis Results from other modules, for example:

```text
Color Analysis
Screenshot Analysis
Reaction Analysis
IRL Analysis
Cosplay Analysis
```

Such information is consumed through the database.

Its absence must not make Universe Analysis impossible unless the module's configured strategy explicitly requires it.

---

# 6. Output

The module produces **Analysis Results** representing universe candidates.

A candidate should contain at least:

```text
file identity / SHA512
module
module version
classification type = UNIVERSE
candidate value
confidence
rank where applicable
timestamp
analysis/model/rule version
```

Multiple candidates may exist for the same file and classification context.

Candidate results are analysis evidence, not final user decisions.

---

# 7. Candidate Ranking and Thresholds

Candidates should be ordered by descending confidence or another explicitly documented ranking score.

The module may store multiple candidates rather than forcing a single answer when uncertainty exists.

The minimum confidence required for storing a candidate is configurable.

The default threshold shall not be treated as a permanent architectural constant.

A configured threshold may be used to determine whether a candidate is strong enough to enter a later workflow.

A high-confidence candidate still does not automatically authorize movement into FINAL.

For example:

```text
Universe candidate:
Ben 10

Confidence:
99.2%
```

may be strong enough for an AI/transition workflow, but it does not authorize creation of:

```text
FINAL/.../Ben 10
```

unless that destination already exists in Collection Definition or is explicitly selected by the user.

---

# 8. AI / Transition Workspace Integration

Universe Analysis may provide candidates to a later processing workflow such as AutoSort.

If a configured confidence threshold is exceeded, an authorized processing workflow may create or use a corresponding **AI/transition workspace directory** for the candidate, even when no matching FINAL directory exists.

Example:

```text
Candidate:
Ben 10
Confidence:
99.2%

AI/Ben 10/
```

This is a working/classification proposal, not a FINAL collection definition.

The creation of such a directory belongs to the authorized processing workflow, not to the analysis result itself.

The analysis module does not directly create the directory merely by producing the candidate.

---

# 9. FINAL Destination Rules

Universe Analysis shall never create new FINAL collection directories merely because a new universe is detected.

Automatic final placement is valid only when:

* the destination already exists;
* the destination is represented in Collection Definition;
* the authorized processing module has permission to perform the operation;
* all applicable review/user-decision rules are satisfied.

If no appropriate FINAL destination exists, the candidate may instead be handled through:

```text
AI / Transition workspace
Review Queue
Database-only result
User-defined destination
```

The existence of a high-confidence universe candidate does not by itself change Collection Definition.

---

# 10. Processing Rules

Universe Analysis may be executed repeatedly and independently.

For a given SHA512 and module/analysis version, an existing valid current result should normally be reused when it remains applicable.

Reprocessing may occur when:

* the file has a different SHA512;
* the module version changes;
* the model, rule set or universe catalogue changes in a way that affects the result;
* the current result is invalid or superseded;
* the user or reprocessing system explicitly requests it.

A path or filename change without a SHA512 change does not by itself invalidate the universe analysis.

If the SHA512 changes, previous candidates remain associated with the previous binary identity and must not be treated as candidates for the new binary object.

---

# 11. Manual User Decisions

A Universe Analysis result is an automatic suggestion unless explicitly converted into a user decision.

If the user manually corrects the universe or final placement, the user decision becomes authoritative for the affected classification/placement context according to DOC-013.

Later automatic Universe Analysis runs may produce new observations, but must not silently replace a protected manual decision.

The fact that a user corrected the destination means that the selected destination is considered valid for that decision context. The system must not subsequently challenge that physical placement merely because a model predicted another location.

---

# 12. Review Queue Integration

Universe Analysis may create Review Queue cases when:

* confidence is insufficient for safe automatic handling;
* multiple candidates remain materially plausible;
* the proposed destination requires user approval;
* the detected universe conflicts with an existing classification;
* a FINAL validation case requires explicit user review.

Review Queue is a user-decision mechanism and is not a second automatic classification system.

A rejected or modified suggestion must not automatically become accepted during a later repeat execution merely because the model produces the same suggestion again.

---

# 13. FINAL Validation

Universe Analysis may be configured to inspect FINAL in read-only validation mode.

For example:

```text
FINAL/Anime/Winx Club/image.jpg
        ↓
Universe Analysis
        ↓
possible candidate: Ben 10
```

The module must not move the file directly as a consequence of this result.

The result may instead become:

```text
Review Queue
```

or a configured path report/workspace workflow.

FINAL is not assumed to be error-free, but its correction remains controlled by user decision and filesystem access policy.

---

# 14. Multiple Candidates

The module should preserve useful uncertainty where more than one universe is plausible.

Example:

```text
Candidate A    0.81
Candidate B    0.13
Candidate C    0.04
```

The exact number of stored candidates is implementation/configuration dependent.

The module must not manufacture artificial certainty merely to produce a single answer.

---

# 15. Database Access

The module reads:

```text
File
Module
Analysis Results
Classification Results where relevant
Collection configuration where required for validation
```

The module writes:

```text
Analysis Results
Module Execution state
appropriate File Events where explicitly required
```

It must not overwrite analysis results owned by other modules or user decisions.

Persistent communication with other modules occurs through the shared database.

---

# 16. Performance Requirements

The module shall remain suitable for very large image collections.

Implementation should support:

* batch inference;
* configurable worker count;
* efficient reuse of valid existing results;
* optional use of cheaper supporting evidence before expensive visual inference.

The module should not require the entire collection to be loaded into memory.

---

# 17. Threading and Resource Usage

Parallel execution shall be supported.

Worker count and applicable resource limits shall be configurable through the common module interface/configuration system.

The module should use available resources efficiently while avoiding exhaustion of the configured memory/CPU budget.

Parallel workers must not produce inconsistent database state.

---

# 18. Error Handling

If an individual file cannot be analysed:

* the error shall be logged;
* other eligible files should continue where safe;
* incomplete candidate results shall not be published as valid results.

Typical recoverable failures include:

```text
corrupted image
unsupported encoding
filesystem read failure
model/inference error
insufficient access
```

An execution-level infrastructure failure may stop the execution if continuing would produce unsafe or invalid database state.

---

# 19. Logging

Each execution shall create a Module Execution record and summary log according to DOC-007 and DOC-011.

The summary should identify:

```text
started
finished
processed
skipped
errors
duration
```

Where practical, detailed entries should include the file SHA512 and the candidate/result involved.

---

# 20. Interaction with Other Modules

Universe Analysis never invokes another module directly.

Its communication model is:

```text
Database
    ↓
Universe Analysis
    ↓
Database
```

Other modules may consume its results later, especially Character Analysis and AutoSort.

No downstream module needs Universe Analysis to remain running.

Character Analysis may use Universe candidates to reduce its own search space, but this is a database-level data dependency, not a process dependency.

---

# 21. Design Philosophy

Universe Analysis is a probabilistic information provider.

Its goal is not to force every image into a universe.

The module should prefer:

```text
uncertain result
```

over:

```text
confidently wrong result
```

The confidence threshold is a workflow/configuration decision, not a universal architectural constant.

The module should remain useful even when the detected universe has no existing FINAL collection.

---

# 22. Future Extensions

Possible future capabilities include:

* improved multi-universe/crossover handling;
* scene-context analysis;
* source-art recognition;
* event/location context;
* model ensembles;
* improved candidate calibration;
* universe catalogue management.

Such extensions remain within this document when they remain logically part of universe identification. A genuinely independent function may become a separate module.

---

# 23. Acceptance Criteria

The module is considered compliant when it can:

* identify plausible fictional universes;
* produce ranked candidate results;
* preserve multiple candidates when useful;
* use configurable confidence thresholds;
* operate independently of other module processes;
* read supporting information from the database;
* associate results with the correct SHA512 identity;
* reprocess when the relevant module/model/rule version requires it;
* preserve manual user decisions;
* support FINAL validation without directly modifying FINAL;
* integrate with AI/transition workflows without creating FINAL directories;
* recover from per-file errors where safe;
* operate efficiently on large collections.

---

# End of DOC-106
