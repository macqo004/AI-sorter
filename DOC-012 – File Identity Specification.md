# DOC-012 – File Identity Specification

## 1. Purpose

This document defines how files are uniquely identified within the project.

The purpose of the File Identity system is to ensure that every physical image stored in the collection can be reliably identified regardless of its filename or location.

The identity mechanism serves as the foundation for:

* Scanner Module;
* Database Architecture;
* Analysis Modules;
* AutoSort Engine;
* Database Maintenance;
* Collection Consistency Checker;
* File Renamer.

---

# 2. Design Philosophy

The project identifies files by their **content**, not by their filename.

File names and directory locations may change during the lifetime of the collection.

The actual binary content of the image is considered the primary identity.

The project therefore separates:

* **file identity**
* **file location**

---

# 3. Primary Identifier

The primary identifier of an image is:

**SHA512**

The SHA512 hash represents the binary contents of the file.

Two files with identical SHA512 values are considered identical binary objects.

---

# 4. Internal Database Identifier

Each database record receives a unique:

```text
file_id
```

`file_id` is an internal database identifier.

Characteristics:

* assigned when the record is created;
* unique within the database;
* never reused;
* independent from filename;
* independent from directory;
* independent from SHA512.

`file_id` exists only to simplify internal database relations.

---

# 5. File Record

Each file record contains at minimum:

```text
file_id

SHA512

current_path

width

height

metadata

status

created_at

deleted_at
```

Additional fields may be added by future versions.

---

# 6. current_path

The database stores the current relative location of the file.

Example:

```text
AI/Games/Hoyoverse/Genshin Impact/Furina/image001.jpg
```

The stored path represents the latest known location.

Whenever a file is successfully renamed or moved by project modules, `current_path` shall be updated.

---

# 7. File Status

Every record shall have one status.

Supported statuses:

## ACTIVE

The file currently exists inside one of the configured collection directories.

---

## ARCHIVED

The file previously existed but is no longer present.

Archived records remain available until explicitly removed by the user.

---

Future versions may introduce additional statuses if required.

---

# 8. File Creation

When Scanner discovers a file whose SHA512 does not exist in the database:

1. calculate SHA512;
2. create a new file record;
3. assign a new file_id;
4. set status to ACTIVE;
5. store current_path;
6. initialize metadata.

---

# 9. File Rename

Changing a filename does **not** create a new file.

Example:

Before:

```text
file_id = 15

SHA512 = AAAA

current_path = /todo/furina (1).jpg
```

After:

```text
file_id = 15

SHA512 = AAAA

current_path = /todo/furina.jpg
```

Only `current_path` changes.

All analysis results remain valid.

---

# 10. File Move

Moving a file inside supported directories behaves exactly like renaming.

Only:

```text
current_path
```

is updated.

No new record shall be created.

---

# 11. File Modification

If binary contents change, the SHA512 value changes.

The project treats the modified image as a completely new file.

Example:

Before:

```text
file_id = 15

SHA512 = AAAA
```

After editing:

```text
SHA512 = BBBB
```

Scanner shall:

* archive the old record;
* create a new record;
* assign a new file_id.

Previous analysis results remain attached to the archived record.

---

# 12. Deleted Files

If Scanner cannot find a previously known SHA512 inside configured directories:

the record shall become:

```text
ARCHIVED
```

The record is not deleted automatically.

Removal of archived records is handled by Database Maintenance.

---

# 13. Reappearing Files

If a previously archived file appears again with exactly the same SHA512:

the record may be restored to ACTIVE.

If the archived record has already been permanently removed from the database:

a completely new record shall be created.

---

# 14. SHA512 Calculation Failure

Scanner may encounter files whose SHA512 cannot be calculated.

Examples include:

* corrupted files;
* unreadable files;
* permission errors;
* interrupted reads;
* hardware failures.

The system shall:

* skip creation of the database record;
* create a log entry;
* optionally create a Review Queue entry according to DOC-013.

No placeholder SHA values shall ever be generated.

---

# 15. Hash Collision

The project assumes SHA512 provides a practically unique identifier.

Intentional handling of SHA512 collisions is outside the project scope.

No additional collision-resolution mechanism is implemented.

---

# 16. Database Relations

All analysis modules shall reference:

```text
file_id
```

rather than file paths.

This ensures that changing filenames does not invalidate analysis data.

---

# 17. Relationship with Renamer

The File Renamer module modifies:

* filenames;
* directory names;
* current_path.

It shall never modify:

* file_id;
* SHA512;
* analysis results.

After every successful rename, the database shall be updated with the new current_path.

---

# 18. Relationship with Database Maintenance

Database Maintenance may:

* archive records;
* permanently remove archived records;
* rebuild the database.

Database rebuild recreates file records from currently existing files.

Previously assigned file_id values are not guaranteed to remain unchanged after a rebuild.

---

# 19. Identity Principles

The project follows the following identity rules:

| Operation             | New file_id | New SHA512 |   Update current_path  |
| --------------------- | :---------: | :--------: | :--------------------: |
| Rename                |      No     |     No     |           Yes          |
| Move                  |      No     |     No     |           Yes          |
| Binary modification   |     Yes     |     Yes    |           Yes          |
| Delete                |      No     |     No     | No (status → ARCHIVED) |
| Restore archived file |     No*     |     No     |           Yes          |

* Only if the archived record still exists.

---

# 20. Safety Principles

The identity system is designed around one fundamental rule:

> **Binary content defines identity. Names and locations describe identity.**

Whenever binary contents change, the project treats the result as a different file.

Whenever only filenames or locations change, the existing identity shall be preserved.

These principles guarantee consistent behaviour across all project modules and simplify long-term maintenance of the collection.
