DOC-005B
Database Schema
Part B – Entity Definitions

Project: AI Image Framework (working title)

Version: 0.1

Status: Draft

Depends on:

DOC-005A
1. Entity: Image
Purpose

The Image entity represents the logical identity of an image known to the framework.

It is the root entity of the database.

Every other entity references Image.

The Image entity MUST NOT contain information related to current file location or AI classification.

Ownership

Created by:

Scanner

Modified by:

Never (except controlled database maintenance)
Fields
ImageID

Type:

INTEGER (64-bit)

Purpose:

Permanent internal identifier.

Properties:

Primary Key
Unique
Immutable
Auto-generated
CurrentSHA512

Type:

TEXT

Length:

128 hexadecimal characters

Purpose:

Stores the SHA-512 hash of the current binary representation of the image.

Properties:

Unique
Indexed
Mutable (only if the file itself is intentionally modified)
FirstSeen

Type:

DATETIME

Purpose:

Timestamp when the image first entered the database.

Immutable.

LastSeen

Type:

DATETIME

Purpose:

Timestamp of the latest successful scan confirming the file still exists.

Updated by Scanner only.

Status

Type:

ENUM

Initial values:

ACTIVE
MISSING
DELETED

Future values MAY be added.

Why this entity exists

The Image entity provides a permanent logical identity independent of filename, directory structure and AI classifications.

2. Entity: File
Purpose

Represents the current physical file associated with an Image.

Unlike Image, this entity describes the filesystem.

Ownership

Created by:

Scanner

Updated by:

Scanner

Rename module

Move module

Fields
ImageID

Foreign Key

References:

Image

AbsolutePath

Type:

TEXT

Purpose:

Current absolute path.

Must always point to the current location.

Filename

Type:

TEXT

Purpose:

Current filename.

Extension excluded.

Extension

Type:

TEXT

Examples:

jpg

jpeg

png

webp

bmp

gif

pns

Unknown extensions MAY be stored.

SizeBytes

INTEGER

Current file size.

Width

INTEGER

Pixels.

Height

INTEGER

Pixels.

FileModifiedTime

DATETIME

Filesystem timestamp.

LastFilesystemScan

DATETIME

Last successful verification.

Why this entity exists

Physical properties change over time.

They do not change Image identity.

3. Entity: Analysis
Purpose

Stores objective observations.

Never interpretations.

Ownership

Created and updated only by analysis modules.

Example fields

BWDetected

BOOLEAN

ScreenshotDetected

BOOLEAN

IRLDetected

BOOLEAN

MemeDetected

BOOLEAN

CosplayDetected

BOOLEAN

AnimationDetected

BOOLEAN

AlphaChannel

BOOLEAN

Confidence

REAL

0.0–1.0

AnalysisTimestamp

DATETIME

ModuleVersion

TEXT

Why this entity exists

Analysis represents measurable facts.

These facts should remain independent from semantic interpretation.

4. Entity: Classification
Purpose

Represents AI conclusions.

Unlike Analysis, these values are expected to change.

Example fields

Universe

TEXT

Character

TEXT

Theme

TEXT

GroupImage

BOOLEAN

Confidence

REAL

Source

ENUM

Possible values:

AI

USER

IMPORTED

Confirmed

BOOLEAN

LastUpdated

DATETIME

Why this entity exists

Semantic interpretation evolves.

It should never overwrite factual observations.

5. Entity: Event
Purpose

Provides complete history.

Events are append-only.

Never updated.

Never deleted.

Fields

EventID

Primary Key

ImageID

Foreign Key

Timestamp

DATETIME

Module

TEXT

EventType

ENUM

Examples:

SCANNED

MOVED

RENAMED

CLASSIFIED

USER_CORRECTED

RETURNED_TO_TODO

ACCEPTED

DELETED

Description

TEXT

Optional.

Why this entity exists

Every important action should become traceable.

6. Entity: Module

Stores metadata describing every framework module.

Fields:

Name
Version
BuildDate
ConfigurationVersion
Enabled
LastExecution
ExecutionCount
7. Entity: Tag

Represents generic tags independent from universes.

Examples:

Christmas

Halloween

School Uniform

Night

Rain

Beach

Smile

Bikini

Multiple tags per image are allowed.

8. Design Rules

Every Image MUST exist before dependent entities.

Every entity MUST reference ImageID.

No entity may directly reference another analysis entity.

Modules communicate through Image.

9. Normalization

The schema intentionally avoids duplicated information.

Every piece of information should have a single authoritative location.

10. Future Extensions

Future entities may include:

OCR
Embedding
Similarity Groups
Duplicate Families
Face Detection
Clothing Detection
Artist Detection
Quality Assessment

The current schema has been designed to accommodate these additions without structural redesign.

End of DOC-005B