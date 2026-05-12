# Quick Rename

Rename files (and optionally directories) by applying a regex substitution to each
item's name.

Positional arguments:

  1) REGEX: Python regex pattern applied to each basename
  2) REPLACEMENT (optional): replacement string for re.sub (default: "")
  3) PATH: Wildcard path to files and folders to rename
  
Options:
  -r/--recursive   Recurse into subdirectories when PATH is a directory
  --rename-dirs    Also rename directories
  -d/--dry-run     Show what would be renamed, but do not rename
  -f/--force       Actually rename. Don't only show what would be renamed
  -h/--help        Show this help text

## Examples

Remove spaces from filenames in a folder (non-recursive):

```bash
./rename.py "\\s+" "_" ./photos
```

Recursively remove " copy" from names:

```bash
./rename.py "\\s+copy" "" ./
```

Switch date format in filename from german to UTC

```bash
 ./rename.py '(?P<day>\d{2})\.(?P<month>\d{2})\.(?P<year>\d{4})' '\g<year>-\g<month>-\g<day>' testenv/**
```
