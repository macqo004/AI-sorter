from __future__ import annotations

from pathlib import Path

import pytest

from ai_sorter.renamer import (
    RemoveDuplicateImageExtensionRule,
    RemoveDuplicateSuffixRule,
    RemoveLeadingNonAlphanumericRule,
    RemoveTrailingNonAlphanumericRule,
    RenamerEngine,
)


def test_remove_duplicate_suffix() -> None:
    rule = RemoveDuplicateSuffixRule()
    assert rule.apply("furina (1).jpg") == "furina.jpg"
    assert rule.apply("furina [25].png") == "furina.png"
    assert rule.apply("furina {3}.webp") == "furina.webp"
    assert rule.apply("furina.jpg") == "furina.jpg"


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
    # Use the rule pipeline without requiring a real file.
    name = source.name
    for rule in engine.rules:
        name = rule.apply(name)
    assert name == "Furina (1).png"


def test_engine_auto_resolves_existing_destination(tmp_path: Path) -> None:
    source = tmp_path / " sample.txt"
    destination = tmp_path / "sample.txt"
    source.write_text("x", encoding="utf-8")
    destination.write_text("existing", encoding="utf-8")

    engine = RenamerEngine()
    proposals = engine.plan([source])
    assert len(proposals) == 1
    assert proposals[0].destination == tmp_path / "sample__dup-1.txt"
    assert "auto-conflict-resolution" in proposals[0].reason

    engine.execute(proposals)

    assert not source.exists()
    assert destination.read_text(encoding="utf-8") == "existing"
    assert (tmp_path / "sample__dup-1.txt").read_text(encoding="utf-8") == "x"


def test_engine_auto_resolves_proposal_collision(tmp_path: Path) -> None:
    first = tmp_path / " sample.txt"
    second = tmp_path / "_sample.txt"
    first.write_text("first", encoding="utf-8")
    second.write_text("second", encoding="utf-8")

    engine = RenamerEngine()
    proposals = engine.plan([first, second])

    assert [proposal.destination.name for proposal in proposals] == [
        "sample.txt",
        "sample__dup-1.txt",
    ]

    engine.execute(proposals)

    assert (tmp_path / "sample.txt").read_text(encoding="utf-8") == "first"
    assert (tmp_path / "sample__dup-1.txt").read_text(encoding="utf-8") == "second"
