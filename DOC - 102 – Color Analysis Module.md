# DOC-102

# Color Analysis Module

**Project:** AI Image Collection Management System

**Document:** DOC-102

**Module:** Color Analysis

**Version:** 2.1

**Status:** Design Specification

**Depends on:**

DOC-005
DOC-007
DOC-008
DOC-010
DOC-011
DOC-012
DOC-014
DOC-205

---

# 1. Purpose

The Color Analysis module extracts basic global colour characteristics from image files and stores the results in the shared database.

The module is an information provider. It does not decide where a file belongs, perform semantic classification or modify the collection structure.

---

# 2. Responsibilities

The module shall:

* analyse global colour characteristics;
* determine whether an image satisfies the project's black-and-white criteria;
* determine whether an image is predominantly black-and-white;
* determine whether an image is monochrome;
* determine whether an image is predominantly monochrome;
* write its analysis results to the shared database;
* record module execution and errors according to the common project standards.

The module shall not:

* identify universes or characters;
* detect screenshots, memes, IRL content or other semantic categories owned by other modules;
* move or rename files;
* create or modify collection directories;
* modify user classifications or manual decisions owned by other workflows.

---

# 3. Module Independence

Color Analysis is an independently executable module.

It does not invoke other modules and does not require another module process to remain active.

The module reads the current database state when it runs and writes its own results back to the database.

For example, the following execution history is valid:

```text
Scanner
    ↓
Database

IRL Analysis × 5
Screenshot Analysis × 2
Color Analysis × 10
IRL Analysis × 1
```

The order and number of executions of other modules do not impose an execution schedule on Color Analysis.

The module normally requires the file to have a valid SHA512-based identity in the database. Scanner is responsible for discovering new files and creating such identities; Color Analysis does not invoke Scanner automatically.

---

# 4. Scope

The module evaluates global visual colour characteristics only.

The following questions are outside its scope:

```text
What character is shown?
What universe is represented?
Is the image a screenshot?
Is the image a reaction image or meme?
Is the image IRL?
Is the image AI-generated?
Where should the file be stored?
```

---

# 5. Input

The module processes eligible file records known to the database.

Required logical information includes:

```text
SHA512
current filesystem state
image format
image dimensions
```

An internal `file_id` may be used for database relationships where the implementation provides one.

The module may read the image from the filesystem when required for decoding or pixel analysis. Such filesystem access is subject to the configured access policy.

---

# 6. Output

Color Analysis writes **Analysis Result** records as defined by DOC-005.

The initial feature set is:

```text
IS_BW
IS_MOSTLY_BW
IS_MONOCHROME
IS_MOSTLY_MONOCHROME
```

Each result may include supporting metadata such as:

```text
file identity
module
feature
value
confidence where applicable
execution reference
analysis/model/rule metadata where useful for diagnostics
creation time
```

Such metadata is informational. It is not used as an automatic stale-result mechanism. Module-result lifecycle and cleanup are governed by DOC-014 and DOC-205.

The module owns the results that it produces. It must not overwrite analysis results belonging to another module.

Other modules may consume these results through the shared database without communicating directly with Color Analysis.

---

# 7. Definitions

## 7.1 Black-and-White

An image is considered black-and-white when its pixels satisfy the project's configured black-and-white criteria.

The exact numerical criteria are an implementation/configuration concern and may be refined without changing the logical feature definition.

## 7.2 Mostly Black-and-White

An image is mostly black-and-white when it does not fully satisfy the black-and-white definition but the configured analysis determines that the image is predominantly black-and-white.

Examples may include:

* a grayscale illustration containing a small coloured element;
* a manga page with a limited coloured area;
* an otherwise monochrome image containing a coloured signature.

## 7.3 Monochrome

An image is monochrome when its visual content is predominantly based on a single colour family.

Monochrome is not limited to grayscale.

Examples include:

```text
sepia
blue monochrome
green monochrome
red monochrome
```

## 7.4 Mostly Monochrome

An image is mostly monochrome when one colour family clearly dominates while a limited amount of secondary colour information remains.

The distinction between `IS_MONOCHROME` and `IS_MOSTLY_MONOCHROME` is determined by the configured analysis criteria.

---

# 8. Confidence

The module may provide confidence for results when its analysis method supports a meaningful confidence value.

Confidence expresses the module's certainty about the analysis result.

Confidence must not be confused with the semantic meaning of the feature itself.

For example:

```text
IS_MOSTLY_BW = TRUE
confidence = 0.98
```

means the module is highly confident that the image satisfies the `mostly black-and-white` criterion. It does not mean that the image is 98% black-and-white in a semantic sense unless the implementation explicitly defines confidence that way.

