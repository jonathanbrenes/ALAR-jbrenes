#!/usr/bin/env python3
"""
Merge new VM collection results into vm-data-consolidated.json.

Takes one or more results JSON files (already sanitized by collect-vm-info.yml)
and merges them into the consolidated file. Each VM is keyed by its IMDS
publisher:offer:sku (e.g., "RedHat:RHEL:7.6"), so the same image collected
from different inventories always maps to the same entry.

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


def get_sku_key(host_data):
    """Extract publisher:offer:sku:transport from IMDS and disk data.

    Transport is determined by the root disk device name:
    - 'nvme' if root_disk starts with 'nvme' (e.g., nvme0n1)
    - 'scsi' otherwise (e.g., sda, sdb)
    Note: nvme_present may be 'yes' even when root is on SCSI
    (Azure NVMe Accelerator for temp disk), so we use root_disk.
    """
    compute = host_data.get("imds", {}).get("compute", {})
    publisher = compute.get("publisher", "")
    offer = compute.get("offer", "")
    sku = compute.get("sku", "")
    # Determine transport from root disk name
    root_disk = host_data.get("disk", {}).get("root_disk", "")
    transport = "nvme" if root_disk.startswith("nvme") else "scsi"
    if publisher and offer and sku:
        return f"{publisher}:{offer}:{sku}:{transport}"
    return None


def rekey_hosts(hosts_dict):
    """Re-key a hosts dict from arbitrary hostnames to publisher:offer:sku.

    Returns a new dict keyed by SKU and a list of any entries that could
    not be re-keyed (missing IMDS data).
    """
    rekeyed = {}
    skipped = []
    for name, data in hosts_dict.items():
        key = get_sku_key(data)
        if key:
            rekeyed[key] = data
        else:
            skipped.append(name)
    return rekeyed, skipped


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
        # Re-key existing data if it uses old hostname-based keys
        old_hosts = consolidated.get("hosts", {})
        consolidated["hosts"], skipped = rekey_hosts(old_hosts)
        if skipped:
            print(f"  Warning: {len(skipped)} entries without IMDS data (kept as-is): {skipped}")
            for name in skipped:
                consolidated["hosts"][name] = old_hosts[name]
        if len(consolidated["hosts"]) != len(old_hosts):
            print(f"  Re-keyed: {len(old_hosts)} entries -> {len(consolidated['hosts'])} unique SKUs")
    else:
        print(f"Creating new: {args.output}")
        consolidated = {"_meta": {}, "hosts": {}}

    added = []
    updated = []

    # Merge each input file
    for filepath in args.files:
        print(f"Processing: {filepath}")
        new_data = load_json(filepath)
        new_hosts = new_data.get("hosts", {})

        for name, host_data in new_hosts.items():
            key = get_sku_key(host_data)
            if not key:
                print(f"  Warning: skipping {name} — no IMDS publisher:offer:sku")
                continue
            if key in consolidated["hosts"]:
                updated.append(key)
            else:
                added.append(key)
            consolidated["hosts"][key] = host_data

        print(f"  {len(new_hosts)} hosts from {filepath}")

    # Update _meta
    total = len(consolidated["hosts"])
    consolidated["_meta"] = {
        "description": f"Consolidated VM reference data - {total} Azure images",
        "total_hosts": total,
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
        json.dump(consolidated, f, indent=2, default=str)

    size_kb = os.path.getsize(args.output) / 1024
    print(f"\nWritten: {args.output} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
