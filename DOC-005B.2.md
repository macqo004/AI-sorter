DOC-005B.2
Database Schema
Part B.2 – Operational Entities

Project: AI Image Framework (working title)

Version: 0.1 Draft

Depends on

DOC-005A
DOC-005B.1
1. Purpose

This document defines the operational entities responsible for recording how the framework performs its work.

Unlike Image, File and Observation, these entities describe:

module execution,
framework history,
user feedback,
system configuration.
2. Overview
Module
   │
   ├── Job
   │
   └── Observation

Image
   │
   ├── Event
   │
   └── Tag
3. Entity: Module
Purpose

Represents one framework module.

Every executable component of the framework MUST have exactly one Module record.

Examples
Scanner

BW Filter

Screenshot Filter

Meme Filter

IRL Filter

Universe Detector

Character Detector
Fields
ModuleID

INTEGER

Primary Key

Name

TEXT

Unique.

Examples:

Scanner

BW Filter

IRL Filter
Version

TEXT

Current module version.

Example:

1.0.0
Enabled

BOOLEAN

Determines whether Scheduler may execute the module.

Description

TEXT

Optional.

Human-readable description.

Created

DATETIME

Creation timestamp.

Design Notes

Module stores configuration-level information.

It does not store execution history.

4. Entity: Job
Purpose

Represents one execution of one module.

Every module execution creates exactly one Job.

Example
Scanner

Start

↓

5,000,000 files

↓

Completed

↓

Duration

↓

Statistics
Fields
JobID

INTEGER

Primary Key

ModuleID

INTEGER

Foreign Key

References

Module.ModuleID

Started

DATETIME

Finished

DATETIME

Status

ENUM

Possible values:

Running

Completed

Cancelled

Failed
FilesProcessed

INTEGER

FilesSkipped

INTEGER

FilesFailed

INTEGER

DurationMs

INTEGER

Execution time.

Notes

TEXT

Optional.

Design Notes

Jobs describe executions.

They never describe images.

5. Entity: Event
Purpose

Stores important events affecting an Image.

Events are append-only.

They are never modified.

Examples
Image discovered

Moved

Renamed

User accepted AI result

Returned to TODO

Deleted

Imported
Fields
EventID

INTEGER

Primary Key

ImageID

INTEGER

Foreign Key

Timestamp

DATETIME

EventType

TEXT

Examples:

DISCOVERED

MOVED

RENAMED

RETURNED_TO_TODO

AI_ACCEPTED

USER_RECLASSIFIED

DELETED
ModuleID

INTEGER

Nullable.

References Module.

NULL means:

manual user action.

Description

TEXT

Optional.

Design Notes

Events represent history.

History is never overwritten.

6. Entity: Tag
Purpose

Represents generic semantic tags.

Tags are independent from folder structure.

They provide additional search capability.

Examples
Christmas

Halloween

School Uniform

Beach

Bikini

Night

Rain
Fields
TagID

INTEGER

Primary Key

Name

TEXT

Unique.

Description

TEXT

Optional.

Relationship

Images and Tags form a many-to-many relationship.

Implementation should therefore include an intermediate table.

Example:

ImageTag

ImageID

TagID

This table stores only relationships.

No additional metadata is required in the first version.

7. User Feedback

User feedback is one of the primary learning mechanisms.

The framework MUST NOT silently overwrite user decisions.

Example:

AI

↓

Furina

↓

User

↓

Ganyu

The original observation remains in the database.

A new observation representing the user decision is added.

An Event is also created.

8. Manual Corrections

If the user manually moves an image:

AI

↓

AI\Genshin\Furina

↓

User

↓

AI\Genshin\Ganyu

The framework MUST:

detect the change,
create an Event,
mark previous Observation as not final,
create a new Observation representing the corrected classification.
9. Returning Images to TODO

When an image is returned to TODO:

AI

↓

TODO

the framework interprets this as:

AI classification rejected.

The next execution of the corresponding module MAY attempt another classification.

The previous rejected observation remains available for learning and statistics.

10. Deleted Images

If an image disappears from every monitored directory:

LifecycleState becomes

DELETED

The database record remains.

Historical information is preserved.

11. Design Rules

Modules never communicate directly.

Communication occurs only through the database.

Every module reads existing information.

Every module appends new information.

Modules do not modify data owned by other modules, except where explicitly defined (e.g. superseding their own previous observations).

12. Scalability

Operational entities must support millions of executions.

History must remain queryable.

The framework should prioritize append operations over destructive updates.

End of DOC-005B.2