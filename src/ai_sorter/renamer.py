"""Deterministic filename renaming engine and built-in filename rules."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol

DUPLICATE_SUFFIX_RE = re.compile(r"(?:\s*\(\d+\)|\s*\[\d+\]|\s*\{\d+\})$")
DUPLICATE_IMAGE_EXTENSION_RE = re.compile(r"(?i)(\.(?:jpe?g|png|webp|gif|bmp|pns))$")
AUTO_CONFLICT_SUFFIX_RE = re.compile(r"(?i)_x(?:\d+)?$")
LEGACY_CONFLICT_SUFFIX_RE = re.compile(r"(?i)__dup-(\d+)$")
LEADING_SINGLE_CHAR_UNDERSCORE_RE = re.compile(r"^([^_\W])_")
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
    rule_id: str = "remove_duplicate_suffix"
    version: str = "1.1"

    def apply(self, filename: str) -> str:
        path = Path(filename)
        stem = path.stem
        suffix = path.suffix
        transformed = stem
        while True:
            next_stem = DUPLICATE_SUFFIX_RE.sub("", transformed)
            if next_stem == transformed:
                break
            transformed = next_stem
        if not transformed:
            return filename
        return f"{transformed}{suffix}"


@dataclass(frozen=True, slots=True)
class RemoveAutoConflictSuffixRule:
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
class RemoveLeadingSingleCharUnderscoreRule:
    rule_id: str = "remove_leading_single_char_underscore"
    version: str = "1.0"

    def apply(self, filename: str) -> str:
        path = Path(filename)
        stem = path.stem
        suffix = path.suffix
        transformed = LEADING_SINGLE_CHAR_UNDERSCORE_RE.sub("", stem, count=1)
        if not transformed:
            return filename
        return f"{transformed}{suffix}"


@dataclass(frozen=True, slots=True)
class RemoveLeadingNonAlphanumericRule:
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
    RemoveLeadingSingleCharUnderscoreRule(),
    RemoveLeadingNonAlphanumericRule(),
    RemoveTrailingNonAlphanumericRule(),
    RemoveDuplicateImageExtensionRule(),
)


class RenamerEngine:
    TEMP_PREFIX = ".asrtmp_"
    TEMP_SUFFIX = ".tmp"

    def __init__(self, rules: Iterable[FilenameRule] = DEFAULT_RULES) -> None:
        self.rules = tuple(rules)
        rule_ids = [rule.rule_id for rule in self.rules]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError("Duplicate rule_id in RenamerEngine configuration.")

    def propose(self, source: Path) -> RenameProposal | None:
        source = source.absolute()
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

    def plan(
        self,
        sources: Iterable[Path],
        *,
        existing_paths: set[str] | None = None,
    ) -> list[RenameProposal]:
        proposals: list[RenameProposal] = []
        for source in sources:
            proposal = self.propose(source)
            if proposal is not None and proposal.changed:
                proposals.append(proposal)
        return self._resolve_conflicts(proposals, existing_paths=existing_paths)

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

    @staticmethod
    def _conflict_sequence_index(path: Path) -> int | None:
        """Return the existing _xN slot number encoded in a filename, if any."""
        match = AUTO_CONFLICT_SUFFIX_RE.search(path.stem)
        if not match:
            return None
        digits = match.group(0)[2:]
        return int(digits) if digits else 0

    def _resolve_conflicts(
        self,
        proposals: Iterable[RenameProposal],
        *,
        existing_paths: set[str] | None = None,
    ) -> list[RenameProposal]:
        proposals = list(proposals)
        if not proposals:
            return []

        def path_exists(path: Path) -> bool:
            if existing_paths is not None:
                return self._path_key(path) in existing_paths
            return path.exists()

        # Every proposal whose transformed destination is the same path belongs
        # to one filename-conflict group.  Conflict suffixes (_xN) are
        # reversible positions, not permanent identities: the group is packed
        # into base, _x01, _x02, ... whenever possible.
        groups: dict[str, list[RenameProposal]] = {}
        for proposal in proposals:
            groups.setdefault(self._path_key(proposal.destination), []).append(proposal)

        resolved: list[RenameProposal] = []
        used_destinations: set[str] = set()

        def sort_key(proposal: RenameProposal) -> tuple[int, int, str]:
            slot = self._conflict_sequence_index(proposal.source)
            if slot is None:
                return (1, 0, self._path_key(proposal.source))
            return (0, slot, self._path_key(proposal.source))

        for destination_key in sorted(groups):
            group = sorted(groups[destination_key], key=sort_key)
            base = group[0].destination
            base_key = self._path_key(base)
            group_source_keys = {self._path_key(proposal.source) for proposal in group}
            base_occupied = path_exists(base) and base_key not in group_source_keys

            next_index = 1
            for position, proposal in enumerate(group):
                if not base_occupied and position == 0:
                    destination = base
                else:
                    while True:
                        destination = self._conflict_name(base, next_index)
                        next_index += 1
                        candidate_key = self._path_key(destination)

                        # A source belonging to this same conflict group will
                        # be moved/reassigned as part of this packing pass.
                        candidate_is_movable_source = candidate_key in group_source_keys
                        candidate_is_occupied = path_exists(destination) and not candidate_is_movable_source

                        if candidate_key in used_destinations:
                            continue
                        if candidate_is_occupied:
                            continue
                        break

                destination_key_for_proposal = self._path_key(destination)
                used_destinations.add(destination_key_for_proposal)

                source_key = self._path_key(proposal.source)
                if destination_key_for_proposal == source_key:
                    # The file already occupies its compact sequence slot.
                    # It remains physically unchanged and therefore needs no
                    # rename proposal.
                    continue

                reason = proposal.reason
                if destination != proposal.destination:
                    reason = f"{reason}, auto-conflict-resolution"
                resolved.append(
                    RenameProposal(
                        proposal.source,
                        destination,
                        proposal.rule_id,
                        proposal.changed,
                        reason,
                    )
                )

        self._validate_plan(resolved, existing_paths=existing_paths)
        return resolved

    def _validate_plan(
        self,
        proposals: Iterable[RenameProposal],
        *,
        existing_paths: set[str] | None = None,
    ) -> None:
        proposals = list(proposals)
        destinations: dict[str, RenameProposal] = {}
        sources = {self._path_key(proposal.source) for proposal in proposals if proposal.changed}

        def path_exists(path: Path) -> bool:
            if existing_paths is not None:
                return self._path_key(path) in existing_paths
            return path.exists()

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
            if path_exists(proposal.destination) and destination_key not in sources:
                raise FileExistsError(
                    f"Rename refused because destination already exists: {proposal.destination}"
                )

    @classmethod
    def _temporary_path(cls, source: Path, index: int) -> Path:
        return source.with_name(f"{cls.TEMP_PREFIX}{index:06d}{cls.TEMP_SUFFIX}")

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
                temporary_path = self._temporary_path(proposal.source, index)
                if temporary_path.exists():
                    raise FileExistsError(f"Temporary rename path already exists: {temporary_path}")
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
    """Return regular files below *root* with deterministic per-directory ordering."""
    root = root.absolute()
    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {root}")

    files: list[Path] = []
    for current_root, directories, filenames in os.walk(root, topdown=True):
        directories.sort(key=str.casefold)
        filenames.sort(key=str.casefold)
        current = Path(current_root)
        files.extend(current / name for name in filenames if (current / name).is_file())
        if not recursive:
            break
    return files
