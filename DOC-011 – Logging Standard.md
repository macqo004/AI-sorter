# DOC-011

# Logging Standard

**Project:** AI Image Collection Management System

**Document:** DOC-011

**Version:** 2.0

**Status:** Draft

**Depends on:**

DOC-005
DOC-007
DOC-010

---

# 1. Purpose

This document defines the common logging standard used by project modules and shared system components.

The primary objectives are to:

* provide understandable diagnostic information;
* allow the user to determine what happened without reading source code;
* support troubleshooting;
* provide execution statistics;
* preserve a chronological record of significant module activity.

Logs are primarily human-oriented. They may also be structured sufficiently for later automated analysis.

---

# 2. General Principles

Logging shall be:

* consistent;
* readable;
* useful;
* sufficiently detailed for troubleshooting;
* independent of individual module implementation;
* lightweight enough not to become a significant processing bottleneck.

Every module shall use the common logging conventions defined here while remaining responsible for module-specific information that is useful for understanding its own operation.

---

# 3. Module Independence

Logging does not create dependencies between modules.

A module writes its own execution log. It does not require another module to be running in order to log its activity.

Modules do not communicate with one another through logs.

Persistent information exchanged between modules is exchanged through the project database according to DOC-007 and DOC-010.

For example, ten executions of a B&W Analysis module and one execution of an IRL Analysis module are independent executions:

```text
B&W #1  ──┐
B&W #2    │
B&W #3    │
...       ├── Database
B&W #10   │
          │
IRL #1  ──┘
```

The fact that one module has executed once does not limit, require or synchronize the number of executions of another module.

Logging shall preserve the individual execution history of each invocation.

---

# 4. What a Log Entry Should Explain

An important log entry should answer, whenever applicable:

1. What happened?
2. Which module or component produced the entry?
3. Which file or object was affected?
4. Why did it happen?
5. What action was taken?
6. What should the user do next, if intervention is required?

Example:

```text
Scanner
WARNING

Unable to calculate SHA512.

File:
D:\Incoming\furina.jpg

Reason:
Access denied.

Suggested action:
Check file permissions and run Scanner again.
```

---

# 5. Human Readability

Logs must not intentionally be written as incomprehensible machine output.

User-facing log messages should use clear language and identify the affected object when practical.

Avoid relying on messages such as:

```text
Error 0x82
NullReferenceException
Operation failed
```

without useful context.

Technical exception details may be retained in a debug log when useful, but they must not replace the human-readable explanation of the event.

---

# 6. Log Levels

The project uses the following standard levels.

## INFO

Normal and expected operation.

Examples:

* module started;
* configuration loaded;
* database opened successfully;
* significant operation completed;
* module execution completed.

## WARNING

Unexpected but recoverable situation.

Examples:

* image skipped;
* optional metadata unavailable;
* confidence below configured threshold;
* file requires user review.

## ERROR

An operation failed, but the module may continue or preserve previously completed work.

Examples:

* one image could not be read;
* SHA512 calculation failed for one file;
* one database operation failed;
* one requested filesystem operation could not be completed.

## FATAL

The current module execution cannot safely continue.

Examples:

* required database unavailable;
* incompatible database schema;
* invalid essential configuration;
* required storage unavailable.

FATAL terminates the current module execution only. It must not terminate unrelated modules.

## DEBUG

Optional developer diagnostics.

DEBUG output may be disabled by default and may contain implementation details unsuitable for normal user-facing logs.

---

# 7. Module and Component Identification

Every log entry shall identify its originating module or system component.

Examples:

```text
Scanner
Color Analysis
IRL Analysis
Universe Analysis
Character Analysis
Theme Analysis
AutoSort
File Renamer
Database Maintenance
Collection Consistency Checker
Configuration Manager
Collection Definition Wizard
System
```

A log category shall not represent a component that does not exist as a current project concept. In particular, Migration Queue is not a separate module in the current architecture.

---

# 8. Execution Identification

Where a module execution has been assigned an `execution_id` according to DOC-005, log entries associated with that execution should include the execution identifier where practical.

This allows multiple independent executions of the same module to be distinguished.

For example:

```text
Module: B&W Analysis
Execution ID: 1042

Module: B&W Analysis
Execution ID: 1043
```

Both executions may occur independently and their logs must not be merged in a way that makes their individual history ambiguous.

---

# 9. File Identification in Logs

When a log entry concerns a particular file, the entry should include as much identifying information as is useful and available.

Preferred identifiers are:

```text
SHA512
file_id (when available)
current path
filename
```

Because SHA512 is the logical binary-content identity defined by DOC-012, it is the preferred stable file identifier in logs where the relevant value is available.

Paths and filenames remain useful for locating the physical file but do not define file identity.

---

# 10. Standard Log Entry Fields

A structured log entry should contain, where applicable:

