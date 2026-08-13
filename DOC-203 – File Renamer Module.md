DOC-203 – File Renamer Module

1. Purpose

The File Renamer module provides a controlled and deterministic mechanism for modifying filenames within the project.

Unlike ordinary batch renaming utilities, File Renamer is designed to operate safely on collections containing millions of images, including files stored inside the project's final collection trees.

The module shall prioritize data safety over automation.

Whenever uncertainty exists, the module shall preserve the original filename rather than attempting to infer the user's intentions.

The File Renamer modifies only filenames.

It shall never modify image contents.

2. Scope

The File Renamer is responsible for:

renaming files;
normalizing filenames;
preparing filenames according to predefined rules;
synchronizing filename changes with the project database;
generating Undo information;
generating Review Queue entries whenever required.

The module shall never:

modify image contents;
change directory structure;
move files between collections;
classify images;
perform AutoSort operations.

These responsibilities belong to other project modules.

3. Design Philosophy

The File Renamer follows the project's general design principle:

The system shall never guess when confidence is insufficient.

The module shall only perform deterministic transformations explicitly defined by enabled triggers.

If a filename cannot be safely transformed according to the selected trigger, the operation shall not be executed.

Instead, a Review Queue entry may be created according to DOC-013.

4. Architecture

The File Renamer consists of two logical components.

4.1 Renamer Engine

The Renamer Engine is responsible for:

directory traversal;
trigger execution;
conflict detection;
database synchronization;
Undo generation;
logging;
Review Queue integration;
operation summary.

The Renamer Engine does not define filename transformation rules.

4.2 Rename Triggers

Actual filename modifications are performed by independent triggers.

Each trigger performs exactly one well-defined task.

Examples include:

Remove Duplicate Suffixes
Replace Spaces
Transliterate Characters
WWW Filename Normalization
Future filename rules

The Renamer Engine executes enabled triggers.

Triggers remain independent from one another.

5. Trigger Philosophy

Each trigger has exactly one responsibility.

A trigger shall never perform unrelated filename modifications.

Example:

The trigger:

Remove Duplicate Suffixes

may remove:

 (1)

 (25)

 [1]

 {3}

It shall not:

replace spaces;
transliterate characters;
convert filename case;
remove arbitrary words.

Those operations belong to separate triggers.

This approach guarantees deterministic behaviour and simplifies future maintenance.

6. Trigger Independence

Triggers are completely independent.

The user may execute:

one trigger;
multiple triggers;
the same trigger multiple times.

Example:

Run:

Remove Duplicate Suffixes

Later:

Run:

Replace Spaces

Later again:

Run:

Remove Duplicate Suffixes

The File Renamer shall not assume that previous triggers have already been executed.

Every trigger shall analyse the current filename only.

7. Trigger Execution

When multiple triggers are selected, they shall be executed sequentially.

Each trigger receives the filename produced by the previous trigger.

Example:

Original:

Фурина (1).jpg

Trigger:

Remove Duplicate Suffixes

↓

Фурина.jpg

Trigger:

Transliteration

↓

Furina.jpg

Each trigger performs only its own transformation.

8. Trigger Configuration

Each trigger may be enabled or disabled independently.

Example:

☑ Remove Duplicate Suffixes

☑ Replace Spaces

☐ Transliterate Characters

☐ Convert To Lowercase

Only enabled triggers participate in the current execution.

The File Renamer itself shall not permanently enable or disable triggers.

Trigger configuration belongs to project settings.

9. Working Scope

The user selects a starting directory.

The module processes:

the selected directory;
all subdirectories below it.

Example:

Selected:

Collection/Anime

Processed:

Collection/Anime/Genshin

Collection/Anime/Furina

Collection/Anime/Blue Archive

Not processed:

Collection/Monster Girls

Collection/Themes
10. Supported Objects

The File Renamer operates only on files.

Directory names shall not be modified.

Future support for directory renaming may be introduced as a separate module.

11. Rule Engine

Triggers shall use configurable Rule Sets.

The Rule Engine determines which filename patterns are recognised.

Examples include:

Windows duplicate suffixes;
browser duplicate suffixes;
application-generated suffixes;
user-defined suffixes.

The Rule Engine shall be configurable.

Hardcoded filename rules should be avoided whenever practical.

Rule Set specification is defined separately from this document.

12. Safe Transformation Principle

Triggers shall only perform transformations explicitly defined by their Rule Sets.

Example:

Allowed:

furina (1).jpg

↓

furina.jpg

Not allowed:

furina_drawn_by_artist.jpg

↓

furina.jpg

because no rule explicitly defines such transformation.

13. Ambiguous Cases

If a trigger cannot determine whether a filename fragment matches one of its rules with sufficient certainty, the filename shall remain unchanged.

The trigger may create a Review Queue entry according to DOC-013.

The module shall always prefer preserving filenames over risking incorrect modifications.

14. Dry Run Mode

Every trigger shall support Dry Run mode.

During Dry Run:

filenames are analysed;
proposed changes are generated;
conflicts are detected;
Review Queue entries are generated;
database remains unchanged;
files remain unchanged.

Example:

Current:

