AI Image Sorter
Project Specification
Version 0.1 (Draft)
1. Project Overview
1.1 Purpose

The purpose of this project is to build a fully offline, modular image cataloguing system capable of assisting with organizing very large collections of digital artwork.

The project is designed around collections containing millions of images and must prioritize:

stability,
modularity,
reproducibility,
easy testing,
incremental development.

The application is not intended to be a general-purpose image management software.

It is designed specifically around a predefined directory structure maintained by the user.

1.2 Primary Goals

The first development stages focus on creating a reliable image processing pipeline.

Expected functionality:

scan image collections,
build an image database,
calculate unique identifiers,
perform simple image classification,
prepare images for future AI processing.

Automatic character recognition is not a goal of the initial versions.

1.3 Long-Term Goals

Future versions should gradually introduce:

anime detection,
universe recognition,
character recognition,
general tag classification,
user feedback learning,
automatic file organization.

Each feature must remain independent from previous modules.

1.4 Project Philosophy

The project follows several non-negotiable principles.

Modularity

Every module has exactly one responsibility.

Examples:

Scanner:

scans files,
builds database.

B&W Filter:

detects monochrome images.

Mover:

moves files.

Rename:

renames files.

No module should perform responsibilities belonging to another module.

Offline First

The project must work completely offline.

No cloud services.

No online APIs.

No mandatory Internet connection.

All AI models must run locally.

Safety First

The application must never modify the user's original collection unless explicitly instructed.

Early project versions should be read-only whenever possible.

Destructive operations (move, rename, delete) will only be introduced after the earlier modules have been thoroughly tested.

Database First

The database is the source of truth.

Folders are only physical storage locations.

The application should never rely exclusively on folder names when making decisions.

Incremental Development

The project is intentionally divided into independent milestones.

Each completed milestone must provide useful functionality on its own.

Development may stop after any milestone without making previous work useless.

Example:

Scanner completed.

↓

Project already provides a searchable database.

Later modules only expand existing functionality.

1.5 Supported Environment

Operating system:

Windows 10
Windows 11

Primary database:

SQLite

Primary language:

Python

Primary execution:

local workstation

Internet:

optional

GPU:

optional

CPU execution must always be supported.

1.6 Supported Image Formats

Required:

JPG
JPEG
PNG
WEBP

Supported when encountered:

BMP
GIF
PNS (treated as PNG whenever possible)

Ignored:

MP4
WEBM
AVI
MKV
other video formats

Unsupported formats should be skipped without interrupting processing.

1.7 Initial Development Roadmap

Version 0.x consists of independent modules developed in order.

Phase 1

Scanner

Phase 2

B&W Filter

Phase 3

Screenshot Filter

Phase 4

Meme Filter

Phase 5

IRL Filter

Only after these five modules are considered stable will automatic image classification be introduced.

1.8 AI Introduction Policy

Artificial Intelligence is not part of the initial architecture.

AI modules may only appear after:

Scanner is completed,
database structure is stable,
simple filters are validated,
testing confirms reliable operation.

The project must never depend on AI to perform basic functionality.

1.9 Future AI Workflow

Future AI modules will classify only images located inside the TODO tree.

Images located in AI or FINAL trees are considered observation targets only.

Classification and monitoring are separate responsibilities.

1.10 Project Success Criteria

The project is considered successful if it can significantly reduce manual image sorting work.

Perfect classification accuracy is not required.

A success rate around 95% is considered acceptable when remaining errors can be corrected manually.

The project values stability and predictability over maximum automation.

End of Version 0.1