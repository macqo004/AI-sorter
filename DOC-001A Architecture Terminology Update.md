DOC-001A
Architecture Terminology Update

Project: AI Image Collection Management System

Document: DOC-001A

Version: 1.0

Status: Approved

Purpose: Terminology and Architecture Extension

1. Purpose

This document extends DOC-001 and introduces official terminology used throughout the project.

The goal is to separate generic project architecture from collection-specific logic.

This document does not replace DOC-001.

It only extends it.

2. General Philosophy

The project does not organize images around a single directory tree.

Instead, the project manages multiple independent Collection Trees.

Each Collection Tree represents a different method of organising images.

Every Collection Tree may use different analysis modules and different internal hierarchy.

3. Collection Tree

A Collection Tree is a top-level branch of the physical collection.

Examples:

Anime
Monster Girls
Western Animation
Themes

All Collection Trees are equal.

None of them is globally superior to another.

4. Current Collection Trees
Anime

Purpose:

Organisation of anime and game-related universes.

Typical hierarchy:

Anime
└── Universe
    └── Character (optional)

Examples:

Genshin Impact
Blue Archive
Honkai
Pokemon

Character folders are enabled only for selected universes.

Monster Girls

Purpose:

Organisation by species.

Typical hierarchy:

Monster Girls
└── Species

Examples:

Angel
Demon
Kemono
Undead
Lamia
Harpy
Slime

Character hierarchy is not currently planned.

Western Animation

Purpose:

Organisation of western animated franchises.

Typical hierarchy:

Western Animation
└── Universe

Examples:

Disney
DreamWorks
Cartoon Network

Character folders are optional and disabled by default.

Themes

Purpose:

Fallback collection for images that do not belong to an established Collection Tree or for images intentionally organised by visual theme.

Examples:

Bikini
Christmas
Halloween
Maid
School Uniform
Beach

Themes is considered a valid final destination.

It is not an error state.

5. TODO Tree

TODO is not a Collection Tree.

TODO is a working area.

Images inside TODO are expected to:

enter the analysis pipeline,
receive classifications,
remain in TODO when no suitable destination exists,
return to TODO after manual user actions.

The project does not require TODO to become empty.

Permanent content inside TODO is expected.

6. Collection Classifier

The first classification stage determines which Collection Tree is most appropriate.

Output:

Anime
Monster Girls
Western Animation
Themes
Unknown

The Collection Classifier does not move files.

It only records its observations in the database.

7. Tree-specific Classifiers

After a Collection Tree has been identified, specialised classifiers may be executed.

Examples:

Anime

↓

Universe Analysis

↓

Character Analysis

Monster Girls

↓

Species Analysis

Themes

↓

Theme Analysis

Different Collection Trees may use different specialised modules.

8. Secondary Classifiers

Some Collection Trees support additional hierarchy.

Example:

Anime

↓

Universe

↓

Character

Character Analysis is optional.

Whether it is executed depends on Collection Tree configuration.

9. Collection Configuration

Every Collection Tree may define its own configuration.

Examples:

supported classifiers,
hierarchy depth,
automatic sorting rules,
optional modules,
confidence thresholds.

This allows new Collection Trees to be added without redesigning the project.

10. AutoSort Interaction

AutoSort never performs classification.

It evaluates database information together with Collection Tree configuration.

Sorting decisions are therefore independent from the analysis modules.

11. Extensibility

Future Collection Trees may be introduced without modifying existing architecture.

Examples:

Comics
Movies
Manga
Games
Original Characters

Each Collection Tree may define its own hierarchy and specialised modules.

12. Design Principles

The architecture follows these principles:

Modular design
One image = one physical file
Database is the source of truth
Collection Trees are independent
Analysis modules never perform sorting
AutoSort never performs analysis
Manual user actions always have priority
Every Collection Tree may evolve independently
End of DOC-001A