```text
timestamp
module
execution_id
level
message
SHA512
file_id
current_path
operation
result
```

Not every field is required for every entry.

The purpose of the standard is to ensure that useful context is available without forcing irrelevant fields into every message.

---

# 11. Execution Start and Completion

Every module execution shall log its start and final outcome.

At minimum:

```text
STARTING / INFO
RUNNING / INFO
COMPLETED / INFO
CANCELLED / INFO or WARNING
FAILED / ERROR or FATAL
```

The completion entry should include useful statistics where available, such as:

```text
files processed
files skipped
files failed
time elapsed
```

Example:

```text
Universe Analysis
Execution ID: 1042

Finished successfully.

Processed: 18,452
Recognized: 17,981
Below confidence threshold: 471
Execution time: 00:03:12
```

---

# 12. Error Reporting

Whenever possible, an error should include a corrective action or explain whether user intervention is required.

Example:

```text
Database
ERROR

Unable to write record.

Reason:
Database file is read-only.

Suggested action:
Check file permissions.
```

An error concerning one file should not be described as a failure of the entire module unless the module actually had to terminate.

---

# 13. Logging Successful Operations

Logs shall record significant successful operations as well as failures.

Examples include:

* module started;
* configuration validated;
* database connected;
* batch completed;
* file moved successfully;
* file renamed successfully;
* analysis result stored;
* module execution completed.

Logging every trivial internal operation is not required and may reduce performance or readability.

---

# 14. Reports vs Logs

Reports and logs serve different purposes.

**Logs** explain what happened during execution and support diagnostics.

**Reports** present selected results to the user for review, summary or further processing.

Examples of reports include:

* consistency reports;
* analysis statistics;
* review lists;
* duplicate reports;
* export files.

A report must not replace the execution log.

---

# 15. Review-Related Logging

When a module creates a case requiring user review, the log should record:

* that review is required;
* the affected file;
* the reason;
* the proposed or detected result where applicable;
* whether the file was moved to a review/workspace location;
* whether the module left the original file untouched.

Review Queue remains a logical user-decision mechanism defined by DOC-013. Logging does not create a separate migration subsystem.

---

# 16. Performance

Logging must not become a significant processing bottleneck, especially for modules processing millions of files.

Implementations may use:

* buffered writes;
* asynchronous logging;
* batch flushing;
* configurable verbosity.

The module must not spend more effort logging routine events than performing the actual work unless a diagnostic mode explicitly requires it.

---

# 17. Log Storage and Rotation

The physical log storage mechanism is an implementation decision unless another document defines it.

The system should support practical log retention and rotation.

A useful default is to associate logs with individual module executions or execution sessions so that unrelated runs remain easy to distinguish.

Old logs may be archived or removed according to user configuration.

Log retention must not alter database records or file history.

---

# 18. Failure to Write Logs

Failure to write a log must not normally terminate module execution.

If logging fails, the module should:

* continue when safe;
* notify the user when practical;
* retain the failure in memory or another temporary mechanism when feasible.

A module may treat logging as mandatory only where an explicit higher-level integrity requirement justifies that behaviour.

---

# 19. Debug Information

Debug logs may contain:

* stack traces;
* implementation details;
* timing information;
* internal state useful for troubleshooting;
* database queries where appropriate.

Debug information must not replace the normal readable log and should be clearly identified as diagnostic output.

---

# 20. Log History and Database History

Logs and database history serve related but different purposes.

The database stores persistent project state and structured historical information defined by DOC-005.

Logs explain the execution process and assist troubleshooting.

A log must not be the only place where a required persistent state change is recorded.

Conversely, the database does not need to store every diagnostic message produced during execution.

---

# 21. Standardization and Module Extensions

All modules shall follow this standard.

A module may add additional log fields or messages when they are useful for its specific operation.

Such extensions must not:

* remove required context;
* contradict the common log levels;
* make normal messages intentionally unreadable;
* create hidden dependencies between modules.

---

# 22. Relationship with Other Documents

```text
DOC-005
    Defines persistent database entities and execution records.

DOC-007
    Defines module execution and independence.

DOC-010
    Defines the module interface contract.

DOC-011
    Defines the logging standard.

DOC-012
    Defines file identity and SHA512.

DOC-013
    Defines Review Queue and user decisions.
```

This document should not redefine the ownership rules of those documents.

---

# 23. Acceptance Criteria

The logging standard is considered correctly implemented when:

* every module provides useful execution logging;
* independent module executions can be distinguished;
* logs identify the originating module;
* file-related entries use stable identity information where available;
* major operations and final outcomes are logged;
* errors contain useful context;
* user intervention requirements are visible;
* logging does not create module-to-module communication;
* logging does not become a significant performance bottleneck;
* debug information can be separated from normal user-readable output.

---

# End of DOC-011
