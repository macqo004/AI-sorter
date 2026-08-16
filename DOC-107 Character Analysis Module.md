# DOC-107

# Character Analysis Module

**Project:** AI Image Collection Management System

**Document:** DOC-107

**Module:** Character Analysis

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

---

# 1. Purpose

The Character Analysis module identifies fictional characters depicted in an image.

The module is an analysis provider. It writes candidate character classifications to the shared database and does not itself perform physical sorting or filesystem placement.

Character Analysis is a refinement layer. A character result may provide more specific information than a universe result, but failure to identify a character does not invalidate the universe classification.

---

# 2. Module Independence

Character Analysis is independently executable once the relevant file has a valid database identity.

Scanner must have discovered the file first, but Scanner does not need to be running while Character Analysis executes.

Universe Analysis may provide useful candidate universes through the database, but it is **not a runtime dependency**.

For example:

```text
Universe Analysis
        ↓
Database
        ↓
Character Analysis
```

is an efficient workflow, but Character Analysis must not require Universe Analysis to be running or to have been executed immediately beforehand.

If suitable Universe Analysis results are available, Character Analysis should use them to reduce its search space. If they are absent, the module may use its configured fallback strategy, such as a broader character search, or skip the file when the selected strategy explicitly requires universe candidates.

The module never invokes Universe Analysis or any other module directly.

---

# 3. Responsibilities

The module shall:

* identify candidate fictional characters;
* use available universe information as supporting data when useful;
* rank character candidates;
* assign confidence values where meaningful;
* record the module/model/rule version used;
* write candidate results to the shared database;
* preserve the distinction between automatic analysis and user decisions.

The module shall not:

* identify real people as its primary responsibility;
* move, rename or delete files as part of analysis;
* create or modify FINAL directory structure;
* silently overwrite user decisions;
* modify analysis results owned by other modules;
* directly invoke another module.

---

# 4. Scope

The module recognises fictional characters belonging to supported universes or other supported character catalogues.

Examples may include:

```text
Furina
Nahida
Raiden Shogun
Lumine
March 7th
Firefly
```

The supported character catalogue is implementation/configuration data and is not a hard-coded project taxonomy.

The module may identify characters even when the corresponding universe does not currently have a FINAL collection.

A character candidate is an analysis result, not a final filesystem decision.

---

# 5. Input

The module reads current database state for eligible files and may access the corresponding image from the filesystem when visual analysis is required.

Required information includes:

```text
SHA512
current filesystem state
image format where available
image dimensions where available
```

Optional supporting information may include:

```text
Universe Analysis results
Cosplay Analysis results
Screenshot Analysis results
Color Analysis results
other documented Analysis Results
```

Supporting information is consumed through the shared database.

A Universe Analysis result may greatly reduce the search space, but absence of that result must not create a process dependency.

---

# 6. Output

The module produces **Analysis Results** representing character candidates.

A candidate should contain at least:

```text
file identity / SHA512
module
module version
classification type = CHARACTER
candidate value
confidence
rank where applicable
timestamp
analysis/model/rule version
```

Multiple character candidates may be stored for the same file and classification context.

Candidate results are suggestions and evidence, not automatic user decisions.

---

# 7. Candidate Thresholds

Candidate storage and automatic placement are separate concepts.

### Candidate storage threshold

A configurable threshold may determine which candidates are worth storing.

### Automatic assignment threshold

A separate configurable threshold may determine whether a downstream workflow may treat the highest-ranked character as sufficiently reliable for automatic placement.

Illustrative configuration:

```text
CharacterStoreThreshold = configurable
CharacterAssignmentThreshold = configurable
```

These values are not fixed architectural constants.

A candidate may therefore be stored without being strong enough for automatic placement.

A high-confidence character result does not by itself authorize movement into FINAL.

---

# 8. Character Assignment Philosophy

Character identification is an optional refinement layer.

If a character cannot be identified with sufficient confidence, the system may retain the stronger universe-level classification without forcing a character assignment.

Example:

```text
Universe:
Genshin Impact

Character:
uncertain
```

This is a valid result.

The module should prefer uncertainty over false certainty.

---

# 9. Processing Rules

Character Analysis may be executed repeatedly and independently.

For a given SHA512 and module/analysis version, a valid current result should normally be reused rather than recalculated unnecessarily.

Reprocessing may occur when:

* the file has a different SHA512;
* the module version changes;
* the character model, rule set or character catalogue changes in a way that affects the result;
* supporting universe data changes materially and the configured policy requires reprocessing;
* an existing result is invalid or superseded;
* the user or reprocessing system explicitly requests recalculation.

A rename or move without a SHA512 change does not by itself invalidate character analysis.

If SHA512 changes, results belonging to the previous binary identity remain associated with that previous identity and must not be treated as results for the new binary object.

---

# 10. Database Access

The module reads, where required:

```text
File
Module
Analysis Results
Classification Results where relevant
Collection configuration where needed for validation
```

The module writes:

