from __future__ import annotations

from pathlib import Path

import pytest

from ai_sorter.renamer import (
    RemoveAutoConflictSuffixRule,
    RemoveCopySuffixRule,
    RemoveDuplicateImageExtensionRule,
    RemoveDuplicateSuffixRule,
    RemoveLeadingNonAlphanumericRule,
    RemoveLeadingSingleCharUnderscoreRule,
    RemoveTrailingNonAlphanumericRule,
    RenameProposal,
    RenamerEngine,
)


def test_remove_duplicate_suffix() -> None:
    rule = RemoveDuplicateSuffixRule()
    assert rule.apply("furina (1).jpg") == "furina.jpg"
    assert rule.apply("furina [25].png") == "furina.png"
    assert rule.apply("furina {3}.webp") == "furina.webp"
    assert rule.apply("4 (2) (1).jpg") == "4.jpg"
    assert rule.apply("4 (2) (1) [3].jpg") == "4.jpg"
    assert rule.apply("furina.jpg") == "furina.jpg"


def test_remove_copy_suffix() -> None:
    rule = RemoveCopySuffixRule()
    assert rule.apply("daneobrazu copy.jpg") == "daneobrazu.jpg"
    assert rule.apply("daneobrazu_copy.jpg") == "daneobrazu.jpg"
    assert rule.apply("daneobrazu-copy.jpg") == "daneobrazu.jpg"
    assert rule.apply("daneobrazu - Copy 2.jpg") == "daneobrazu.jpg"
    assert rule.apply("daneobrazu (copy 2).jpg") == "daneobrazu.jpg"
    assert rule.apply("daneobrazu (copy).jpg") == "daneobrazu.jpg"
    assert rule.apply("daneobrazu kopia.png") == "daneobrazu.png"
    assert rule.apply("daneobrazu_kopia.webp") == "daneobrazu.webp"
    assert rule.apply("copy.jpg") == "copy.jpg"
    assert rule.apply("kopia.jpg") == "kopia.jpg"



def test_remove_auto_conflict_suffix() -> None:
    rule = RemoveAutoConflictSuffixRule()
    assert rule.apply("sample_x.jpg") == "sample.jpg"
    assert rule.apply("sample_x01.jpg") == "sample.jpg"
    assert rule.apply("sample_x12.jpg") == "sample.jpg"
    assert rule.apply("sample_x2.jpg") == "sample.jpg"
    assert rule.apply("sample__dup-1.jpg") == "sample.jpg"
    assert rule.apply("sample__dup-25.jpg") == "sample.jpg"
    assert rule.apply("sample_xx.jpg") == "sample_xx.jpg"
    assert rule.apply("sample.jpg") == "sample.jpg"


def test_remove_leading_single_char_underscore() -> None:
    rule = RemoveLeadingSingleCharUnderscoreRule()
    assert rule.apply("a_fabjnfalfjan.jpg") == "fabjnfalfjan.jpg"
    assert rule.apply("Z_image.png") == "image.png"
    assert rule.apply("1_image.webp") == "image.webp"
    assert rule.apply("4_daneobrazu.jpg") == "daneobrazu.jpg"
    assert rule.apply("ab_image.jpg") == "ab_image.jpg"
    assert rule.apply("_image.jpg") == "_image.jpg"
    assert rule.apply("a__image.jpg") == "_image.jpg"


def test_remove_leading_non_alphanumeric() -> None:
    rule = RemoveLeadingNonAlphanumericRule()
    assert rule.apply("  __--sample.png") == "sample.png"
    assert rule.apply("---_ image.png") == "image.png"
    assert rule.apply("_001_test.webp") == "001_test.webp"
    assert rule.apply("---Furina.jpg") == "Furina.jpg"
    assert rule.apply("Furina_-test.jpg") == "Furina_-test.jpg"
    assert rule.apply("---.jpg") == "---.jpg"


def test_remove_trailing_non_alphanumeric() -> None:
    rule = RemoveTrailingNonAlphanumericRule()
    assert rule.apply("5_.jpg") == "5.jpg"
    assert rule.apply("5---.png") == "5.png"
    assert rule.apply("5___--_.webp") == "5.webp"
    assert rule.apply("Furina_-test.jpg") == "Furina_-test.jpg"
    assert rule.apply("---.jpg") == "---.jpg"


