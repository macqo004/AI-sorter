DOC-301
Collection Definition Wizard

Project: AI Image Collection Management System

Document: DOC-301

Version: 1.0 Draft

Status: Design Specification

1. Purpose

Collection Definition Wizard is responsible for building and maintaining the logical structure of the user's image collection.

The wizard does not analyse images.

It analyses only the directory structure.

Its purpose is to teach the system:

which Collection Trees exist,
which branches represent classification,
where classification ends,
which directories are user-managed content.
2. Design Philosophy

The project must adapt to the user's collection.

The user should never be forced to manually edit configuration files describing hundreds or thousands of folders.

Instead, the system learns the collection structure directly from the existing directory tree.

3. Collection Definition

The generated configuration describes only logical structure.

It never contains image information.

Example:

Anime
└── Games
    └── Hoyoverse
        └── Genshin Impact
            └── Furina

The wizard stores only the hierarchy.

Images are ignored.

4. First Run

During the first execution:

User selects one or more Collection Tree roots.
Wizard scans the directory structure.
Wizard builds a temporary hierarchy.
Wizard presents the hierarchy.
User defines Classification Boundaries.
Configuration is saved.

No image analysis is performed.

5. Classification Boundary

A Classification Boundary defines the last directory considered part of the logical collection structure.

Everything below that point belongs to the user.

Example:

Anime
└── Games
    └── Hoyoverse
        └── Genshin Impact
            └── Furina   ← Classification Boundary
                ├── 001
                ├── 002
                ├── 003
                └── Favorites

Directories:

001
002
003
Favorites

are ignored by Collection Definition Wizard.

They are considered user organisation only.

6. Boundary Types

Every Classification Boundary has a type.

Examples:

Character

Anime
└── Genshin Impact
    └── Furina

Species

Monster Girls
└── Angel

Universe

Western Animation
└── Disney

Theme

Themes
└── Bikini

The boundary type is stored together with the configuration.

7. User Interface

The Wizard presents the directory tree visually.

Example:

Anime
└── Games
    └── Hoyoverse
        └── Genshin Impact
            └── Furina
                ├── 001
                ├── 002
                └── 003

User selects:

✓ Furina

Boundary Type:
Character

Only one click is required.

8. Generated Configuration

The Wizard generates the internal collection configuration.

The implementation format is intentionally unspecified.

JSON is currently considered the preferred format.

Configuration files are generated automatically.

Manual editing is optional.

9. Collection Updates

Collection structure changes over time.

The Wizard supports incremental updates.

Example:

Initial structure:

Anime
└── Games
    └── Hoyoverse
        └── Genshin Impact

Later:

Anime
└── Games
    ├── Hoyoverse
    │   ├── Genshin Impact
    │   └── Honkai Star Rail
    └── Nintendo

Only new branches are analysed.

Existing branches remain unchanged.

10. Boundary Protection

Already defined Classification Boundaries are never automatically modified.

Example:

Previously defined:

Furina

During later scans:

Furina
├── 001
├── 002
├── 003
└── New Set

The Wizard completely ignores those directories.

User configuration always has priority.

11. New Branch Detection

When a previously unknown branch is detected:

Example:

Anime
└── Games
    └── Hoyoverse
        └── Zenless Zone Zero

The Wizard reports:

New branch detected:

Anime
→ Games
→ Hoyoverse
→ Zenless Zone Zero

Configure now?

[Yes]

[Later]

[Ignore]

Only the new branch is presented.

Previously configured branches remain hidden.

12. Manual Changes

Users may manually reorganise directories.

The Wizard never assumes automatic meaning.

Every newly discovered branch requires user confirmation.

13. Relationship with AutoSort

AutoSort never scans directory structure.

It relies entirely on Collection Definition.

If a folder does not exist in Collection Definition, AutoSort treats it as unavailable.

This prevents accidental creation of unwanted directory structures.

14. Relationship with Analysis Modules

Analysis modules may recognise:

Universe
Character
Species
Theme

However, recognised objects become valid AutoSort destinations only if they exist inside Collection Definition.

Example:

AI detects:

Winx Club
Confidence:
0.99

Collection Definition:

Winx Club

does not exist.

Result:

No automatic move is performed.

Observation is stored in the database only.

15. Design Principles

Collection Definition Wizard:

never analyses images;
never analyses metadata;
never creates folders automatically;
never guesses Classification Boundaries;
never modifies existing boundaries;
always requires user confirmation for new branches.
16. Future Extensions

Possible future features:

Import existing folder structures.
Export configuration.
Compare multiple collections.
Detect renamed branches.
Merge configurations.
Version history.
17. Acceptance Criteria

Collection Definition Wizard is considered complete when it:

learns collection hierarchy;
supports Classification Boundaries;
protects existing user configuration;
detects only new branches during updates;
generates configuration automatically;
requires no manual editing of configuration files during normal operation.
End of DOC-301