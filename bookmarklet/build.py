#!/usr/bin/env python3
"""Build script to minify claude_extractor.js into bookmarklet format."""
import sys
from pathlib import Path

try:
    from jsmin import jsmin
except ImportError:
    print("Error: jsmin not installed. Install with: pip install jsmin")
    sys.exit(1)


def build_bookmarklet():
    """Minify claude_extractor.js and generate bookmarklet .txt file."""
    script_dir = Path(__file__).parent
    js_file = script_dir / "claude_extractor.js"
    txt_file = script_dir / "claude_extractor_bookmarklet.txt"

    if not js_file.exists():
        print(f"Error: {js_file} not found")
        sys.exit(1)

    # Read the JavaScript file
    with open(js_file, "r", encoding="utf-8") as f:
        js_code = f.read()

    # Minify the code
    minified = jsmin(js_code)

    # Add the javascript: prefix for bookmarklet
    bookmarklet = f"javascript:{minified}"

    # Write the bookmarklet
    with open(txt_file, "w", encoding="utf-8") as f:
        f.write(bookmarklet)

    print(f"✓ Generated bookmarklet: {txt_file}")
    print(f"  Size: {len(bookmarklet):,} characters")
    print(f"  Original: {len(js_code):,} characters")
    print(f"  Reduction: {100 * (1 - len(bookmarklet) / len(js_code)):.1f}%")


if __name__ == "__main__":
    build_bookmarklet()
