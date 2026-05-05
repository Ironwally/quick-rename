#!/usr/bin/env python3

"""regex_rename_recursive

Rename files (and optionally directories) by applying a regex substitution to each
item's name.

Positional arguments:
  1) PATH: Wildcard path to files and folders to rename
  2) REGEX: Python regex pattern applied to each basename
  3) REPLACEMENT (optional): replacement string for re.sub (default: "")

Options:
  -r/--recursive   Recurse into subdirectories when PATH is a directory
  --rename-dirs    Also rename directories
  -d/--dry-run     Show what would be renamed, but do not rename
  -h/--help        Show this help text

Examples:
  # remove spaces from filenames in a folder (non-recursive)
  python regex_rename_recursive.py ./photos "\\s+" "_" -d

  # recursively remove " copy" from names
  python regex_rename_recursive.py ./ "\\s+copy" "" -r
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True)
class RenameOp:
	src: Path
	dst: Path


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    prog="regex_rename_recursive.py",
    description=(
      "Rename files (and optionally directories) by applying a regex substitution to each item's name."
    ),
  )
  parser.add_argument(
    "path",
    help="Wildcard path to files and folders to rename",
  )
  parser.add_argument("regex", help="Python regex pattern applied to each basename")
  parser.add_argument(
    "replacement",
    nargs="?",
    default="",
    help="Replacement string for re.sub (default: '')",
  )
  parser.add_argument(
    "-r",
    "--recursive",
    action="store_true",
    help="Recurse into subdirectories when PATH is a directory",
  )
  parser.add_argument(
    "--rename-dirs",
    action="store_true",
    help="Also rename directories",
  )
  parser.add_argument(
    "-d",
    "--dry-run",
    action="store_true",
    help="Ony show what would be renamed, but do not rename",
  )

  # Support `help` as a first positional argument (e.g. `./regex_rename_recursive.py help`).
  if argv is None:
    argv = sys.argv[1:]
  if len(argv) == 1 and argv[0].lower() == "help":
    parser.print_help()
    parser.exit(0)

  args = parser.parse_args(argv)

  try:
    re.compile(args.regex)
  except re.error as exc:
    parser.error(f"Invalid REGEX: {exc}")

  return args


def _expand_glob(path_glob: str) -> list[Path]:
  matches = glob.glob(path_glob)
  return [Path(m).absolute() for m in matches]


def _iter_targets_in_dir(dir_path: Path, *, recursive: bool, rename_dirs: bool) -> Iterable[Path]:
  # Always include files in the folder set by the glob.
  # Include directories only if --rename-dirs is set.
  # Include paths in subdirectories only if --recursive is set.
  if recursive:
    for root, dir_names, file_names in os.walk(dir_path, followlinks=False):
      root_path = Path(root)
      for name in sorted(file_names):
        yield (root_path / name).absolute()
      if rename_dirs:
        for name in sorted(dir_names):
          yield (root_path / name).absolute()
    return

  for child in sorted(dir_path.iterdir(), key=lambda p: p.name):
    child_abs = child.absolute()
    if child.is_file():
      yield child_abs
    elif rename_dirs and child.is_dir():
      yield child_abs


def _collect_targets(roots: Sequence[Path], *, recursive: bool, rename_dirs: bool) -> list[Path]:
  seen: set[Path] = set()
  targets: list[Path] = []
  for root in roots:
    if root.is_dir():
      for p in _iter_targets_in_dir(root, recursive=recursive, rename_dirs=rename_dirs):
        if p not in seen:
          seen.add(p)
          targets.append(p)
    else:
      p = root.absolute()
      if p not in seen:
        seen.add(p)
        targets.append(p)
  return targets


def _validate_new_name(name: str) -> None:
  if name in {"", ".", ".."}:
    raise ValueError("replacement produced an invalid empty/dot name")
  if "\x00" in name:
    raise ValueError("replacement produced an invalid name containing NUL")
  seps = {os.sep}
  if os.altsep:
    seps.add(os.altsep)
  if any(sep in name for sep in seps):
    raise ValueError("replacement produced an invalid name containing path separators")


def _plan_ops(targets: Sequence[Path], *, pattern: re.Pattern[str], replacement: str) -> list[RenameOp]:
  ops: list[RenameOp] = []
  for src in targets:
    new_name = pattern.sub(replacement, src.name)
    _validate_new_name(new_name)
    try:
      dst = src.with_name(new_name)
    except ValueError as exc:
      raise ValueError(f"replacement produced an invalid name for {src}: {exc}") from exc
    ops.append(RenameOp(src=src, dst=dst))
  return ops


def _group_ops_by_parent(ops: Sequence[RenameOp]) -> dict[Path, list[RenameOp]]:
  groups: dict[Path, list[RenameOp]] = {}
  for op in ops:
    groups.setdefault(op.src.parent, []).append(op)
  for parent in groups:
    groups[parent].sort(key=lambda o: str(o.src))
  return groups


def _execute_group(parent: Path, ops: Sequence[RenameOp]) -> None:
  # Execute a safe rename within a single parent directory.
  # Two-phase rename via temporary names prevents collisions and cycles.
  ops_to_do = [op for op in ops if op.src != op.dst]
  if not ops_to_do:
    return

  sources = {op.src for op in ops_to_do}
  dests = [op.dst for op in ops_to_do]
  if len(set(dests)) != len(dests):
    raise RuntimeError(f"Destination name collision in {parent}")

  for dst in dests:
    if dst.exists() and dst not in sources:
      raise RuntimeError(f"Destination already exists: {dst}")

  used_names = {p.name for p in sources} | {p.name for p in dests}
  tmp_for_src: dict[Path, Path] = {}
  for op in ops_to_do:
    while True:
      tmp_name = f".__rrr_tmp_{uuid.uuid4().hex}__"
      if tmp_name in used_names:
        continue
      tmp_path = parent / tmp_name
      if tmp_path.exists():
        continue
      used_names.add(tmp_name)
      tmp_for_src[op.src] = tmp_path
      break

  # Phase 1: move sources out of the way.
  for op in ops_to_do:
    tmp_path = tmp_for_src[op.src]
    try:
      op.src.rename(tmp_path)
    except OSError as exc:
      raise RuntimeError(f"Failed renaming {op.src} -> {tmp_path}: {exc}") from exc

  # Phase 2: move temps to final destinations.
  for op in ops_to_do:
    tmp_path = tmp_for_src[op.src]
    try:
      tmp_path.rename(op.dst)
    except OSError as exc:
      raise RuntimeError(f"Failed renaming {tmp_path} -> {op.dst}: {exc}") from exc


def main(argv: Sequence[str] | None = None) -> int:
  args = _parse_args(argv)
  
  roots = _expand_glob(args.path)
  if not roots:
    print(f"No matches for PATH glob: {args.path}", file=sys.stderr)
    return 2

  targets = _collect_targets(roots, recursive=args.recursive, rename_dirs=args.rename_dirs)
  if not targets:
    print(f"No rename targets found under: {args.path}", file=sys.stderr)
    return 2

  pattern = re.compile(args.regex)
  try:
    ops = _plan_ops(targets, pattern=pattern, replacement=args.replacement)
  except ValueError as exc:
    print(f"Error planning rename operations: {exc}", file=sys.stderr)
    return 2

  # Always print: original name -> new name
  for op in sorted(ops, key=lambda o: str(o.src)):
    print(f"{op.src} -> {op.dst}")

  if args.dry_run:
    return 0

  groups = _group_ops_by_parent(ops)
  parents_by_depth = sorted(groups.keys(), key=lambda p: len(p.parts), reverse=True)
  try:
    for parent in parents_by_depth:
      _execute_group(parent, groups[parent])
  except RuntimeError as exc:
    print(str(exc), file=sys.stderr)
    return 1

  return 0


if __name__ == "__main__":
  raise SystemExit(main())