```text
Analysis Results for CHARACTER
Module Execution state
appropriate File Events where explicitly required
```

It must not overwrite another module's analysis results or user decisions.

Persistent communication with other modules occurs through the shared database.

---

# 11. Performance Requirements

The module is intended for very large collections.

The preferred execution strategy is to narrow the character search space whenever reliable supporting information exists.

For example:

```text
Universe = Genshin Impact
        ↓
search characters from Genshin catalogue
```

instead of searching the entire character catalogue.

When Universe Analysis results are absent, a broader search strategy may be used only when configured and computationally practical.

The module should avoid loading the entire collection into memory.

---

# 12. Threading and Resource Usage

Parallel execution shall be supported.

Worker count and resource limits shall be configurable through the common module interface/configuration system.

The module should use available CPU, GPU and memory resources efficiently without exhausting configured limits.

Parallel execution must not produce conflicting database state.

---

# 13. Error Handling

If an individual file cannot be analysed:

* the error shall be logged according to DOC-011;
* processing of other eligible files should continue where safe;
* incomplete or invalid character results shall not be published as valid results.

Typical recoverable conditions include:

```text
corrupted image
unsupported image encoding
filesystem read failure
model/inference failure
insufficient access
```

An execution-level infrastructure failure may stop the execution when continuing would risk invalid database state.

---

# 14. Logging

Each execution shall create a Module Execution record and summary log according to DOC-007 and DOC-011.

The summary should include, where applicable:

```text
started
finished
processed
skipped
errors
duration
```

Detailed records should identify the affected SHA512 and candidate/result where practical.

---

# 15. Review Queue Integration

Character Analysis may create Review Queue cases when:

* multiple character candidates remain materially plausible;
* confidence is insufficient for the configured workflow;
* a proposed character assignment would have material consequences;
* an existing manual classification conflicts with the new automatic evidence;
* FINAL validation identifies a likely character mismatch.

Review Queue is a user-decision mechanism, not an extension of automatic candidate generation.

A user's explicit character or destination decision has priority for the affected classification/placement context according to DOC-013.

---

# 16. FINAL Validation

Character Analysis may inspect FINAL in read-only validation scope when configured.

For example:

```text
FINAL/Anime/Genshin Impact/Furina/image.jpg
        ↓
Character Analysis
        ↓
possible mismatch: Nahida
```

The module must not move the file merely because it produced such a result.

The result may enter Review Queue or another documented validation workflow.

FINAL is not assumed to be error-free, but correction remains subject to user decision and applicable access policy.

---

# 17. AI / FINAL Placement Boundary

Character Analysis does not create FINAL directories and does not itself perform placement.

A downstream authorized processing workflow may use character results to organize the AI/transition workspace.

AI may contain newly created character or universe working directories when the relevant configured workflow permits their creation and its applicable threshold is met, even when the corresponding destination does not yet exist in FINAL.

FINAL destinations must already exist in Collection Definition or be explicitly selected/created by the user.

A character candidate from Character Analysis is never by itself a command to create a FINAL directory.

---

# 18. Interaction with Universe Analysis

Universe Analysis is the preferred source of universe candidates when available because it can substantially reduce the search space.

Character Analysis may consume:

```text
Universe candidate
Universe confidence
Universe analysis/model version
```

through the database.

Character Analysis should not modify Universe Analysis results.

A character result may remain valid even when a universe has multiple candidates, provided the supporting evidence and selected character result are independently sufficient.

Failure to identify a character must never invalidate a universe result.

---

# 19. Multiple Characters

The initial model permits multiple candidates for a file.

A future implementation may distinguish:

```text
primary character
secondary character
background character
multiple-character scene
```

Such distinctions are not required for the first implementation.

The module must not force a single character when the evidence supports multiple plausible candidates.

---

# 20. Design Philosophy

Character Analysis is a probabilistic information provider.

Its purpose is to refine semantic understanding after or alongside universe analysis without turning analysis into an irreversible filesystem action.

The module should optimize for useful evidence and low false-positive rates rather than forcing a complete character assignment for every image.

---

# 21. Future Extensions

Possible future capabilities include:

* multi-character scene analysis;
* background character detection;
* pose/context analysis;
* alternate outfit recognition;
* variant-aware character identification;
* improved character catalogue handling;
* relationship/context analysis.

Such features remain in this module while they are still logically part of character identification. A genuinely independent analytical function may become a separate module.

---

# 22. Acceptance Criteria

The module is considered compliant when it can:

* identify plausible fictional character candidates;
* preserve multiple candidates when useful;
* use Universe Analysis data through the database without a runtime dependency;
* operate independently when its configured strategy permits it;
* support configurable storage and assignment thresholds;
* associate results with the correct SHA512 binary identity;
* reprocess when the relevant module/model/rule/catalogue version requires it;
* preserve manual user decisions;
* support FINAL validation without directly modifying FINAL;
* support AI/transition workflows without automatically creating FINAL directories;
* recover from per-file failures where safe;
* operate efficiently on large collections.

---

# End of DOC-107
