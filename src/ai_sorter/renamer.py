"""Deterministic filename renaming engine and built-in filename rules."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol


DUPLICATE_SUFFIX_RE = re.compile(r"(?:\s*\(\d+\)|\s*\[\d+\]|\s*\{\d+\})$")


@dataclass(frozen=True, slots=True)
class RenameProposal:
    source: Path
    destination: Path
    rule_id: str
    changed: bool
    reason: str = ""


class FilenameRule(Protocol):
    rule_id: str
    version: str

    def apply(self, filename: str) -> str:
        """Return the transformed filename, or the original filename when unchanged."""


@dataclass(frozen=True, slots=True)
class RemoveDuplicateSuffixRule:
    """Remove explicit numeric copy suffixes from the filename stem."""

    rule_id: str = "remove_duplicate_suffix"
    version: str = "1.0"

    def apply(self, filename: str) -> str:
        path = Path(filename)
        stem = path.stem
        suffix = path.suffix
        transformed = DUPLICATE_SUFFIX_RE.sub("", stem)
        if not transformed:
            return filename
        return f"{transformed}{suffix}"


@dataclass(frozen=True, slots=True)
class RemoveLeadingNonAlphanumericRule:
    """Remove the complete leading run of non-alphanumeric Unicode characters."""

    rule_id: str = "remove_leading_non_alphanumeric"
    version: str = "1.0"

    def apply(self, filename: str) -> str:
        path = Path(filename)
        stem = path.stem
        suffix = path.suffix
        index = 0
        while index < len(stem) and not stem[index].isalnum():
            index += 1
        if index == 0 or index == len(stem):
            return filename
        return f"{stem[index:]}{suffix}"


DEFAULT_RULES: tuple[FilenameRule, ...] = (
    RemoveDuplicateSuffixRule(),
    RemoveLeadingNonAlphanumericRule(),
)


class RenamerEngine:
    """Plan and safely execute deterministic filename transformations.

    The engine never overwrites an existing destination. A rename is only performed
    when the transformed name differs from the current name and the destination does
    not already exist.
    """

    def __init__(self, rules: Iterable[FilenameRule] = DEFAULT_RULES) -> None:
        self.rules = tuple(rules)
        rule_ids = [rule.rule_id for rule in self.rules]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError("Duplicate rule_id in RenamerEngine configuration.")

    def propose(self, source: Path) -> RenameProposal | None:
        source = source.resolve()
        if not source.is_file():
            raise FileNotFoundError(f"Source file does not exist: {source}")

        current_name = source.name
        transformed_name = current_name
        applied_rule_ids: list[str] = []
        for rule in self.rules:
            next_name = rule.apply(transformed_name)
            if next_name != transformed_name:
                transformed_name = next_name
                applied_rule_ids.append(f"{rule.rule_id}@{rule.version}")

        if transformed_name == current_name:
            return RenameProposal(source, source, "", False, "No rule matched")

        destination = source.with_name(transformed_name)
        reason = ", ".join(applied_rule_ids)
        return RenameProposal(source, destination, reason.split("@", 1)[0] if len(applied_rule_ids) == 1 else "+".join(applied_rule_ids), True, reason)

    def plan(self, sources: Iterable[Path]) -> list[RenameProposal]:
        proposals: list[RenameProposal] = []
        for source in sources:
            proposal = self.propose(source)
            if proposal is not None and proposal.changed:
                proposals.append(proposal)
        return proposals

    def execute(self, proposals: Iterable[RenameProposal]) -> list[RenameProposal]:
        executed: list[RenameProposal] = []
        planned_destinations: set[Path] = set()
        for proposal in proposals:
            source = proposal.source
            destination = proposal.destination
            if not proposal.changed:
                continue
            if destination in planned_destinations:
                raise FileExistsError(f"Multiple rename proposals target the same destination: {destination}")
            if destination.exists():
                raise FileExistsError(
                    f"Rename refused because destination already exists: {destination}"
                )
            if not source.exists():
                raise FileNotFoundError(f"Rename refused because source disappeared: {source}")
            source.rename(destination)
            planned_destinations.add(destination)
            executed.append(proposal)
        return executed


def iter_files(root: Path, *, recursive: bool = True) -> list[Path]:
    """Return regular files below *root*, sorted for deterministic planning."""
    root = root.resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {root}")
    paths = root.rglob("*") if recursive else root.glob("*")
    return sorted((path for path in paths if path.is_file()), key=lambda path: str(path).lower())
