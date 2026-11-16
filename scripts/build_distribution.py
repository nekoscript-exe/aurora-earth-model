"""Build an allowlisted, content-verified real-data demo without modifying sources."""
import argparse
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT/'src'))
from aurora.distribution import build_demo, zip_demo
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--wheelhouse', type=Path)
    args = parser.parse_args()
    manifest = build_demo(args.root, args.output, args.wheelhouse)
    if args.archive: zip_demo(args.output, args.archive)
    print(f"Packaged {len(manifest['files'])} files; real Querétaro observations; four trained models.")
