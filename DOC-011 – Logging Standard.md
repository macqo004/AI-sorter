# DOC-011 – Logging Standard

## 1. Purpose

This document defines the logging standard used by all project modules.

The primary objectives of the logging system are:

* provide understandable diagnostic information;
* allow users to identify problems without reading source code;
* simplify troubleshooting;
* provide execution statistics;
* create a chronological history of module activity.

Logs are intended primarily for **human users**, while remaining suitable for automated analysis if required.

---

# 2. General Principles

Every module shall generate logs according to the same rules.

Logging must be:

* consistent;
* readable;
* deterministic;
* lightweight;
* independent of individual module implementation.

Every module shall use the common logging framework defined by this document.

---

# 3. Readability

Logs **must not** contain cryptic messages, internal error codes or implementation-specific information unless absolutely necessary.

Preferred:

> Scanner
> Unable to calculate SHA512.
> File: D:\TODO\furina.jpg
> Reason: Access denied.
> Suggested action: Close the application using the file and run Scanner again.

Avoid:

> Error 0x82

or

> NullReferenceException in Scanner.cs line 472

Internal exception details may optionally be written to a separate debug log but shall never replace the user-readable message.

---

# 4. Human-Oriented Logging

Every important log entry should answer four questions whenever possible:

1. What happened?
2. Which file or object was affected?
3. Why did it happen? (if known)
4. What can the user do next?

Example:

Scanner

Image could not be processed.

File:
D:\TODO\furina.jpg

Reason:
File is currently locked by another application.

Suggested action:
Close the application and run Scanner again.

---

# 5. Log Levels

The following log levels shall be used throughout the project.

## INFO

Normal operation.

Examples:

* module started;
* module finished;
* configuration loaded;
* database connected.

---

## WARNING

Unexpected but recoverable situations.

Examples:

* image skipped;
* confidence below threshold;
* missing optional metadata;
* file already exists.

---

## ERROR

Operation failed.

Examples:

* SHA512 calculation failed;
* database write failed;
* image unreadable.

---

## FATAL

Critical error preventing further execution.

Examples:

* database unavailable;
* configuration corrupted;
* storage unavailable.

---

## DEBUG (optional)

Additional developer diagnostics.

Disabled by default.

---

# 6. Log Categories

Every log entry shall identify its originating module.

Examples:

* Scanner
* Renamer
* Database
* Universe Analysis
* Character Analysis
* Theme Analysis
* AutoSort
* Migration Queue
* Collection Definition Wizard
* Configuration Manager
* System

---

# 7. Log Format

Each entry should contain, where applicable:

* timestamp;
* module name;
* log level;
* message;
* file_id (if available);
* SHA512 (if available);
* current file path (if available).

Example:

2026-07-22 10:41:15

Scanner

INFO

Calculated SHA512 successfully.

File ID:
14582

SHA512:
...

Path:
AI\TODO\furina.jpg

---

# 8. Success Logging

Logs shall record not only failures but also successful execution of important operations.

Example:

Universe Analysis

Finished successfully.

Processed:
18,452 images

Recognized:
17,981

Below confidence threshold:
471

Execution time:
00:03:12

---

# 9. Error Reporting

Whenever possible, errors should include a suggested corrective action.

Example:

Database

Unable to write record.

Reason:
Database file is read-only.

Suggested action:
Verify file permissions.

---

# 10. Reports vs Logs

Reports and logs serve different purposes.

Logs are intended for diagnostics.

Reports are intended for presenting processing results to the user.

Examples of reports:

* Migration Queue;
* Theme Summary;
* Universe Statistics;
* Duplicate Report.

Reports shall not replace logging.

---

# 11. Performance

Logging shall not significantly reduce processing performance.

Recommended implementation:

* buffered writes;
* asynchronous logging;
* periodic flushing.

Logging must never become the primary performance bottleneck.

---

# 12. Log Rotation

Log files should be automatically rotated.

Recommended strategy:

* create a new log file for each module execution;
* optionally archive older logs;
* allow automatic cleanup according to user configuration.

---

# 13. Failure to Write Logs

Failure to save a log shall never terminate module execution unless logging is explicitly required for system integrity.

If log writing fails:

* module continues whenever possible;
* warning is displayed;
* failure is recorded in memory if feasible.

---

# 14. Consistency

All project modules shall follow this standard.

Individual modules may extend logging with additional information but shall not violate the formatting and readability rules defined in this document.

---

# 15. Design Philosophy

The logging system follows the principle:

> Logs should explain what happened, not merely report that something happened.

A user with basic computer knowledge should be able to understand the majority of log entries without consulting technical documentation or source code.

Logs should assist troubleshooting rather than create additional uncertainty.
