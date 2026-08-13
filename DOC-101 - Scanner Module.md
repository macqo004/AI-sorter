DOC-101
Scanner Module

Project: AI Image Framework (working title)

Document: DOC-101

Module: Scanner

Version: 1.0 Draft

Status: Draft

Depends on

DOC-001
DOC-002
DOC-003
DOC-004
DOC-005
DOC-006
1. Purpose

Scanner is responsible for synchronizing the database with the filesystem.

Scanner performs no image analysis.

Scanner is the only module responsible for discovering new files and detecting filesystem changes.

All other modules depend on Scanner.

2. Responsibilities

Scanner SHALL:

discover new image files;
detect deleted files;
detect renamed files;
detect moved files;
detect modified files;
compute SHA-512 hashes when required;
update the database;
generate execution logs.

Scanner SHALL NOT:

classify images;
move files;
rename files;
create tags;
execute AI models;
modify user classifications.
3. Supported File Types

Initially supported:

jpg
jpeg
png
webp
gif
bmp
pns

Ignored:

mp4
webm
avi
mkv
mov
zip
rar
7z

Unknown file extensions shall be ignored unless explicitly enabled in future versions.

4. Scan Targets

Scanner operates on configured directory roots.

Each root has a logical role.

Possible roles:

TODO

AI

Library

Library represents one manually curated collection.

Multiple Library roots are supported.

Example:

TODO

AI

Anime

MonsterGirls

WesternAnimation

Themes

Scanner treats every Library root identically.

5. Recursive Scanning

Every configured root is scanned recursively.

Every subdirectory is included automatically.

No directory depth limit exists.

6. File Discovery

For every supported file Scanner collects:

absolute path;
directory;
filename;
extension;
size;
image dimensions;
modification time;
SHA-512 hash.
7. SHA-512 Strategy

SHA-512 is calculated only when required.

Algorithm:

Read file size

↓

Read modification timestamp

↓

Compare with database

↓

Changed?

YES
    ↓
    Calculate SHA-512
    ↓
    Update database

NO
    ↓
    Reuse existing SHA-512

This minimizes unnecessary disk reads during repeated scans.

8. Change Detection

Scanner detects the following events.

New file

File not present in database.

Action:

Create Image and File records.

Modified file

Size or modification timestamp changed.

Action:

Recalculate SHA-512.

Update File information.

Previous analytical results become invalid according to module-specific rules.

Renamed file

SHA identical.

Filename different.

Action:

Update File record.

Create Event.

Moved file

SHA identical.

Directory different.

Action:

Update File record.

Create Event.

Deleted file

File no longer exists.

Action:

Update LifecycleState.

Create Event.

9. Database Access

Scanner may modify:

Image
File
Event

Scanner SHALL NOT create Observations.

10. Threading

Scanner is designed for parallel execution.

Configuration parameter:

WorkerThreads

Allowed values:

0 = Automatic

1

2

4

8

16

...

Automatic mode selects an implementation-defined number of worker threads based on available CPU resources.

11. Transactions

Scanner is not transactional.

Every successfully processed file is written immediately.

Failure processing one file must not affect any other file.

Example:

File A

OK

↓

saved

File B

ERROR

↓

logged

File C

OK

↓

saved
12. Error Handling

Scanner continues processing whenever possible.

Typical recoverable errors:

access denied;
corrupted image;
unsupported format;
temporary I/O error.

The affected file is skipped.

Processing continues.

13. Logging

Each execution generates one log.

Example:

Scanner

Start:
2026-07-17 20:00

Finished:
2026-07-17 20:04

New:
124

Modified:
8

Moved:
12

Deleted:
3

Errors:
2

Duration:
00:04:18

Errors are listed below the summary.

Example:

Access denied

D:\TODO\image123.jpg
14. Performance Requirements

The Scanner shall be optimized for repeated execution.

Repeated scans should avoid recalculating SHA-512 whenever file metadata indicates no changes.

The Scanner shall be capable of processing collections containing millions of files.

15. Interaction with Other Modules

Scanner executes before every analysis module.

Analysis modules rely exclusively on information produced by Scanner.

Scanner never invokes analysis modules directly.

Module execution order is managed externally.

16. Configuration

The Scanner configuration shall include:

monitored directory roots;
logical role for each root (TODO, AI, Library);
worker thread count;
log directory;
supported file extensions.
17. Design Philosophy

Scanner is intentionally simple.

Its responsibility is limited to filesystem synchronization.

Semantic interpretation belongs to analysis modules.

18. Future Extensions

Possible future enhancements include:

file system event monitoring (instead of full scans),
configurable exclusion patterns,
incremental directory scanning,
checksum algorithm abstraction.

These features are outside the scope of the first implementation.

19. Acceptance Criteria

The Scanner module shall be considered complete when it can:

recursively scan configured roots;
detect new, moved, renamed, modified and deleted files;
maintain database consistency;
reuse existing SHA-512 values whenever possible;
generate execution logs;
continue operation after recoverable errors;
process collections containing millions of files without requiring manual intervention.


20. Hash Calculation Reliability
Purpose

The Scanner Module shall ensure that calculated SHA512 values are reliable and that failures during hash calculation do not compromise the integrity of the collection database.

The objective of this section is not to detect cryptographic SHA512 collisions, but to detect software, hardware and data integrity issues that could result in an incorrect hash being associated with a file.

21. Hash Status

Every scanned file shall always have one of the following hash states:

PENDING

Hash has not yet been calculated.

VALID

SHA512 has been successfully calculated and verified.

FAILED

The hash could not be calculated due to an error.

Typical causes include:

unreadable file;
file locked by another process;
storage I/O error;
insufficient permissions;
unexpected internal exception.

Files with status FAILED shall not participate in any subsequent processing modules until a valid SHA512 value has been obtained.

22. Hash Verification

Whenever SHA512 is calculated successfully, the Scanner shall associate the value with the current database record.

If Scanner detects an unexpected situation during rescanning, such as:

the same file path producing a different SHA512 value,
inconsistent file metadata,
unexpected read errors,

the Scanner should perform a second SHA512 calculation before accepting the new value.

This additional verification is intended to reduce the likelihood of incorrect hashes caused by transient read errors or software faults.

23. Cryptographic Collisions

The project assumes that SHA512 uniquely identifies file content.

The probability of two different files producing the same SHA512 value accidentally is considered negligible for the intended collection size.

Therefore, identical SHA512 values are treated as identical binary content.

The Scanner is not required to implement any special handling for theoretical SHA512 collisions.

24. Internal Consistency

The Scanner shall assume that software defects, storage errors or memory corruption are significantly more likely than an actual SHA512 collision.

If internal consistency checks indicate that identical SHA512 values appear to represent different binary content, the event shall be treated as an internal integrity error.

Such situations should be reported in logs for manual investigation rather than handled as normal operating conditions.

25. Recovery

Files with FAILED hash status may be rescanned during future Scanner executions.

Once a valid SHA512 value has been successfully calculated, the file may continue through the normal processing pipeline.

26. Design Principle

The Scanner shall never silently ignore hash calculation failures.

Every unsuccessful calculation shall produce:

a log entry;
an error status for the file;
exclusion of the file from analysis until the problem has been resolved.

This ensures that no file enters the analysis pipeline without a verified SHA512 identifier.

End of DOC-101