#!/usr/bin/env python3
# scripts/gate_console_logs.py
# Replace `console.log(` with `dcLog(` in templates and static JS files.

import sys, os, re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
EXTS = ('.js', '.html', '.jsx', '.tsx')
SKIP_DIRS = {'.venv', 'node_modules', '.git', 'backup', 'backups', 'Artifacts', 'staticfiles', 'venv'}

pattern = re.compile(r"(?<!dcLog)\bconsole\.log\(")

# walk files
replacements = 0
for dirpath, dirnames, filenames in os.walk(ROOT):
    # skip directories that are not part of the repo code or are build artifacts
    if any(sd in dirpath for sd in SKIP_DIRS):
        continue
    for fname in filenames:
        if fname.endswith(EXTS):
            fpath = os.path.join(dirpath, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as fh:
                    text = fh.read()
                if 'console.log(' not in text:
                    continue
                # do replacement but keep track
                new_text = text
                new_text = pattern.sub('dcLog(', new_text)
                if new_text != text:
                    with open(fpath, 'w', encoding='utf-8') as fh:
                        fh.write(new_text)
                    replacements += 1
                    print('Updated:', fpath)
            except Exception as e:
                print('Skipping', fpath, 'due to', e)

print('Total replacements:', replacements)
