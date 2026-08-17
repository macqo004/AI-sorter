# DOC-108

# Theme Analysis Module

**Project:** AI Image Collection Management System

**Document:** DOC-108

**Module:** Theme Analysis

**Version:** 1.0 Draft

**Status:** Design Specification

---

# 1. Purpose

Theme Analysis is responsible for detecting broad visual themes present within an image.

The module does not determine:

* Universe
* Character
* Species

Those are handled by dedicated modules.

Theme Analysis focuses only on general visual content.

Examples:

* Bikini
* Christmas
* Halloween
* Maid
* Beach
* School Uniform
* Kimono

The module stores observations inside the database.

It does not move files.

---

# 2. Design Philosophy

Themes are intentionally generic.

They describe:

> "What is shown?"

rather than

> "Who is shown?"

or

> "Where does the image come from?"

Examples:

Correct:

* Bikini
* Beach
* Christmas

Incorrect:

* Furina
* Genshin Impact
* Demon Girl

---

# 3. Responsibilities

Theme Analysis SHALL:

* analyse visual themes;
* assign confidence values;
* write observations to the database;
* support multiple themes per image.

Theme Analysis SHALL NOT:

* move files;
* rename files;
* create folders;
* analyse Universe;
* analyse Character;
* analyse Monster Girl species.

---

# 4. Database Output

Each detected theme creates an observation.

Example:

```text
SHA512:
abc123

Theme:
Bikini

Confidence:
0.96
```

Additional observations:

```text
Beach
0.81

Summer
0.77
```

---

# 5. Multiple Themes

An image may contain multiple valid themes.

Example:

Image:

Girl wearing bikini on a beach during Christmas event.

Possible observations:

```text
Bikini
0.97

Beach
0.92

Christmas
0.83
```

All observations are stored independently.

---

# 6. Theme Confidence

Every detected theme receives a confidence value.

Example:

```text
Theme

Confidence

Bikini
0.96

Beach
0.91

Summer
0.74

Swimming Pool
0.42
```

Low-confidence observations remain available for manual review.

---

# 7. Theme Categories

Themes are intentionally broad.

Examples:

Clothing

* Bikini
* Maid
* Kimono
* School Uniform

Seasonal

* Christmas
* Halloween
* Valentine's Day

Environment

* Beach
* Swimming Pool
* Forest

General concepts

* Winter
* Summer
* Festival

The list is expandable.

---

# 8. Theme Priority

Theme Analysis has lower priority than Collection-specific classifiers.

If an image belongs to an existing Collection Tree, Theme observations remain metadata.

Example:

```text
Anime

↓

Genshin Impact

↓

Furina
```

Theme:

```text
Bikini
```

The image remains inside:

```text
Anime/
Genshin Impact/
Furina/
```

Theme information is retained in the database.

---

# 9. Fallback Classification

Themes may also serve as a valid destination for images that cannot currently be organised into another Collection Tree.

Examples:

Original artwork.

Unknown artist.

Unknown universe.

Random wallpaper.

Unknown game.

Those images may be organised using Themes.

Example:

```text
Themes/
└── Bikini/
```

---

# 10. Future Collection Expansion

Theme classification is never considered final.

If, in the future, a dedicated Collection Tree is created, images may later be moved there by AutoSort.

Example:

Initially:

```text
Themes/
└── Fairy/
```

Later:

User creates:

```text
Anime/
└── Winx Club/
```

The database already contains:

```text
Universe:
Winx Club
```

AutoSort may relocate images during a later execution.

Theme Analysis performs no action.

---

# 11. Manual Review

Users may manually reject Theme suggestions.

Rejected themes remain recorded inside the database.

Future project versions may use those decisions to improve workflow.

Theme Analysis itself never modifies user decisions.

---

# 12. Performance

Theme Analysis should balance speed and accuracy.

Requirements:

* GPU acceleration when available.
* CPU fallback.
* Batch processing.
* Multi-threading.
* Incremental processing.

Only images requiring analysis are processed.

Previously analysed images are skipped unless re-analysis is explicitly requested.

---

# 13. Re-analysis

The module supports repeated execution.

Typical scenarios:

* improved AI model;
* new theme categories;
* manual request;
* database rebuild.

Previous observations remain available for comparison.

---

# 14. Logging

Each execution produces a log.

Example:

```text
Start:
2026-08-01 18:00

Images analysed:
8421

Images skipped:
74112

New observations:
21437

Execution time:
00:08:17
```

Errors are logged separately.

---

# 15. Future Extensions

Possible future additions:

* Theme hierarchy.
* Theme groups.
* User-defined themes.
* Theme synonyms.
* Confidence calibration.
* Theme voting from multiple AI models.

The current version intentionally keeps Theme Analysis simple and modular.

---

# 16. Acceptance Criteria

Theme Analysis is considered complete when it:

* detects broad visual themes;
* supports multiple themes per image;
* stores confidence values;
* never performs file operations;
* integrates with AutoSort through the database;
* supports future expansion without redesign.

---

# End of DOC-108
