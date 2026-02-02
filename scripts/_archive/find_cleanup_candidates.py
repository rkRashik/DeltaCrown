import os
import sys
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
output = {
    'zero_byte': [],
    'nuls': [],
    'backup_patterns': [],
    'large_logs': [],
    'candidate_dirs': [],
}

backup_patterns = ['~', '.bak', '.old', '.orig', '.copy', '.backup', 'backup', 'BACKUP']

for p in root.rglob('*'):
    try:
        if p.is_symlink():
            continue
        if p.is_file():
            try:
                size = p.stat().st_size
            except Exception:
                size = None
            rel = str(p.relative_to(root)).replace('\\','/')
            if size == 0:
                output['zero_byte'].append(rel)
            # check for NUL bytes
            try:
                with p.open('rb') as f:
                    chunk = f.read(1024)
                    if b'\x00' in chunk:
                        output['nuls'].append(rel)
            except Exception:
                pass
            # check backup-like filenames
            lower = p.name.lower()
            for pat in backup_patterns:
                if lower.endswith(pat) or pat in lower:
                    # but ignore legitimate folders like backups/
                    output['backup_patterns'].append(rel)
                    break
            # large log files > 5MB
            if size and size > 5 * 1024 * 1024 and p.suffix in ('.log', '.txt'):
                output['large_logs'].append({'path': rel, 'size': size})
    except Exception:
        pass

# candidate dirs (common junk folders)
dirs = ['backups', 'template_archives', 'backups_old', 'Artifacts', 'backups', 'user_profile_legacy_v1']
for d in dirs:
    dir_path = root / d
    if dir_path.exists() and dir_path.is_dir():
        # find a few sample files
        sample = [str(p.relative_to(root)).replace('\\','/') for p in dir_path.rglob('*')][:20]
        output['candidate_dirs'].append({'dir': d, 'sample_count': len(sample), 'sample_files': sample[:10]})

outf = root / 'cleanup_candidates.json'
with outf.open('w', encoding='utf-8') as f:
    json.dump(output, f, indent=2)

print('WROTE', outf)
