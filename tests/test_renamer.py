from __future__ import annotations

from pathlib import Path

from ai_sorter.renamer import (
    RemoveDuplicateSuffixRule,
    RemoveLeadingNonAlphanumericRule,
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


def test_rules_are_applied_sequentially() -> None:
    engine = RenamerEngine()
    source = Path(r"M:\anime\example\  Furina (1).jpg")
    # Use the rule pipeline without requiring a real file.
    name = source.name
    for rule in engine.rules:
        name = rule.apply(name)
    assert name == "Furina.jpg"


def test_engine_rejects_destination_collision(tmp_path: Path) -> None:
    source = tmp_path / " sample.txt"
    destination = tmp_path / "sample.txt"
    source.write_text("x", encoding="utf-8")
    destination.write_text("existing", encoding="utf-8")

    engine = RenamerEngine()
    proposals = engine.plan([source])
    assert len(proposals) == 1

    try:
        engine.execute(proposals)
    except FileExistsError:
        pass
    else:
        raise AssertionError("Expected destination collision to be refused")

    assert source.exists()
    assert destination.read_text(encoding="utf-8") == "existing"
