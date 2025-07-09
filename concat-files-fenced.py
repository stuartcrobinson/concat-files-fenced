#!/usr/bin/env python3
"""
Concatenate text files recursively with syntax highlighting fences.

usage:

python3 nesl-test/concat-files-fenced.py /Users/stuart/repos/nesl-lang/nesl-test/tests/cases nesl-test/concatenated-test-cases.md
"""

import argparse
import sys
from pathlib import Path
from typing import Optional
import fnmatch


def is_binary_file(file_path: Path) -> bool:
    """Check if file is binary by looking for null bytes in first 8KB."""
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(8192)
            return b'\x00' in chunk
    except Exception:
        return True  # Assume binary if can't read


def should_skip_path(path: Path, gitignore_spec: Optional['PathSpec'], 
                     exclude_patterns: list[str], input_dir: Path) -> bool:
    """Determine if a path should be skipped."""
    rel_path = path.relative_to(input_dir)
    
    # Check gitignore patterns
    if gitignore_spec and gitignore_spec.match_file(str(rel_path)):
        return True
    
    # Check exclude patterns
    for pattern in exclude_patterns:
        if fnmatch.fnmatch(str(rel_path), pattern):
            return True
    
    return False


def process_file(file_path: Path, output_file, input_dir: Path, separator: str) -> bool:
    """Process a single file, writing to output. Returns True if processed."""
    if not file_path.is_file():
        return False
    
    if is_binary_file(file_path):
        return False
    
    rel_path = file_path.relative_to(Path.cwd()).as_posix()

    extension = file_path.suffix[1:] if file_path.suffix else 'txt'
    
    try:
        output_file.write(f"{separator} {rel_path}\n")
        output_file.write(f"```{extension}\n")
        
        last_char = '\n'
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                output_file.write(line)
                if line:
                    last_char = line[-1]
        
        # Ensure newline before closing fence
        if last_char != '\n':
            output_file.write('\n')
        
        output_file.write("```\n")
        return True
    except (OSError, IOError) as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return False





def main():
    parser = argparse.ArgumentParser(description='Concatenate text files with syntax fences')
    parser.add_argument('input_dir', help='Input directory to process')
    parser.add_argument('output_file', help='Output file path')
    parser.add_argument('--gitignore', action='store_true', 
                        help='Honor .gitignore patterns')
    parser.add_argument('--exclude', action='append', default=[], 
                        help='Exclude glob patterns (repeatable)')
    parser.add_argument('--separator', default='_' * 30, 
                        help='Custom separator (default: 30 underscores)')
    
    args = parser.parse_args()
    
    # input_dir = Path(args.input_dir).resolve()    # https://claude.ai/chat/437db461-bcef-4e45-b8d1-5f49602a9aa9
    input_dir = Path(args.input_dir)
    output_file = Path(args.output_file).resolve()
    
    # Validate paths
    if not input_dir.exists():
        print(f"Error: Input directory '{input_dir}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    if not input_dir.is_dir():
        print(f"Error: '{input_dir}' is not a directory", file=sys.stderr)
        sys.exit(1)
    
    # Prevent output file inside input directory
    try:
        output_file.relative_to(input_dir)
        print(f"Error: Output file cannot be inside input directory", file=sys.stderr)
        sys.exit(1)
    except ValueError:
        pass  # Good, output is outside input
    
    # Load gitignore if requested
    gitignore_spec = None
    if args.gitignore:
        try:
            import pathspec
            gitignore_path = input_dir / '.gitignore'
            if gitignore_path.exists():
                with open(gitignore_path, 'r', encoding='utf-8') as f:
                    patterns = f.read().splitlines()
                gitignore_spec = pathspec.PathSpec.from_lines('gitwildmatch', patterns)
        except ImportError:
            print("Error: pathspec library required for --gitignore option", file=sys.stderr)
            print("Install with: pip install pathspec", file=sys.stderr)
            sys.exit(1)
    
    # Collect and sort files
    files = []
    for item in input_dir.rglob('*'):
        if item.is_file() and not should_skip_path(item, gitignore_spec, 
                                                   args.exclude, input_dir):
            files.append(item)
    
    # Sort by relative path
    files.sort(key=lambda p: p.relative_to(input_dir).as_posix().lower())
    
    # Process files
    processed = 0
    skipped = 0
    
    with open(output_file, 'w', encoding='utf-8') as out:
        for file_path in files:
            if process_file(file_path, out, input_dir, args.separator):
                processed += 1
            else:
                skipped += 1
    
    print(f"Processed {processed} files, skipped {skipped}")


if __name__ == '__main__':
    main()