def test_remove_duplicate_image_extension() -> None:
    rule = RemoveDuplicateImageExtensionRule()
    assert rule.apply("5.jpg.png") == "5.png"
    assert rule.apply("image.jpeg.jpg") == "image.jpg"
    assert rule.apply("foo.webp.png") == "foo.png"
    assert rule.apply("foo.version.jpg") == "foo.version.jpg"
    assert rule.apply("foo.txt.jpg") == "foo.txt.jpg"
    assert rule.apply("foo.jpg") == "foo.jpg"


def test_rules_are_applied_sequentially() -> None:
    engine = RenamerEngine()
    source = Path(r"M:\anime\example\  Furina (1)__.jpg.png")
    name = source.name
    for rule in engine.rules:
        name = rule.apply(name)
    assert name == "Furina.jpg.png"



def test_engine_resolves_many_same_destination_conflicts_linearly(tmp_path: Path) -> None:
    base = tmp_path / "sample.jpg"
    existing_x01 = tmp_path / "sample_x01.jpg"
    existing_x02 = tmp_path / "sample_x02.jpg"
    base.write_text("base", encoding="utf-8")
    existing_x01.write_text("x01", encoding="utf-8")
    existing_x02.write_text("x02", encoding="utf-8")

    proposals = []
    for index in range(20):
        source = tmp_path / f" sample ({index}).jpg"
        source.write_text(str(index), encoding="utf-8")
        proposals.append(
            RenameProposal(
                source,
                base,
                "test",
                True,
                "test",
            )
        )

    existing_paths = {
        str(path.resolve()).casefold()
        for path in (base, existing_x01, existing_x02)
    }
    engine = RenamerEngine()
    resolved = engine._resolve_conflicts(proposals, existing_paths=existing_paths)

    assert [proposal.destination.name for proposal in resolved] == [
        f"sample_x{index:02d}.jpg" for index in range(3, 23)
    ]
    assert len({proposal.destination for proposal in resolved}) == 20


def test_engine_treats_existing_directory_as_conflict(tmp_path: Path) -> None:
    source = tmp_path / " sample.jpg"
    occupied_directory = tmp_path / "sample.jpg"
    source.write_text("x", encoding="utf-8")
    occupied_directory.mkdir()

    proposal = RenameProposal(
        source,
        occupied_directory,
        "test",
        True,
        "test",
    )
    existing_paths = {
        str(source.resolve()).casefold(),
        str(occupied_directory.resolve()).casefold(),
    }

    engine = RenamerEngine()
    resolved = engine._resolve_conflicts([proposal], existing_paths=existing_paths)

    assert len(resolved) == 1
    assert resolved[0].destination == tmp_path / "sample_x01.jpg"


def test_engine_auto_resolves_existing_destination(tmp_path: Path) -> None:
    source = tmp_path / " sample.txt"
    destination = tmp_path / "sample.txt"
    source.write_text("x", encoding="utf-8")
    destination.write_text("existing", encoding="utf-8")

    engine = RenamerEngine()
    proposals = engine.plan([source])
    assert len(proposals) == 1
    assert proposals[0].destination == tmp_path / "sample_x01.txt"
    assert "auto-conflict-resolution" in proposals[0].reason

    engine.execute(proposals)

    assert not source.exists()
    assert destination.read_text(encoding="utf-8") == "existing"
    assert (tmp_path / "sample_x01.txt").read_text(encoding="utf-8") == "x"


def test_engine_auto_resolves_proposal_collision(tmp_path: Path) -> None:
    first = tmp_path / " sample.txt"
    second = tmp_path / "_sample.txt"
    first.write_text("first", encoding="utf-8")
    second.write_text("second", encoding="utf-8")

    engine = RenamerEngine()
    proposals = engine.plan([first, second])

    assert [proposal.destination.name for proposal in proposals] == [
        "sample.txt",
        "sample_x01.txt",
    ]

    engine.execute(proposals)

    assert (tmp_path / "sample.txt").read_text(encoding="utf-8") == "first"
    assert (tmp_path / "sample_x01.txt").read_text(encoding="utf-8") == "second"