furina (1).jpg

Proposed:

furina.jpg

Dry Run allows the user to verify the entire operation before making any changes.

15. Trigger Result

After execution each trigger shall produce a summary.

Minimum information:

processed files;
renamed files;
skipped files;
conflicts;
Review Queue entries;
errors.

Example:

Trigger

Remove Duplicate Suffixes

Processed:
124523

Renamed:
119842

Skipped:
4652

Review Queue:
18

Errors:
11

The Renamer Engine combines individual trigger reports into the final operation summary.

16. Filename Conflict Detection

Before renaming a file, the Renamer Engine shall verify whether the target filename already exists within the destination directory.

Example:

Current directory:

furina.jpg

furina (1).jpg

Removing the duplicate suffix would result in:

furina.jpg

Since the filename already exists, the rename operation shall not be executed automatically.

The original filename shall remain unchanged.

17. Conflict Handling

When a filename conflict is detected:

the affected file shall not be renamed;
remaining files shall continue processing;
a Review Queue entry may be created;
the conflict shall be included in the operation summary.

The Renamer shall never stop processing the remaining files because of individual conflicts.

18. Review Queue Integration

Whenever a trigger cannot safely complete an operation, it may create a Review Queue entry according to DOC-013.

Typical situations include:

filename conflicts;
ambiguous rule matches;
unsupported filename patterns;
filesystem errors requiring manual verification.

The Review Queue shall contain:

module name;
trigger name;
current filename;
proposed filename (if available);
reason for review;
confidence level (if applicable).

The File Renamer shall never execute operations stored only as suggestions.

19. Undo Support

The File Renamer shall generate Undo information for every successful rename operation.

Undo information shall allow the original filename to be restored.

Each Undo record should contain at minimum:

Timestamp

Trigger

file_id

SHA512

Original filename

New filename

Original path

New path

Undo information shall be stored independently from ordinary log files.

The exact storage format is implementation-dependent.

20. Database Synchronization

The File Renamer modifies only filenames.

Image identity remains unchanged.

After every successful rename:

current_path shall be updated;
file_id shall remain unchanged;
SHA512 shall remain unchanged;
analysis results shall remain unchanged.

The database shall only be updated after the filesystem operation has completed successfully.

Recommended order:

Prepare rename.
Validate conflicts.
Rename file.
Verify success.
Update current_path.
Write log.
Store Undo information.

The database shall never be updated before a successful filesystem operation.

21. Relationship with File Identity

The File Renamer shall comply with DOC-012.

Renaming a file shall never create a new database record.

Example:

Before:

file_id = 152

SHA512 = AAAAA

current_path = AI/Furina (1).jpg

After:

file_id = 152

SHA512 = AAAAA

current_path = AI/Furina.jpg

Only current_path changes.

22. Logging

Every rename operation shall be logged according to DOC-011.

The log should contain:

trigger name;
processed file;
result;
execution time;
errors;
generated Review Queue entries.

The operational log shall not replace Undo information.

23. Error Handling

The Renamer Engine shall continue processing whenever possible.

Errors affecting one file shall not interrupt processing of remaining files.

Examples include:

permission denied;
filename already exists;
file locked by another process;
filesystem errors;
database update failure.

Each error shall be logged.

Critical failures may terminate the current trigger only if continuing could compromise data integrity.

24. Safety Principles

The File Renamer shall follow these principles:

never guess filename semantics;
never remove information not explicitly matched by a rule;
never overwrite existing files;
never silently resolve filename conflicts;
never modify image contents;
never modify directory names;
never modify SHA512;
never modify file_id.

Whenever uncertainty exists, the filename shall remain unchanged.

25. Performance

The File Renamer shall process files sequentially within the selected scope.

The implementation may use multiple worker threads provided that:

two workers never attempt to rename the same file simultaneously;
database consistency is preserved;
Undo information remains ordered correctly.

Performance optimizations shall never compromise deterministic behaviour.

26. User Interaction

The user controls:

starting directory;
enabled triggers;
recursive processing;
Dry Run mode;
execution.

The File Renamer shall never execute automatically.

Every execution is initiated explicitly by the user.

27. Operation Summary

After completion, the Renamer Engine shall generate a global summary.

Recommended information:

Execution Summary

Starting directory

Execution time

Processed files

Renamed files

Skipped files

Conflicts

Review Queue entries

Errors

Database updates

Undo records created

This summary provides the user with an overview of the completed operation.

28. Future Extensions

The architecture is designed to support additional triggers without modifying the Renamer Engine.

Future triggers may include:

filename case normalization;
removal of unsupported filesystem characters;
custom user-defined rules;
filename templates;
regular-expression-based transformations;
plugin-provided filename transformations.

Each future trigger shall comply with the principles defined in this document.

29. Final Design Principle

The File Renamer is intentionally conservative.

Its purpose is not to "clean" filenames aggressively.

Its purpose is to execute deterministic, explicitly requested transformations while preserving the integrity of the collection.

Whenever there is doubt, the system shall preserve the original filename and defer the decision to the user through the Review Queue.

This principle takes precedence over automation and shall remain the guiding rule for all future development of the File Renamer module.