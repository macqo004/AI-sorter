# DOC-105

# IRL Analysis Module

**Project:** AI Image Collection Management System

**Document:** DOC-105

**Module:** IRL Analysis

**Version:** 2.1

**Status:** Design Specification

**Depends on:** DOC-005, DOC-007, DOC-008, DOC-010, DOC-011, DOC-012, DOC-013, DOC-014, DOC-205

---

# 1. Purpose

The IRL Analysis module determines whether an image most likely represents real-world subject matter rather than artwork or a digitally created illustration.

It provides analysis results for other modules and does not itself move, rename or delete files.

# 2. Responsibilities

The module shall analyse visual evidence associated with real-world imagery, provide confidence where meaningful, write results to the shared database and preserve the distinction between automatic analysis and user decisions.

It shall not identify anime characters/universes, perform Cosplay Analysis as its primary responsibility, modify folder structures or overwrite other modules' results/user decisions.

# 3. Scope

Typical positive examples include people, animals, vehicles, buildings, landscapes, food, products, interiors and outdoor photographs. Typical negative examples include anime artwork, manga, fanart, CG illustrations, digital paintings and stylized game artwork.

# 4. Input

Required information includes SHA512, current filesystem state, image format and dimensions where available. A valid database file identity is required. The module may access the corresponding file.

# 5. Output

Initial features may include:

```text
IS_IRL
LOOKS_PHOTOGRAPHIC
LOOKS_ILLUSTRATED
```

Results may include file identity, module, feature, value, confidence and diagnostic execution/model information. Diagnostic metadata is informational and does not automatically invalidate results.

# 6. Definitions

**IRL** means an image primarily representing people, objects or environments existing in the physical world. It does not require a camera photograph.

**Uncertainty** is a normal analysis outcome when evidence is insufficient for a reliable automatic decision.

# 7. Confidence

Confidence describes the strength of the module's evidence and is not a user decision. Low confidence does not authorize guessing; downstream workflows use their configured thresholds and Review Queue rules.

# 8. Processing Rules

IRL Analysis may be executed repeatedly and independently.

A valid current result for the same SHA512 may normally be reused.

A change to the module implementation, model, analysis rules, thresholds or configuration does **not** automatically clear existing IRL results and does not automatically trigger reprocessing.

When the user wants complete recalculation with changed logic, the user shall use **DOC-205 – Module Result Cleanup Utility** to clear IRL results and then run IRL Analysis again.

A path or filename change without a SHA512 change does not by itself invalidate the result. A changed SHA512 means a new binary identity and requires a new result.

# 9. Processing Scope

Scope is configurable and may include configured source roots, AI/transition workspace, selected FINAL validation roots or user-selected subsets. Physical names such as TODO, AI and FINAL are not hard-coded.

# 10. Interaction with Other Modules

IRL Analysis communicates through the shared database and does not invoke other modules. It may consume documented supporting results from other modules without creating a runtime dependency.

# 11. Database Access

The module reads the current database and corresponding files and writes only IRL analysis results and execution-related state. It must not overwrite Scanner state, unrelated results or user decisions.

# 12. Performance and Resource Usage

The module shall be suitable for collections containing millions of images, use available CPU/GPU resources efficiently within configured limits, avoid unnecessary work and avoid requiring the whole collection in memory.

# 13. Threading

Parallel execution is supported. Worker count and resource limits are configurable.

# 14. Error Handling

Per-file analysis failures are logged and should not stop unrelated work where safe. Incomplete or invalid results must not be published as valid current results. Analysis uncertainty is not a processing error.

# 15. Logging

Each execution creates a Module Execution record and summary log according to DOC-007 and DOC-011.

# 16. Design Philosophy

IRL Analysis is an information provider. It should minimize false positives and prefer uncertainty to unjustified classification. It does not decide whether an image should be removed, moved to AI or moved to FINAL.

# 17. Relationship with Other Analysis

Color Analysis, Screenshot Analysis or other documented results may be consumed through the database when useful. No analysis module directly invokes another.

# 18. Review Queue and User Decisions

Downstream workflows may create Review Queue items when uncertainty requires explicit user intervention. A later user correction has priority over later automatic observations for the protected decision context. IRL Analysis must not undo a user-selected destination merely because later model output differs.

# 19. FINAL and AI Handling

IRL Analysis does not manage final directory structures. FINAL destinations come from Collection Definition or explicit user action. AI workspace creation belongs to the responsible authorized workflow.

# 20. Future Extensions

Possible extensions include improved photographic/illustration discrimination, specialized scene recognition, source-specific photography detection and improved mixed-content handling.

# 21. Acceptance Criteria

The module is compliant when it can distinguish likely real-world imagery with documented confidence, associate results with SHA512, reuse current results, avoid automatic invalidation after model/rule changes, support full recalculation through DOC-205 followed by a new execution, operate independently, continue after recoverable errors and communicate through the shared database.

---

# End of DOC-105