def test_engine_removes_own_conflict_suffix_when_base_is_free(tmp_path: Path) -> None:
    source = tmp_path / "sample_x01.jpg"
    source.write_text("x", encoding="utf-8")

    engine = RenamerEngine()
    proposals = engine.plan([source])

    assert len(proposals) == 1
    assert proposals[0].destination == tmp_path / "sample.jpg"


def test_engine_migrates_legacy_conflict_suffix_when_base_is_free(tmp_path: Path) -> None:
    source = tmp_path / "sample__dup-1.jpg"
    source.write_text("x", encoding="utf-8")

    engine = RenamerEngine()
    proposals = engine.plan([source])

    assert len(proposals) == 1
    assert proposals[0].destination == tmp_path / "sample.jpg"


def test_engine_migrates_legacy_conflict_suffix_when_base_is_occupied(tmp_path: Path) -> None:
    base = tmp_path / "sample.jpg"
    source = tmp_path / "sample__dup-1.jpg"
    base.write_text("base", encoding="utf-8")
    source.write_text("x", encoding="utf-8")

    engine = RenamerEngine()
    proposals = engine.plan([source])

    assert len(proposals) == 1
    assert proposals[0].destination == tmp_path / "sample_x01.jpg"


def test_engine_compacts_existing_conflict_suffix_gap(tmp_path: Path) -> None:
    base = tmp_path / "sample.jpg"
    x01 = tmp_path / "sample_x01.jpg"
    x05 = tmp_path / "sample_x05.jpg"
    x09 = tmp_path / "sample_x09.jpg"
    for path, value in ((base, "base"), (x01, "x01"), (x05, "x05"), (x09, "x09")):
        path.write_text(value, encoding="utf-8")

    engine = RenamerEngine()
    proposals = engine.plan([x01, x05, x09])

    assert [(proposal.source.name, proposal.destination.name) for proposal in proposals] == [
        ("sample_x05.jpg", "sample_x02.jpg"),
        ("sample_x09.jpg", "sample_x03.jpg"),
    ]


def test_engine_moves_high_conflict_suffix_to_smallest_free_slot(tmp_path: Path) -> None:
    base = tmp_path / "sample.jpg"
    x01 = tmp_path / "sample_x01.jpg"
    x02 = tmp_path / "sample_x02.jpg"
    x03 = tmp_path / "sample_x03.jpg"
    x04 = tmp_path / "sample_x04.jpg"
    x23 = tmp_path / "sample_x23.jpg"
    for path in (base, x01, x02, x03, x04, x23):
        path.write_text("x", encoding="utf-8")

    engine = RenamerEngine()
    proposals = engine.plan([x23])

    assert [(proposal.source.name, proposal.destination.name) for proposal in proposals] == [
        ("sample_x23.jpg", "sample_x05.jpg"),
    ]


def test_engine_uses_base_name_first_when_compacting_conflict_suffixes(tmp_path: Path) -> None:
    x05 = tmp_path / "sample_x05.jpg"
    x23 = tmp_path / "sample_x23.jpg"
    x05.write_text("x05", encoding="utf-8")
    x23.write_text("x23", encoding="utf-8")

    engine = RenamerEngine()
    proposals = engine.plan([x05, x23])

    assert [(proposal.source.name, proposal.destination.name) for proposal in proposals] == [
        ("sample_x05.jpg", "sample.jpg"),
        ("sample_x23.jpg", "sample_x01.jpg"),
    ]


def test_engine_compacts_conflict_group_with_generic_renames(tmp_path: Path) -> None:
    base = tmp_path / "sample.jpg"
    x23 = tmp_path / "sample_x23.jpg"
    generic = tmp_path / " sample.jpg"
    base.write_text("base", encoding="utf-8")
    x23.write_text("x23", encoding="utf-8")
    generic.write_text("generic", encoding="utf-8")

    engine = RenamerEngine()
    proposals = engine.plan([x23, generic])

    assert [(proposal.source.name, proposal.destination.name) for proposal in proposals] == [
        ("sample_x23.jpg", "sample_x01.jpg"),
        (" sample.jpg", "sample_x02.jpg"),
    ]

