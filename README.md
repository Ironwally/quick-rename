# Quick-Rename

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

## Update installation on linux system

```bash
chmod +x ./quick-rename.py
cp ./quick-rename.py /usr/local/bin/
echo 'alias qr="quick-rename.py"' >> $HOME/.bashrc
```

## Examples

Remove spaces from filenames in a folder (non-recursive):

```bash
./quick-rename.py "\\s+" "_" ./photos
```

Recursively remove " copy" from names:

```bash
./quick-rename.py "\\s+copy" "" ./
```

Switch date format in filename from german to UTC

```bash
 ./quick-rename.py '(?P<day>\d{2})\.(?P<month>\d{2})\.(?P<year>\d{4})' '\g<year>-\g<month>-\g<day>' testenv/**
```
