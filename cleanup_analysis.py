#!/usr/bin/env python3
"""
DeltaCrown Project Cleanup Script
Identifies and reports potential cleanup candidates.
"""

import os
import sys
from pathlib import Path
from typing import List, Set, Dict, Tuple

# Add Django project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def get_python_files() -> List[Path]:
    """Get all Python files in the project."""
    python_files = []
    for root, dirs, files in os.walk(project_root):
        # Skip these directories
        skip_dirs = {'.git', '__pycache__', '.venv', 'venv', 'env', 'node_modules', 'staticfiles'}
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)
    return python_files

def find_test_files() -> Dict[str, List[Path]]:
    """Categorize test files."""
    test_files = {
        'test_files': [],
        'debug_files': [],
        'temp_files': [],
        'example_files': [],
    }
    
    for root, dirs, files in os.walk(project_root):
        skip_dirs = {'.git', '__pycache__', '.venv', 'venv', 'env', 'node_modules', 'staticfiles'}
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            file_path = Path(root) / file
            filename_lower = file.lower()
            
            # Test files
            if (filename_lower.startswith('test_') or 
                filename_lower.endswith('_test.py') or
                'test' in filename_lower):
                test_files['test_files'].append(file_path)
            
            # Debug files
            elif (filename_lower.startswith('debug_') or
                  'debug' in filename_lower):
                test_files['debug_files'].append(file_path)
            
            # Temporary files
            elif (filename_lower.endswith('.tmp') or
                  filename_lower.endswith('.bak') or
                  filename_lower.startswith('temp_') or
                  filename_lower.startswith('tmp_')):
                test_files['temp_files'].append(file_path)
            
            # Example files
            elif ('example' in filename_lower or
                  'sample' in filename_lower):
                test_files['example_files'].append(file_path)
    
    return test_files

def find_large_files(size_limit_mb: int = 1) -> List[Tuple[Path, int]]:
    """Find files larger than size_limit_mb."""
    large_files = []
    size_limit_bytes = size_limit_mb * 1024 * 1024
    
    for root, dirs, files in os.walk(project_root):
        skip_dirs = {'.git', '__pycache__', '.venv', 'venv', 'env', 'node_modules'}
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            file_path = Path(root) / file
            try:
                file_size = file_path.stat().st_size
                if file_size > size_limit_bytes:
                    large_files.append((file_path, file_size))
            except OSError:
                continue
    
    return sorted(large_files, key=lambda x: x[1], reverse=True)

def analyze_duplicate_imports():
    """Find potential duplicate imports across files."""
    print("\n=== Analyzing for duplicate imports ===")
    
    python_files = get_python_files()
    import_patterns = {}
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
            for line_num, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith('from ') or stripped.startswith('import '):
                    if stripped in import_patterns:
                        import_patterns[stripped].append((file_path, line_num))
                    else:
                        import_patterns[stripped] = [(file_path, line_num)]
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    
    # Report most common imports
    common_imports = {k: v for k, v in import_patterns.items() if len(v) > 10}
    if common_imports:
        print(f"Found {len(common_imports)} imports used in 10+ files")
        for imp, locations in sorted(common_imports.items(), key=lambda x: len(x[1]), reverse=True)[:5]:
            print(f"  '{imp}' used in {len(locations)} files")

def main():
    print("DeltaCrown Project Cleanup Analysis")
    print("=" * 50)
    
    # Analyze test files
    test_files = find_test_files()
    
    print(f"\n=== Test & Debug Files ===")
    for category, files in test_files.items():
        if files:
            print(f"{category.replace('_', ' ').title()}: {len(files)} files")
            for file in files[:5]:  # Show first 5
                print(f"  - {file.relative_to(project_root)}")
            if len(files) > 5:
                print(f"  ... and {len(files) - 5} more")
        else:
            print(f"{category.replace('_', ' ').title()}: None found")
    
    # Analyze large files
    print(f"\n=== Large Files (>1MB) ===")
    large_files = find_large_files(1)
    if large_files:
        for file_path, size in large_files[:10]:
            size_mb = size / (1024 * 1024)
            print(f"  {size_mb:.1f}MB - {file_path.relative_to(project_root)}")
    else:
        print("No files larger than 1MB found")
    
    # Analyze Python files
    python_files = get_python_files()
    print(f"\n=== Python Files Summary ===")
    print(f"Total Python files: {len(python_files)}")
    
    # Count lines in Python files
    total_lines = 0
    large_py_files = []
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = len(f.readlines())
                total_lines += lines
                
                if lines > 500:
                    large_py_files.append((file_path, lines))
        except Exception:
            continue
    
    print(f"Total lines of Python code: {total_lines:,}")
    
    if large_py_files:
        print(f"\nLarge Python files (>500 lines):")
        for file_path, lines in sorted(large_py_files, key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {lines:4d} lines - {file_path.relative_to(project_root)}")
    
    analyze_duplicate_imports()
    
    # Recommendations
    print(f"\n=== Cleanup Recommendations ===")
    recommendations = []
    
    if test_files['debug_files']:
        recommendations.append(f"Consider removing {len(test_files['debug_files'])} debug files")
    
    if test_files['temp_files']:
        recommendations.append(f"Clean up {len(test_files['temp_files'])} temporary files")
    
    if large_py_files:
        recommendations.append(f"Consider breaking down {len([f for f in large_py_files if f[1] > 1000])} very large files (>1000 lines)")
    
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}")
    else:
        print("Code organization looks good!")
    
    print(f"\nAnalysis complete. Project appears to have {len(python_files)} Python files totaling {total_lines:,} lines.")

if __name__ == "__main__":
    main()