---

# 9. Processing Rules

A module execution processes files whose current database state indicates that a Color Analysis result is required for the selected execution scope.

For the current binary identity, identified by SHA512, an existing current result may be reused rather than recalculated unnecessarily.

A change to the following does **not** automatically invalidate existing results or trigger a reprocessing run:

* module implementation version;
* analysis/model version;
* analysis rules;
* thresholds or configuration;
* other internal implementation changes.

If the user wants the collection to be recalculated using a changed implementation or rules, the user explicitly uses **DOC-205 – Module Result Cleanup Utility** to clear the Color Analysis results and then starts Color Analysis again.

A binary-content change that results in a different SHA512 is different: the new binary identity requires its own Color Analysis result.

A rename or move that does not change SHA512 does not invalidate the Color Analysis result merely because the path changed.

---

# 10. SHA512 and Binary Version Changes

Analysis results belong to a specific binary file identity.

Example:

```text
SHA512 = AAAA
    ↓
Color Analysis result
```

If the binary content changes:

```text
SHA512 = BBBB
```

the new binary identity requires a new Color Analysis result.

The result belonging to `AAAA` remains associated with the historical `AAAA` identity and must not be silently reused as the result for `BBBB`.

A rename or move that does not change SHA512 does not invalidate the Color Analysis result merely because the path changed.

---

# 11. Database Access

The module reads information required for its own operation from the shared database and filesystem.

It writes only data belonging to Color Analysis and its execution/logging responsibilities.

Logical database concepts include:

```text
File
Analysis Result
Module
Module Execution
```

The module shall not modify Scanner-owned filesystem synchronization state merely as a side effect of analysis.

---

# 12. Threading and Resource Usage

The module shall support parallel processing where practical.

The worker count should be configurable when exposed by the implementation.

The module may use additional RAM or CPU resources when this provides a meaningful performance benefit, while respecting configured/system resource limits.

Parallel processing must preserve database consistency and must not produce duplicate or conflicting current results for the same analysis context.

---

# 13. Error Handling

If an image cannot be analysed, the module shall:

* record the error according to DOC-011;
* continue processing other eligible files whenever safe;
* avoid storing a partially computed result as a valid current result.

Typical recoverable errors include:

* unsupported image encoding;
* corrupted image;
* filesystem read failure;
* insufficient resources for the current item.

A database failure that prevents safe persistence may stop the execution.

---

# 14. Logging

Every execution shall create the module execution record and logs required by DOC-007 and DOC-011.

A summary should include, where applicable:

```text
files considered
files processed
files skipped
files already current
errors
duration
```

Detailed errors should identify the affected file identity/path where available.

---

# 15. Performance Requirements

The module is intended for collections containing millions of images.

Implementation should favour efficient analysis methods and avoid unnecessary full-image work when existing valid results can be reused.

The module should not require the entire collection to be loaded into memory.

Parallel processing should be used where it provides meaningful performance improvement.

---

# 16. Interaction with Other Modules

Color Analysis does not invoke any other module.

Its relationship with the rest of the system is:

```text
Scanner
   ↓
Database
   ↓
Color Analysis
   ↓
Database
   ↓
other modules may consume Color Analysis results
```

Possible consumers include later filtering, classification or sorting modules, but Color Analysis does not require those modules to be present or running.

---

# 17. Design Philosophy

Color Analysis deliberately separates observation from interpretation.

For example, this module may determine:

```text
IS_BW = TRUE
```

but it does not decide:

```text
"therefore this is a manga"
```

or:

```text
"therefore move this file to Themes"
```

Those decisions belong to other modules and workflows.

---

# 18. Future Extensions

Possible future additions include:

* dominant colour estimation;
* colour palette extraction;
* histogram data;
* brightness estimation;
* contrast estimation;
* saturation analysis;
* additional colour-distribution metrics.

Such features should remain within this module only when they share the same logical responsibility and do not create an unnecessarily broad analysis component.

---

# 19. Acceptance Criteria

Color Analysis is considered compliant when it can:

* process supported image formats;
* produce the four defined colour-analysis results;
* associate every result with the correct SHA512-based binary identity;
* reuse current valid results when applicable;
* avoid automatic invalidation solely because the module/model/rules changed;
* support full recalculation through the user-controlled DOC-205 cleanup workflow followed by a new module execution;
* invalidate results naturally when the binary identity changes;
* write results through the shared database;
* operate independently of other module executions;
* continue after recoverable per-file failures;
* support multi-million-image collections without requiring the entire collection in memory;
* generate execution records and logs according to the common project standards.

---

# End of DOC-102
