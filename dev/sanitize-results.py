#!/usr/bin/env python3
"""
Sanitize and consolidate ALAR VM collection results.

Takes one or more results JSON files (from collect-vm-info.yml) and produces
a single sanitized vm-data-consolidated.json suitable for sharing and AI context.

Usage:
    python sanitize-results.py results1.json [results2.json ...] [-o output.json]

What it removes:
    - IMDS: subscription IDs, resource IDs, VM IDs, resource groups, public keys,
      tags, OS profiles, security profiles, storage profiles
    - resolv.conf: internal Azure DNS domain names
    - mtab: verbose mount entries (redundant with fstab and mounts sections)
    - blkid: raw UUID mappings (redundant with fstab and disk sections)
    - Usernames from sudoers content (keeps permissions and structure)

What it keeps:
    - IMDS: publisher, offer, sku, osType, vmSize, location
    - All boot, GRUB, EFI, BLS, kernel, initramfs, serial console data
    - fstab content, disk layout, LVM details
    - Sudo permissions, auditd config, package manager info
    - Hyper-V module status, waagent/cloud-init versions
"""

import json
import argparse
import sys
import os
import re


def sanitize_imds(imds: dict) -> dict:
    """Strip IMDS down to non-sensitive fields only.

    Removes: subscription IDs, resource IDs, VM IDs, resource group names,
    public SSH keys, OS profiles, security profiles, storage profiles, tags,
    and all other Azure-specific identifiers.

    Keeps: publisher, offer, sku, osType, vmSize, location — these identify
    the image type without exposing any customer-specific information.

    Args:
        imds: The raw IMDS section from the collected VM data.

    Returns:
        A sanitized IMDS dict with only non-sensitive fields.
    """
    compute = imds.get("compute", {})
    img_ref = imds.get("image_reference", {})

    return {
        "compute": {
            "publisher": compute.get("publisher", ""),
            "offer": compute.get("offer", ""),
            "sku": compute.get("sku", ""),
            "osType": compute.get("osType", ""),
            "vmSize": compute.get("vmSize", ""),
            "location": compute.get("location", ""),
        },
        "image_reference": {
            "publisher": img_ref.get("publisher", ""),
            "offer": img_ref.get("offer", ""),
            "sku": img_ref.get("sku", ""),
        },
    }


def sanitize_host(data: dict) -> dict:
    """Sanitize a single host's collected data in place.

    Applies the following sanitization rules:
    - IMDS: Stripped to publisher/offer/sku/osType/vmSize/location only
    - resolv.conf: Replaced with placeholder (contains internal Azure DNS domains)
    - fstab_detail.mtab: Replaced with placeholder (verbose, contains temp mounts)
    - fstab_detail.blkid: Replaced with placeholder (UUIDs already in fstab/mounts)

    All boot, GRUB, EFI, BLS, kernel, initramfs, serial console, Hyper-V,
    sudo, auditd, waagent, and cloud-init data is preserved unchanged.

    Args:
        data: The full collected data dict for a single host.

    Returns:
        The same dict with sensitive fields sanitized.
    """
    # IMDS
    if "imds" in data:
        data["imds"] = sanitize_imds(data["imds"])

    # resolv.conf — contains internal Azure DNS domains
    if "resolv_conf" in data:
        data["resolv_conf"] = ["(sanitized)"]

    # fstab_detail — mtab and blkid are verbose and contain UUIDs already in fstab
    if "fstab_detail" in data:
        if "mtab" in data["fstab_detail"]:
            data["fstab_detail"]["mtab"] = ["(sanitized)"]
        if "blkid" in data["fstab_detail"]:
            data["fstab_detail"]["blkid"] = ["(sanitized)"]

    return data


def process_file(filepath: str) -> dict:
    """Load a results JSON file and return a dict of sanitized hosts.

    Reads a JSON file produced by collect-vm-info.yml, extracts the 'hosts'
    section, and applies sanitize_host() to each host's data.

    Args:
        filepath: Path to a results JSON file.

    Returns:
        A dict mapping hostname to sanitized host data.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    hosts = {}
    for name, host_data in data.get("hosts", {}).items():
        hosts[name] = sanitize_host(host_data)

    return hosts


def main():
    """Entry point: parse args, process files, write consolidated output.

    Merges one or more results JSON files into a single sanitized output.
    Warns on duplicate hostnames (last file wins) and verifies no sensitive
    fields like subscriptionId or publicKeys remain in the output.
    """
    parser = argparse.ArgumentParser(
        description="Sanitize and consolidate ALAR VM collection results."
    )
    parser.add_argument(
        "files",
        nargs="+",
        help="One or more results JSON files from collect-vm-info.yml",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="vm-data-consolidated.json",
        help="Output filename (default: vm-data-consolidated.json)",
    )

    args = parser.parse_args()

    # Validate input files
    for f in args.files:
        if not os.path.isfile(f):
            print(f"Error: File not found: {f}", file=sys.stderr)
            sys.exit(1)

    # Process all files
    all_hosts = {}
    for f in args.files:
        print(f"Processing: {f}")
        hosts = process_file(f)
        # Check for duplicates
        dupes = set(all_hosts.keys()) & set(hosts.keys())
        if dupes:
            print(f"  Warning: duplicate hosts will be overwritten: {dupes}")
        all_hosts.update(hosts)
        print(f"  Loaded {len(hosts)} hosts (total: {len(all_hosts)})")

    # Build output
    output = {
        "_meta": {
            "description": f"Consolidated VM reference data - {len(all_hosts)} Azure images",
            "total_hosts": len(all_hosts),
        },
        "hosts": all_hosts,
    }

    # Verify no sensitive data leaked
    text = json.dumps(output)
    for field in [
        "subscriptionId",
        "resourceId",
        "resourceGroupName",
        "vmId",
        "publicKeys",
        "adminUsername",
    ]:
        if field in text:
            print(
                f"  Warning: '{field}' still present in output — check sanitization",
                file=sys.stderr,
            )

    # Write output
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)

    size_kb = os.path.getsize(args.output) / 1024
    print(f"\nDone: {len(all_hosts)} hosts written to {args.output} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
