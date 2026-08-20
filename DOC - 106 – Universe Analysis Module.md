# DOC-106

# Universe Analysis Module

**Project:** AI Image Collection Management System

**Document:** DOC-106

**Module:** Universe Analysis

**Version:** 2.2

**Status:** Design Specification

**Depends on:** DOC-005, DOC-007, DOC-008, DOC-010, DOC-011, DOC-012, DOC-013, DOC-014, DOC-205, DOC-302

---

# 1. Purpose

The Universe Analysis module determines which fictional universe, franchise or other identifiable fictional setting is most strongly represented by an image.

It writes candidate classifications to the shared database and does not itself perform physical sorting or FINAL placement.

The module may produce multiple ranked candidates for one file.

# 2. Responsibilities

The module shall analyse fictional-universe evidence, produce candidates, assign confidence and rank, write results to the shared database and preserve the distinction between automatic analysis and user decisions.

It shall not identify individual characters as its primary responsibility, move/rename/delete files, create/modify FINAL directory structure, silently overwrite user decisions or invoke another module.

# 3. Scope

Supported universes are implementation/configuration data and are not a hard-coded project taxonomy. The module may analyse content belonging to universes not currently represented in FINAL.

# 4. Module Independence

Universe Analysis is independently executable once a valid database identity exists. Scanner must have discovered the file first, but does not need to be running. Other modules may provide supporting information through the database without creating process dependencies.

# 5. Input

Required information includes SHA512, current filesystem state, image format and dimensions where available. Optional supporting Analysis Results may include Color, Screenshot, Reaction, IRL and Cosplay results.

# 6. Output

Candidates may include:

```text
file identity / SHA512
module
classification type = UNIVERSE
candidate value
confidence
rank
execution reference
analysis/model/rule metadata where useful for diagnostics
```

Diagnostic version information does not automatically control result validity.

# 7. Candidate Ranking and Thresholds

Candidates are ranked by confidence or another documented score. Configurable thresholds may determine whether candidates are worth storing or eligible for later workflow use.

A collection-level count threshold may authorize an AI workspace for an emerging universe. This does not authorize creation of a FINAL directory.

# 8. AI / Transition Workspace Integration

The AI/transition tree is a working area and is not limited to universes already represented in FINAL.

When configured criteria are met, an authorized workflow may create an AI workspace such as:

```text
AI/Ben 10/
```

The analysis result itself does not perform the filesystem operation.

# 9. FINAL Destination Rules

Universe Analysis shall never create new FINAL collection directories merely because a universe is detected. Final placement requires an existing valid Collection Definition destination and an authorized workflow satisfying applicable review/user-decision rules.

# 10. Processing and Reprocessing

Universe Analysis may be executed repeatedly and independently.

Existing valid results for the same SHA512 may be reused when appropriate.

A change to module implementation, model, rule set, universe catalogue, threshold or configuration does **not** automatically clear results and does not automatically trigger a new analysis run.

When the user wants a complete recalculation using changed universe logic, the user shall use **DOC-205 – Module Result Cleanup Utility** to clear Universe Analysis results and then run Universe Analysis again.

A path or filename change without a SHA512 change does not by itself invalidate universe analysis. A changed SHA512 creates a new binary identity whose analysis is independent.

# 11. Manual User Decisions

A Universe Analysis result is an automatic suggestion unless converted into a user decision. Manual correction is authoritative for the affected classification/placement context and later automatic runs must not silently replace it.

# 12. Review Queue Integration

Review Queue may be used for insufficient confidence, multiple plausible candidates, destination approval, classification conflicts or FINAL validation cases. Review Queue is the user-decision mechanism and not a second automatic classification engine.

# 13. FINAL Validation

Universe Analysis may inspect FINAL in read-only validation scope. A detected mismatch may become a Review Queue item or report; the module must not move the file directly.

# 14. Multiple Candidates

Useful uncertainty should be preserved when more than one universe is plausible. The module must not manufacture artificial certainty merely to produce one answer.

# 15. Database Access

The module reads File, Module, Analysis Results and relevant Collection Definition/configuration state. It writes Universe Analysis Results and execution state. Persistent module-to-module information exchange occurs through the database.

# 16. Performance Requirements

The module shall support large collections, batch inference, configurable workers, reuse of existing valid results and optional cheaper supporting evidence before expensive inference. The entire collection must not be required in RAM.

# 17. Threading and Resource Usage

Parallel execution shall be supported with configurable worker and resource limits.

# 18. Error Handling

Per-file analysis failures are logged and should not stop unrelated files where safe. Incomplete candidate results must not be published as valid.

# 19. Logging

Each execution creates a Module Execution record and summary log according to DOC-007 and DOC-011.

# 20. Interaction with Other Modules

Universe Analysis never invokes another module directly. Character Analysis may consume its results through the database. Other consumers may use the results without Universe Analysis remaining active.

# 21. Design Philosophy

Universe Analysis is a probabilistic information provider. It should prefer uncertain results over confidently wrong classifications and remain useful even when the detected universe has no FINAL representation.

# 22. Future Extensions

Possible future capabilities include improved crossover handling, scene context, source-art recognition, model ensembles, improved calibration and universe catalogue management.

# 23. Acceptance Criteria

The module is compliant when it can identify plausible universes, preserve multiple candidates, operate independently, use configurable thresholds, support AI workspaces for emerging universes, associate results with SHA512, avoid automatic invalidation after model/rule changes, support full recalculation through DOC-205 followed by a new execution, preserve manual decisions, validate FINAL without direct modification and operate efficiently on large collections.

---

# End of DOC-106
