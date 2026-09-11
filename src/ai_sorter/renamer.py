"""Deterministic filename renaming engine and built-in filename rules."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol


DUPLICATE_SUFFIX_RE = re.compile(r"(?:\s*\(\d+\)|\s*\[\d+\]|\s*\{\d+\})$")
DUPLICATE_IMAGE_EXTENSION_RE = re.compile(
    r"(?i)(\.(?:jpe?g|png|webp|gif|bmp|pns))$"
)
AUTO_CONFLICT_SUFFIX_RE = re.compile(r"(?i)_x(?:\d+)?$")
LEGACY_CONFLICT_SUFFIX_RE = re.compile(r"(?i)__dup-(\d+)$")
IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".pns"})
MAX_FILENAME_LENGTH = 255
AUTO_CONFLICT_SUFFIX = "_x"


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
class RemoveAutoConflictSuffixRule:
    """Remove current or legacy AI-Sorter conflict suffixes; conflicts are re-applied by the engine."""

    rule_id: str = "remove_auto_conflict_suffix"
    version: str = "2.0"

    def apply(self, filename: str) -> str:
        path = Path(filename)
        stem = path.stem
        suffix = path.suffix
        transformed = AUTO_CONFLICT_SUFFIX_RE.sub("", stem)
        transformed = LEGACY_CONFLICT_SUFFIX_RE.sub("", transformed)
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


@dataclass(frozen=True, slots=True)
class RemoveTrailingNonAlphanumericRule:
    """Remove the complete trailing run of non-alphanumeric Unicode characters from the stem."""

    rule_id: str = "remove_trailing_non_alphanumeric"
    version: str = "1.0"

    def apply(self, filename: str) -> str:
        path = Path(filename)
        stem = path.stem
        suffix = path.suffix
        index = len(stem)
        while index > 0 and not stem[index - 1].isalnum():
            index -= 1
        if index == len(stem) or index == 0:
            return filename
        return f"{stem[:index]}{suffix}"


@dataclass(frozen=True, slots=True)
class RemoveDuplicateImageExtensionRule:
    """Remove a repeated known image extension immediately before the final extension."""

    rule_id: str = "remove_duplicate_image_extension"
    version: str = "1.0"

    def apply(self, filename: str) -> str:
        path = Path(filename)
        suffix = path.suffix
        if suffix.lower() not in IMAGE_EXTENSIONS:
            return filename
        stem = path.stem
        match = DUPLICATE_IMAGE_EXTENSION_RE.search(stem)
        if not match:
            return filename
        transformed = stem[: match.start()]
        if not transformed:
            return filename
        return f"{transformed}{suffix}"


DEFAULT_RULES: tuple[FilenameRule, ...] = (
    RemoveDuplicateSuffixRule(),
    RemoveAutoConflictSuffixRule(),
    RemoveLeadingNonAlphanumericRule(),
    RemoveTrailingNonAlphanumericRule(),
    RemoveDuplicateImageExtensionRule(),
)


class RenamerEngine:
    """Plan and safely execute deterministic filename transformations."""

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
        applied_rules: list[str] = []
        for rule in self.rules:
            next_name = rule.apply(transformed_name)
            if next_name != transformed_name:
                transformed_name = next_name
                applied_rules.append(f"{rule.rule_id}@{rule.version}")

        if transformed_name == current_name:
            return RenameProposal(source, source, "", False, "No rule matched")

        destination = source.with_name(transformed_name)
        reason = ", ".join(applied_rules)
        rule_id = "+".join(applied_rules)
        return RenameProposal(source, destination, rule_id, True, reason)

    def plan(self, sources: Iterable[Path]) -> list[RenameProposal]:
        proposals: list[RenameProposal] = []
        for source in sources:
            proposal = self.propose(source)
            if proposal is not None and proposal.changed:
                proposals.append(proposal)
        return self._resolve_conflicts(proposals)

    @staticmethod
    def _path_key(path: Path) -> str:
        return os.path.normcase(os.path.abspath(str(path)))

    @staticmethod
    def _conflict_name(destination: Path, index: int) -> Path:
        stem = destination.stem
        suffix = destination.suffix
        tag = f"_x{index:02d}"
        available_stem_length = max(1, MAX_FILENAME_LENGTH - len(suffix) - len(tag))
        trimmed_stem = stem[:available_stem_length]
        return destination.with_name(f"{trimmed_stem}{tag}{suffix}")

    def _resolve_conflicts(self, proposals: Iterable[RenameProposal]) -> list[RenameProposal]:
        proposals = list(proposals)
        sources = {self._path_key(proposal.source) for proposal in proposals}
        used_destinations: set[str] = set()
        resolved: list[RenameProposal] = []

        for proposal in proposals:
            destination = proposal.destination
            destination_key = self._path_key(destination)
            source_key = self._path_key(proposal.source)
            conflict = (
                destination_key in used_destinations
                or (destination.exists() and destination_key not in sources)
            )

            if conflict:
                index = 1
                while True:
                    candidate = self._conflict_name(destination, index)
                    candidate_key = self._path_key(candidate)
                    if candidate_key == source_key:
                        index += 1
                        continue
                    if (
                        candidate_key not in used_destinations
                        and not candidate.exists()
                        and candidate_key not in sources
                    ):
                        destination = candidate
                        destination_key = candidate_key
                        break
                    index += 1
                reason = f"{proposal.reason}, auto-conflict-resolution"
                proposal = RenameProposal(
                    proposal.source,
                    destination,
                    proposal.rule_id,
                    proposal.changed,
                    reason,
                )

            used_destinations.add(destination_key)
            resolved.append(proposal)

        self._validate_plan(resolved)
        return resolved

    def _validate_plan(self, proposals: Iterable[RenameProposal]) -> None:
        proposals = list(proposals)
        destinations: dict[str, RenameProposal] = {}
        sources = {self._path_key(proposal.source) for proposal in proposals if proposal.changed}
        for proposal in proposals:
            if not proposal.changed:
                continue
            destination_key = self._path_key(proposal.destination)
            previous = destinations.get(destination_key)
            if previous is not None:
                raise FileExistsError(
                    "Multiple rename proposals target the same destination: "
                    f"{previous.source} -> {previous.destination}; "
                    f"{proposal.source} -> {proposal.destination}"
                )
            destinations[destination_key] = proposal
            if proposal.destination.exists() and self._path_key(proposal.destination) not in sources:
                raise FileExistsError(
                    f"Rename refused because destination already exists: {proposal.destination}"
                )

    def execute(self, proposals: Iterable[RenameProposal]) -> list[RenameProposal]:
        proposals = [proposal for proposal in proposals if proposal.changed]
        self._validate_plan(proposals)
        for proposal in proposals:
            if not proposal.source.exists():
                raise FileNotFoundError(f"Rename refused because source disappeared: {proposal.source}")

        executed: list[RenameProposal] = []
        temporary: list[tuple[Path, Path, RenameProposal]] = []
        try:
            for index, proposal in enumerate(proposals):
                temporary_path = proposal.source.with_name(
                    f".{proposal.source.name}.ai-sorter-rename-{index}.tmp"
                )
                if temporary_path.exists():
                    raise FileExistsError(
                        f"Temporary rename path already exists: {temporary_path}"
                    )
                proposal.source.rename(temporary_path)
                temporary.append((temporary_path, proposal.destination, proposal))

            for temporary_path, destination, proposal in temporary:
                temporary_path.rename(destination)
                executed.append(proposal)
        except Exception:
            for temporary_path, destination, proposal in reversed(temporary):
                try:
                    if temporary_path.exists() and not proposal.source.exists():
                        temporary_path.rename(proposal.source)
                except OSError:
                    pass
            raise
        return executed


def iter_files(root: Path, *, recursive: bool = True) -> list[Path]:
    """Return regular files below *root*, sorted for deterministic planning."""
    root = root.resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {root}")
    paths = root.rglob("*") if recursive else root.glob("*")
    return sorted(
        (path for path in paths if path.is_file()),
        key=lambda path: str(path).lower(),
    )
