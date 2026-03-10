# Task 01 — Unify grubfix + efifix into bootfix

- **Priority**: 1 (Critical)
- **Type**: Enhancement
- **Scripts**: `src/action_implementation/grubfix-impl.sh`, `src/action_implementation/efifix-impl.sh`
- **Plan**: `dev/alar-bootfix-unification.instructions.md`
- **Repo**: https://github.com/jonathanbrenes/ALAR-jbrenes/tree/main/dev

## Problem

`grubfix-impl.sh` (95 lines) handles Gen1/BIOS boot repair and `efifix-impl.sh` (157 lines) handles Gen2/EFI boot repair as two separate scripts. They duplicate logic (resolv-pre/after, per-distro branching, grub2-mkconfig calls) and neither supports arm64 or BLS.

## What needs to change

1. Create a new `bootfix-impl.sh` that detects boot mode via `$efi_part_path` (non-empty = EFI)
2. Merge per-distro recovery functions from both scripts into unified functions
3. Add arm64 support (package names, grub target, serial TTY)
4. Add BLS handling for RHEL 8+ (detect + regenerate `/boot/loader/entries/`)
5. Add `GRUB_DISABLE_OS_PROBER=true` on every grub regeneration call
6. Write EFI grub.cfg as redirect shim (not full standalone)
7. Handle Azure Linux 3 special cases (no vendor dir, NVMe, tdnf)

## Affected lines

### grubfix-impl.sh — entire file (95 lines)

- Lines 1-12: `resolv-pre()` / `resolv-after()` — duplicated, move to `helpers.sh`
- Lines 14-35: `recover_redhat()` — only BIOS, no arm64
- Lines 37-46: `recover_suse()` — typo on line 42: `"{$RECOVER_DISK_PATH}"` should be `"${RECOVER_DISK_PATH}"`; missing `GRUB_DISABLE_OS_PROBER=true` on line 43
- Lines 48-60: `recover_ubuntu()` — typo on line 49: `resolve-pre` should be `resolv-pre`; missing `GRUB_DISABLE_OS_PROBER=true` on line 57
- Lines 62-79: `recover_azurelinux()` — missing `GRUB_DISABLE_OS_PROBER=true` on line 77

### efifix-impl.sh — entire file (157 lines)

- Lines 1-6: `resolv-pre()` — duplicated
- Lines 9-11: `resolv-after()` — typo on line 10: `resolve.conf` should be `resolv.conf`
- Lines 13-37: `recover_redhat()` — writes full standalone EFI grub.cfg (should be redirect shim); no arm64 packages
- Lines 39-75: `recover_suse()` — uses `configfile` redirect but SUSE needs `source`; missing `GRUB_DISABLE_OS_PROBER=true` on line 72
- Lines 78-132: `recover_azurelinux()` — missing `GRUB_DISABLE_OS_PROBER=true` on line 129
- Lines 134-146: `recover_ubuntu()` — typo on line 135: `resolve-pre` should be `resolv-pre`; uses `$new_efi_uuid` on line 143 but variable is `$new_uuid` (line 142); no EFI partition existence check; missing `GRUB_DISABLE_OS_PROBER=true` on line 139; no Debian handling

## How to fix

See `dev/alar-bootfix-unification.instructions.md` for the full 3-phase plan:
- Phase 1: Create `bootfix-impl.sh` with unified per-distro functions and auto boot-mode detection
- Phase 2: Add arm64 packages, grub targets, BLS regeneration
- Phase 3: Write EFI grub.cfg as proper redirect shim per distro (configfile/source)

## Pre-requisite: verify rescue VM generation matching

Before implementing bootfix, confirm that `az vm repair create` correctly matches the VM generation (Gen1/Gen2) and architecture (x86_64/arm64) between the original and rescue VMs. The bootfix script relies on `$efi_part_path` for boot mode detection, which is generation-independent, but mismatched rescue VMs could affect other assumptions.

Possibly addressed by: https://github.com/Azure/azure-cli-extensions/pull/8620/changes

If generation matching is not guaranteed, the bootfix must avoid any fallback to `/sys/firmware/efi` and rely exclusively on `$efi_part_path`.
