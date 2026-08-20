# DOC-108

# Theme Analysis Module

**Project:** AI Image Collection Management System

**Document:** DOC-108

**Module:** Theme Analysis

**Version:** 2.3

**Status:** Design Specification

**Depends on:** DOC-005, DOC-007, DOC-008, DOC-010, DOC-011, DOC-012, DOC-013, DOC-014, DOC-205, DOC-302

---

# 1. Purpose

Theme Analysis detects broad visual themes present within an image.

Examples include Bikini, Christmas, Halloween, Maid, Beach, School Uniform and Kimono. The list is illustrative and not a hard-coded project taxonomy.

Themes have a special architectural role: they are a **fallback organisational classification** used when an image cannot currently be placed into an appropriate higher-priority primary collection tree.

# 2. Design Philosophy

Themes answer what visual theme or subject matter is present, rather than who is shown or which primary collection the image belongs to.

A theme is metadata. It is not by itself a final filesystem placement command.

# 3. Responsibilities

Theme Analysis shall analyse visual themes, assign confidence where meaningful, support multiple themes per file, write results to the shared database and preserve the distinction between automatic analysis and user decisions.

It shall not move/rename files, create FINAL directories, determine primary placement, identify Universe/Character/Monster Girl species as its primary responsibility or invoke other modules.

# 4. Input

Required information includes SHA512, current filesystem state, image format and dimensions where available. Supporting analysis results may be consumed through the database.

# 5. Output

Each detected theme creates an Analysis Result containing at least file identity, module, theme value, confidence where applicable and execution/diagnostic metadata. Diagnostic model/rule information is informational and does not automatically invalidate a result.

# 6. Theme Categories

Themes are intentionally broad and expandable. Categories may include clothing, seasonal, environment and general concepts. Definitions may evolve through configuration/model updates without changing the architectural role of Themes.

# 7. Theme Confidence

Confidence describes the strength of evidence that a theme is present. Low confidence must not automatically cause physical sorting.

# 8. Processing and Reprocessing

Theme Analysis may be executed repeatedly and independently.

Existing valid results for the same SHA512 may be reused where appropriate.

A change to the module implementation, model, theme catalogue, rules, thresholds or configuration does **not** automatically clear Theme results and does not automatically trigger reprocessing.

When the user wants a complete recalculation using changed logic, the user shall use **DOC-205 – Module Result Cleanup Utility** to clear Theme Analysis results and then run Theme Analysis again.

A rename or move without a SHA512 change does not by itself invalidate Theme results. A changed SHA512 creates a new binary identity requiring new analysis.

# 9. Primary Collection Trees

A **primary collection tree** is a user-defined collection root intended to be a main organisational destination. Examples such as Anime, Monster Girls and Western Animation are illustrative only.

All configured primary collection trees have higher organisational priority than the Themes fallback:

```text
Primary Collection Tree(s)
        ↓
Themes fallback
```

# 10. Theme as Fallback Organisation

Theme-based physical organisation is appropriate when no applicable higher-priority primary collection destination is currently available.

The Theme destination must be valid according to Collection Definition and access policy.

# 11. Promotion from Themes to a Primary Collection

If later analysis establishes a valid higher-priority primary classification, an authorized workflow may remove the file from its Theme fallback location and place it into the appropriate primary collection tree. The physical file is moved, not copied.

Theme Analysis itself never performs the move.

# 12. No Primary Destination Available

A valid Theme result with no usable primary destination is a normal state, not an analysis failure. The file may remain in Theme fallback until a better primary destination becomes valid.

# 13. Manual Decisions

User decisions are stored separately from automatic analysis and must not be silently overwritten. A manual placement decision has priority over later automatic placement suggestions for the relevant context until changed by the user.

# 14. Performance and Resource Usage

Theme Analysis should support GPU acceleration where available, CPU fallback, batch processing, multi-threading and incremental processing without requiring the entire collection in memory.

# 15. Logging

Each execution shall create a Module Execution record and summary log according to DOC-007 and DOC-011.

# 16. Interaction with Other Modules

Theme Analysis communicates through the shared database. AutoSort is responsible for applying the configured priority between primary collection trees and Theme fallback when determining physical placement.

# 17. FINAL and AI Handling

Theme Analysis does not create FINAL directories. FINAL destinations are defined by Collection Definition. AI/transition workspaces may be dynamically extended by authorized workflows when their configured criteria are met.

# 18. Future Extensions

Possible future additions include Theme hierarchy, Theme groups, user-defined themes, theme synonyms, confidence calibration and multi-model voting.

# 19. Acceptance Criteria

Theme Analysis is compliant when it can detect broad themes, support multiple themes, store confidence, associate results with SHA512, operate independently, keep Themes subordinate to all configured primary trees, support promotion through authorized workflows, avoid automatic invalidation after model/rule changes, support full recalculation through DOC-205 followed by a new execution, and never create or modify FINAL structure as part of analysis.

---

# End of DOC-108
