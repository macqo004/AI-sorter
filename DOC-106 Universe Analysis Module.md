DOC-106
Universe Analysis Module

Project: AI Image Framework (working title)

Document: DOC-106

Module: Universe Analysis

Version: 1.0 Draft

Status: Draft

Depends on

DOC-001
DOC-002
DOC-003
DOC-004
DOC-005
DOC-006
DOC-101
1. Purpose

The Universe Analysis module determines the fictional universe or franchise most likely represented by an image.

Unlike previous modules, Universe Analysis may produce multiple candidates ranked by confidence.

The module enriches the database with candidate observations.

The module performs no file operations and makes no sorting decisions.

2. Responsibilities

The module SHALL:

analyse fictional universes represented by an image;
assign confidence values;
rank candidate universes;
store candidate observations.

The module SHALL NOT:

identify individual characters;
determine image quality;
rename files;
move files;
modify folder structures.
3. Scope

The module attempts to recognise the fictional universe represented by an image.

Typical examples include:

Genshin Impact
Honkai: Star Rail
Zenless Zone Zero
Fate
Touhou
Azur Lane
Blue Archive
Kantai Collection
Girls' Frontline

The supported universe list is implementation-defined and may evolve over time.

4. Input

The module reads:

Image
File
Scanner metadata
Current SHA-512

Additionally, the module may consume observations produced by previous analysis modules.

Examples include:

Color Analysis
Screenshot Analysis
Reaction Analysis
IRL Analysis

Consumption of previous observations is optional.

The module remains independently executable.

5. Output

The module writes Candidate Observations.

Each candidate contains:

ImageID
ModuleID
Candidate
Confidence
Rank
Timestamp

Multiple candidates may be stored for the same image.

6. Candidate Selection

Candidates shall be ordered by descending confidence.

Only candidates meeting or exceeding the configured confidence threshold shall be stored.

Default threshold:

0.50

The threshold shall be configurable.

The module shall not artificially limit the number of stored candidates.

7. Definitions
Universe

A fictional franchise, game, anime, manga, visual novel or other identifiable fictional setting.

Candidate

A possible universe assigned to an image together with a confidence score.

Candidates represent probabilities rather than final decisions.

Confidence

The estimated probability that the image belongs to the specified universe.

The confidence calculation method is implementation-defined.

8. Processing Rules

Each SHA-512 shall be analysed only once.

Existing candidate observations for the current SHA-512 shall prevent unnecessary reprocessing.

If the SHA-512 changes, previous candidate observations become obsolete and shall be recalculated.

9. Database Access

The module reads:

Image
File
Module
Observation

The module writes:

CandidateObservation

The module shall never modify observations created by other modules.

10. Scan Scope

The module shall support configurable scan scope.

Typical examples include:

Anime collection;
TODO collection;
User-selected directory;
Database subset.

The module shall not require processing of IRL images.

11. Performance Requirements

The module shall support very large collections.

Repeated analysis of unchanged SHA-512 values shall be avoided.

The implementation should favour efficient batch inference.

12. Threading

Parallel execution shall be supported.

Worker thread count shall be configurable.

13. Error Handling

If analysis fails:

processing continues;
the error is logged;
incomplete candidate lists shall not be stored.
14. Logging

Each execution produces a summary log.

Example:

Universe Analysis

Started:
2026-07-18 16:00

Processed:
92,134

Skipped:
3,921,518

Errors:
4

Duration:
00:18:52

Detailed errors follow the summary.

15. Interaction with Other Modules

The module depends only on Scanner.

It may optionally consume observations produced by previous modules.

The module shall never invoke another module directly.

Future modules, especially Character Analysis, are expected to consume Universe candidates.

16. Design Philosophy

The module is not expected to make perfect decisions.

Its role is to provide a ranked list of plausible universes.

Later modules may use these candidates to reduce their own search space.

The module shall prefer uncertainty over false certainty.

17. Future Extensions

The following capabilities are intentionally excluded from Version 1:

scene recognition;
event recognition;
costume recognition;
crossover detection;
multiple-universe composition analysis;
fanart source identification.
18. Acceptance Criteria

The module shall be considered complete when it can:

identify fictional universes;
produce ranked candidate lists;
respect configurable confidence thresholds;
support configurable scan scope;
skip unchanged SHA-512 values;
recover gracefully from processing errors;
operate efficiently on large image collections.
End of DOC-106