#!/usr/bin/env python3
"""
Merge new VM collection results into vm-data-consolidated.json.

Takes one or more results JSON files (already sanitized by collect-vm-info.yml)
and merges them into the consolidated file. Existing hosts with the same name
are replaced with the newer data.

Usage:
    python merge-vm-data.py 2510.json [-o vm-data-consolidated.json]
    python merge-vm-data.py region1.json region2.json -o vm-data-consolidated.json

Examples:
    # Merge new 25.10 data into the default consolidated file:
    python merge-vm-data.py 2510.json

    # Merge multiple files, writing to a specific output:
    python merge-vm-data.py results_alma.json results_azlinux.json -o vm-data-consolidated.json

    # Dry run — show what would change without writing:
    python merge-vm-data.py 2510.json --dry-run
"""

import json
import argparse
import sys
import os


def load_json(filepath):
    """Load and return parsed JSON from a file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(
        description="Merge new VM results into vm-data-consolidated.json."
    )
    parser.add_argument(
        "files",
        nargs="+",
        help="One or more JSON files with new/updated VM data",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="vm-data-consolidated.json",
        help="Output file (default: vm-data-consolidated.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing",
    )

    args = parser.parse_args()

    # Validate input files exist
    for f in args.files:
        if not os.path.isfile(f):
            print(f"Error: File not found: {f}", file=sys.stderr)
            sys.exit(1)

    # Load existing consolidated file if it exists
    if os.path.isfile(args.output):
        print(f"Loading existing: {args.output}")
        consolidated = load_json(args.output)
    else:
        print(f"Creating new: {args.output}")
        consolidated = {"_meta": {}, "hosts": {}}

    existing_hosts = set(consolidated.get("hosts", {}).keys())
    added = []
    updated = []

    # Merge each input file
    for filepath in args.files:
        print(f"Processing: {filepath}")
        new_data = load_json(filepath)
        new_hosts = new_data.get("hosts", {})

        for name, host_data in new_hosts.items():
            if name in consolidated["hosts"]:
                updated.append(name)
            else:
                added.append(name)
            consolidated["hosts"][name] = host_data

        print(f"  {len(new_hosts)} hosts from {filepath}")

    # Update _meta
    total = len(consolidated["hosts"])
    consolidated["_meta"] = {
        "description": f"Consolidated VM reference data - {total} Azure images",
        "total_hosts": total,
    }

    # Report
    print(f"\nSummary:")
    print(f"  Total hosts: {total}")
    if added:
        print(f"  Added ({len(added)}): {', '.join(sorted(added))}")
    if updated:
        print(f"  Updated ({len(updated)}): {', '.join(sorted(updated))}")
    if not added and not updated:
        print("  No changes")

    if args.dry_run:
        print("\n(dry run — no file written)")
        return

    # Write output
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(consolidated, f, indent=2, default=str)

    size_kb = os.path.getsize(args.output) / 1024
    print(f"\nWritten: {args.output} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
