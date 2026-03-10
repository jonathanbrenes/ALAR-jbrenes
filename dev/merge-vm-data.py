#!/usr/bin/env python3
"""
Merge new VM collection results into vm-data-consolidated.json.

Takes one or more results JSON files (from collect-vm-info.yml playbook)
and merges them into the consolidated file. Each VM is keyed by its
Ansible inventory hostname, preserving the original playbook output format.

Usage:
    python merge-vm-data.py results.json [-o vm-data-consolidated.json]
    python merge-vm-data.py region1.json region2.json -o vm-data-consolidated.json

Examples:
    # Merge new results into the default consolidated file:
    python merge-vm-data.py results.json

    # Merge multiple files, writing to a specific output:
    python merge-vm-data.py results_alma.json results_azlinux.json -o vm-data-consolidated.json

    # Dry run — show what would change without writing:
    python merge-vm-data.py results.json --dry-run
"""

import json
import argparse
import sys
import os


def load_json(filepath):
    """Load and return parsed JSON from a file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def get_host_summary(host_data):
    """Extract a short description of a host for logging."""
    compute = host_data.get("imds", {}).get("compute", {})
    publisher = compute.get("publisher", "")
    sku = compute.get("sku", "")
    root_disk = host_data.get("disk", {}).get("root_disk", "")
    transport = "nvme" if root_disk.startswith("nvme") else "scsi"
    return f"{publisher}/{sku} ({transport})" if publisher else "(no IMDS)"


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

    added = []
    updated = []

    # Merge each input file (hostname keys preserved as-is)
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

    # Update _meta (match Ansible to_nice_json format)
    total = len(consolidated["hosts"])
    from datetime import datetime, timezone
    consolidated["_meta"] = {
        "description": f"Consolidated VM reference data - {total} Azure images",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_hosts": str(total),
    }

    # Report
    print(f"\nSummary:")
    print(f"  Total images: {total}")
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
        json.dump(consolidated, f, indent=4, default=str)

    size_kb = os.path.getsize(args.output) / 1024
    print(f"\nWritten: {args.output} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
