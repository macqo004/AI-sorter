DOC-005A
Database Schema
Part A – Data Model

Project: AI Image Framework (working title)

Version: 0.1

Status: Draft

Depends on:

DOC-001
DOC-002
DOC-003
DOC-004
1. Purpose

This document defines the logical data model used by the entire framework.

Unlike previous documents, this specification describes the actual entities that exist inside the system.

The database is designed around the lifecycle of an image, not around software modules.

2. Design Philosophy

The database MUST answer questions such as:

What is this image?
Where is it now?
Where has it been?
What has been detected?
What decisions were made?
What did the user change?
What can the AI learn?

The database MUST NOT be organized around implementation details.

3. Core Principle

Everything revolves around a single entity:

Image

Everything else describes that image.

Not the opposite.

4. Primary Entities

The first version of the framework defines the following entities.

Image

↓

File

↓

Analysis

↓

Classification

↓

Event

↓

Module

↓

Tag

Future versions may extend this model.

Existing entities MUST remain compatible.

5. Entity: Image

Image is the permanent identity of a visual object.

It represents the image independently of:

filename
folder
extension
current location

An Image exists only once.

It never changes identity.

Image Responsibilities

Image stores information that never changes.

Examples:

internal ID
SHA-512
creation timestamp inside database

Nothing related to classification belongs here.

6. Entity: File

A File represents the current physical representation of an Image.

Unlike Image, File may change.

Examples:

filename
extension
folder
size
modification date

Moving a file updates File.

It does NOT create another Image.

7. Entity: Analysis

Analysis stores facts discovered by processing modules.

Examples:

B&W

Screenshot

IRL

Resolution

Aspect Ratio

Transparency

Animation

Analysis contains observations.

It never contains decisions.

8. Entity: Classification

Classification stores interpretations.

Examples:

Universe

Character

Theme

Holiday

Cosplay

Group Image

Unlike Analysis, Classification may change.

User corrections are expected.

9. Entity: Event

Events describe something that happened.

Examples:

Scanned

Moved

Renamed

Accepted

Rejected

Deleted

Returned to TODO

Events are immutable.

An Event is never modified.

New events are appended.

10. Entity: Module

Every action inside the framework originates from a module.

Examples:

Scanner

B&W

Mover

Rename

Universe Detector

Module information allows:

auditing
debugging
performance measurements
reproducibility
11. Entity: Tag

Tags describe semantic information.

Examples:

Christmas

School Uniform

Bikini

Halloween

Night

Rain

Smile

Tags are independent from universe detection.

12. Entity Relationships

The conceptual model is intentionally simple.

Image

│

├──── File

│

├──── Analysis

│

├──── Classification

│

├──── Event

│

└──── Tag

Every entity references Image.

Image references nothing.

It is the root.

13. Immutable Data

The following information MUST never change.

Internal Image ID
SHA-512
Database creation timestamp

If any of these change, a new Image must be created.

14. Mutable Data

The following data MAY change.

Filename

Directory

Extension

Classification

User decisions

Tags

These updates do not change Image identity.

15. Historical Data

History is never overwritten.

Examples.

Wrong:

Character

Old

↓

New

Correct:

Character predicted

↓

User rejected

↓

Character corrected

The database records history.

It does not erase it.

16. Event Sourcing

Where practical, changes SHOULD be represented as events instead of destructive updates.

Advantages:

complete history
debugging
learning
rollback
statistics
17. Future Compatibility

The model intentionally reserves space for future entities.

Possible examples:

OCR

Color Palette

Pose

Clothing

Artist

Quality Score

Duplicate Group

Embedding Vector

No redesign of Image should ever be required.

18. Artificial Intelligence

AI modules never own data.

They produce:

classifications
confidence
explanations (future)

Human decisions always have higher priority.

19. Scalability

The model is expected to operate on collections containing:

Initial target:

5 000 000 images

Future target:

20 000 000+

Entity relationships must remain efficient at this scale.

20. Summary

The framework stores knowledge about Images.

Everything else describes Images.

This principle must never be violated.

End of DOC-005A