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
  -f/--force       Actually rename. Don't only show what would be renamed
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
import logging
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class RenameOp:
	src: Path
	dst: Path

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))
logging.basicConfig(filename='rename.log', level=logging.INFO)

def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    prog="regex_rename_recursive.py",
    description=(
      "Rename files (IN CURRENT FOLDER) (and optionally directories) by applying a regex substitution to each item's name."
    ),
  )
  parser.add_argument(
    "pattern",
    help="Regex pattern to replace in each basename",
  )
  parser.add_argument(
    "replacement",
    help="Replacement string for re.sub (default: '')",
  )
  parser.add_argument(
    "path",
    nargs="+",
    help="Wildcard path to files and folders to rename",
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
  parser.add_argument(
    "-f",
    "--force",
    action="store_true",
    help="Actually rename files"
  )
  parser.add_argument(
    "-v",
    "--verbose",
    action="store_true",
    help="Print more logs."
  )

  # Support `help` as a first positional argument (e.g. `./regex_rename_recursive.py help`).
  if argv is None:
    argv = sys.argv[1:]
  if len(argv) == 1 and argv[0].lower() == "help":
    parser.print_help()
    parser.exit(0)

  args = parser.parse_args(argv)

  try:
    re.compile(args.pattern)
  except re.error as exc:
    parser.error(f"Invalid REGEX: {exc}")

  return args

def _plan_changes(pattern: str, replacement: str, paths: list[Path]):
  new_names = {}
  for path in paths:
    basename=path.name
    
    # replace string
    new_name = re.sub(pattern, replacement, basename)
    
    if new_name != basename:
      new_path=path.with_name(new_name) 
      new_names[path] = new_path
  return new_names

def main(argv: Sequence[str] | None = None) -> int:
  args = _parse_args(argv)
  
  logger.debug('Starting')
  # logging
  if args.verbose:
    logger.setLevel(logging.DEBUG)
  
  logger.debug(f"Passed args: \n{args}")
  
  globbed_paths = []
  for path in args.path:
    globbed_paths += glob.glob(path) 
  
  paths=[Path(path) for path in globbed_paths]
  changes = _plan_changes(args.pattern, args.replacement, paths)
  
  # Check if new names are valid paths
  
  logger.info("changes:")
  for old_name, new_name in changes.items():
    logger.info(f"{old_name} -> {new_name}")
    if os.path.exists(new_name):
      logger.info(f"Error: {new_name} already exists")
      return 2
    
  if args.dry_run or not args.force:
    logger.debug('Finished dry-run only')
    return 0
  
  logger.debug("renaming")
  for old_name, new_name in changes.items():
    os.rename(old_name, new_name)
  
  logger.debug('Finished renaming')
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
