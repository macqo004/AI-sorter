DOC-105
IRL Analysis Module

Project: AI Image Framework (working title)

Document: DOC-105

Module: IRL Analysis

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

The IRL Analysis module determines whether an image most likely represents the real world rather than artwork or computer-generated illustration.

The module enriches the database with IRL-related observations.

The module performs no file operations and makes no sorting decisions.

2. Responsibilities

The module SHALL:

analyse images for real-world characteristics;
distinguish likely photographs from illustrations;
assign confidence values;
write observations to the database.

The module SHALL NOT:

classify anime;
identify characters;
identify universes;
detect cosplay;
move files;
rename files;
modify folder structures.
3. Scope

The module determines whether an image most likely belongs to the category of real-world imagery.

Typical positive examples include:

people;
animals;
vehicles;
buildings;
landscapes;
food;
products;
interior photographs;
outdoor photographs.

Typical negative examples include:

anime artwork;
manga;
fanart;
CG illustrations;
stylized game artwork;
digital paintings.

The module intentionally does not distinguish between individual IRL categories.

4. Input

The module reads:

Image
File
Scanner metadata
Current SHA-512

Image decoding is performed only when required.

5. Output

The module produces Observations.

Initial feature set:

IsIRL

LooksPhotographic

LooksIllustrated

NeedsManualReview

Each Observation shall contain:

ImageID
ModuleID
Feature
Value
Confidence
Timestamp
6. Definitions
IRL

An image primarily representing objects, people or environments existing in the physical world.

Photographic Appearance

Visual characteristics commonly associated with photographs.

The exact detection method is implementation-defined.

Illustrated Appearance

Visual characteristics commonly associated with manually or digitally created artwork.

Manual Review

A state indicating that the module cannot determine the image category with sufficient confidence.

Manual Review is not an error.

It represents intentional uncertainty.

7. Confidence

Every Observation shall include a confidence value.

Confidence reflects the probability that the image belongs to the IRL category.

The calculation method is implementation-defined.

8. Processing Rules

Each SHA-512 shall be analysed only once.

Existing observations for the same SHA-512 shall prevent unnecessary reprocessing.

If the SHA-512 changes, previous observations produced by this module become obsolete and shall be recalculated.

9. Database Access

The module reads:

Image
File
Module

The module writes:

Observation

The module never modifies observations created by other modules.

10. Scan Scope

The module shall support configurable scan scope.

The scan scope determines which images are eligible for analysis.

Examples include:

Entire TODO tree

Entire database

Specific directory

Specific collection

User-selected subset

Scope selection is provided externally.

The module shall not hardcode directory names.

11. Performance Requirements

The module shall support collections containing millions of images.

Repeated analysis of unchanged SHA-512 values shall be avoided.

The implementation should favour efficient inference suitable for large datasets.

12. Threading

Parallel execution shall be supported.

Worker thread count shall be configurable.

13. Error Handling

If an image cannot be analysed:

processing shall continue;
the error shall be logged;
incomplete observations shall not be stored.

Recoverable failures include:

corrupted image;
unsupported encoding;
temporary read failure.
14. Logging

Each execution produces a summary log.

Example:

IRL Analysis

Started:
2026-07-18 13:00

Processed:
112,438

Skipped:
4,812,001

Errors:
7

Duration:
00:12:41

Detailed errors follow the summary.

15. Interaction with Other Modules

The module depends only on Scanner.

It is independent of:

Color Analysis
Screenshot Analysis
Reaction Image Analysis
Universe Analysis
Character Analysis

Other modules may consume its observations.

The module shall never invoke another module directly.

16. Design Philosophy

The IRL Analysis module is a knowledge provider.

It does not decide where an image belongs.

It provides observations that may later be combined with information from other modules.

When confidence is insufficient, the module shall prefer uncertainty over incorrect classification.

17. Future Extensions

The following capabilities are intentionally excluded from Version 1:

cosplay detection;
celebrity recognition;
face identification;
age estimation;
object classification;
scene classification;
OCR;
NSFW detection.

These capabilities may be implemented by dedicated modules.

18. Acceptance Criteria

The module shall be considered complete when it can:

distinguish likely real-world images from artwork;
assign confidence values;
support configurable scan scope;
write observations to the database;
skip unchanged SHA-512 values;
recover gracefully from processing errors;
operate efficiently on multi-million image collections.
End of DOC-105