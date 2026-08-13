# DOC-110 – Set Detection and Grouping Module Specification

## 1. Purpose

The Set Detection and Grouping Module is responsible for identifying and grouping visually related image files into logical collections called **Sets**.

The primary purpose of this module is not to identify the semantic content of images, such as characters, universes, themes, or artists.

The purpose of the module is to reduce the complexity of further analysis by transforming a large number of independent image files into manageable logical groups.

A correctly created Set allows later analysis modules to operate on a group of related images instead of evaluating every file independently.

---

# 2. Scope

The Set Detection Module:

* analyzes image similarity,
* identifies groups of visually related files,
* creates Set objects,
* maintains relationships between Sets and files,
* provides grouped input for further classification modules.

The module does **not**:

* determine the character shown in the image,
* determine the universe/source material,
* determine themes,
* decide the final destination of files,
* rename or move files to final collection locations.

---

# 3. Definition of Set

A Set is a logical group of image files that share a significant visual relationship.

A Set represents the assumption:

> "These files should be analyzed and managed together because separating them may reduce the accuracy of later classification."

A Set does not necessarily mean:

* the same character,
* the same universe,
* the same artist,
* the same exact image.

A Set may contain:

* different expressions of the same character,
* different poses,
* different views,
* variations of the same artwork,
* related images sharing a common visual concept.

---

# 4. Examples of Valid Sets

## 4.1 Expression variations

Example:

```
Set_0001

furina_smile.jpg
furina_angry.jpg
furina_surprised.jpg
furina_happy.jpg
```

The images are different, but the difference is limited mainly to facial expression.

They should be treated as one logical group.

---

## 4.2 Pose or view variations

Example:

```
Set_0002

character_front.jpg
character_side.jpg
character_back.jpg
```

The images represent variations of the same visual subject.

---

## 4.3 Common theme

Example:

```
Set_0003

character_A_vampire.jpg
character_B_vampire.jpg
character_C_vampire.jpg
```

The images may represent different characters but share a common visual concept.

---

# 5. Invalid Set Examples

A Set must not contain unrelated images.

Example:

```
Set_0004

furina.jpg
ben10.jpg
sonic.jpg
random_landscape.jpg
```

The fact that images may share colors, composition, or general style is not sufficient.

A Set must have a meaningful visual connection between members.

---

# 6. Position in Processing Pipeline

Set Detection should run early in the processing pipeline.

Recommended order:

```
Source Trees
      |
      v
Scanner Module
      |
      v
Basic File Analysis
(SHA512, metadata, dimensions)
      |
      v
Set Detection Module
      |
      v
AI Sets Tree
      |
      v
Classification Modules
      |
      +----------------+
      |                |
      v                v
Universe Analysis   Theme Analysis
      |
      v
AutoSort Engine
      |
      v
Final Collection
```

---

# 7. Reason for Early Execution

Processing individual files at collection scale creates unnecessary complexity.

Example:

Without Sets:

```
5 000 000 files
        |
        v
5 000 000 independent analyses
```

With Sets:

```
5 000 000 files
        |
        v
Set Detection
        |
        v
500 000 logical groups
        |
        v
Classification
```

The exact reduction depends on collection structure, but grouping should significantly reduce repeated analysis.

---

# 8. Interaction With Classification Modules

Classification modules must treat Sets as logical analysis units.

Incorrect approach:

```
For every image:
    determine universe
```

Correct approach:

```
For every object:

    if object is SET:
        analyze complete Set

    else:
        analyze individual file
```

---

Example:

Input:

```
AI/Sets/0001

001.jpg
002.jpg
003.jpg
004.jpg
```

Universe Analysis receives:

```
Object:
SET_0001

Members:
4 images
```

The decision should be based on the entire group, not a single file.

---

# 9. Set Classification Independence

Set Detection must remain independent from semantic classification.

The module should not store assumptions such as:

```
character = Furina
universe = Genshin Impact
theme = Anime
```

These belong to other modules.

Correct:

```
Set Detection
        |
        v
Set_0001
        |
        v
Universe Analysis
        |
        v
Genshin Impact
```

---

# 10. Set Storage

Sets are stored initially in the AI processing tree.

Example:

```
AI
└── Sets
    ├──0001
    ├──0002
    └──0003
```

A Set remains there until classification determines a more appropriate destination.

Possible results:

```
AI/Sets
```

if classification is unknown,

or:

```
FINAL/Anime/Genshin Impact/Furina/0001
```

if classification succeeds.

---

# 11. Set Folder Naming

Set folders use numeric identifiers.

Format:

```
NNNN
```

Rules:

* exactly 4 digits,
* range: 0001-9999,
* no suffixes,
* no descriptive names.

Valid:

```
0001
0042
1250
```

Invalid:

```
1
001
Set_001
0001_copy
```

---

# 12. Folder Number Allocation

When creating a new Set folder:

1. Check existing folders in the destination.
2. Ignore folders not matching the Set naming format.
3. Select the smallest available number.
4. Create the new folder.

Example:

Existing:

```
0001
0002
0004
```

New Set receives:

```
0003
```

---

# 13. Set Identifier

The folder name is not the unique identifier.

The database identifier is the source of truth.

Example:

Database:

```
set_id = 15482

folder_name = 0007

destination =
FINAL/Anime/Genshin Impact/Furina
```

The folder name may change after moving the Set, but the Set identity remains unchanged.

---

# 14. Set Merging

If a newly detected Set matches an existing Set, the system should support merging.

Example:

Existing:

```
FINAL/Anime/Genshin Impact/Furina/0005

100 images
```

New:

```
AI/Sets/0009

15 images
```

Analysis:

```
Similarity:
96%

Possible action:
Merge
```

Result:

```
0005

115 images
```

The new Set does not create another independent folder.

---

# 15. Merge Safety

Set merging must consider the difference between:

* visual similarity,
* logical relationship.

High similarity does not always mean the same Set.

Possible automatic merge:

* duplicate data,
* identical source,
* very high confidence match.

Possible review:

* same character,
* same universe,
* similar style,
* unclear grouping reason.

---

# 16. User Review

When confidence is insufficient, the module should create a Review Queue entry.

Example:

```
Possible Set Merge

Existing:
Set 0005

Candidate:
Set 0012

Confidence:
82%

Actions:

[Merge]
[Keep Separate]
[Ignore]
```

No uncertain merge should happen without user approval.

---

# 17. Database Model

Minimal structure:

```
sets

set_id
status
folder_name
destination_path
confidence
created_at
```

Relationship:

```
set_members

set_id
file_id
similarity_score
```

---

# 18. Design Principles

The Set Detection Module follows these principles:

1. Group first, classify later.
2. Never confuse similarity with semantic understanding.
3. Preserve groups during later processing.
4. Analyze Sets as complete objects.
5. Avoid splitting logically connected images.
6. Avoid merging unrelated content.
7. Prefer uncertain review over destructive automatic decisions.

---

# End of DOC-110
