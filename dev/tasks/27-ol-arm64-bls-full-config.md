# Task 27 — Oracle Linux arm64 EFI grub.cfg uses `bls_full_config`

- **Priority**: 3 (Medium)
- **Type**: Design consideration
- **Backlog**: #28
- **Script**: `src/action_implementation/efifix-impl.sh`
- **Related**: Task 04 (arm64 support), Task 06 (EFI redirect)

## Problem

Oracle Linux 8.10, 9.x, and 10.x **arm64** images have a `bls_full_config` EFI grub.cfg at `/boot/efi/EFI/redhat/grub.cfg`. This is a ~216‑line hybrid config that combines:
- BLS entry loading via `blscfg`
- Fallback menuentries
- Full GRUB environment setup

This is **not** a simple redirect shim and **not** a DIVERGED standalone — it's a third pattern. The same pattern appears on RHEL 8+ and AlmaLinux 8+ arm64 images.

## Why it matters

If the EFI repair writes a simple `configfile` redirect shim over this file, the arm64 VM loses the BLS integration and may fail to boot. The repair must recognize this pattern and either:
1. Leave it alone (preferred if `/boot/grub2/grub.cfg` is also intact)
2. Regenerate it using `grub2-mkconfig` targeting the EFI path

## Affected images

| Image | Architecture | EFI grub.cfg type |
|---|---|---|
| OL 8.10 arm64 | aarch64 | bls_full_config |
| OL 9.5 arm64 | aarch64 | bls_full_config |
| OL 9.6 arm64 | aarch64 | bls_full_config |
| OL 10.0 arm64 | aarch64 | bls_full_config |

## Detection

```bash
# bls_full_config files contain blscfg command:
grep -q 'blscfg' /boot/efi/EFI/redhat/grub.cfg && echo "bls_full_config"
```

## Fix approach

1. Check if EFI grub.cfg contains `blscfg` — if so, classify as `bls_full_config`
2. On BLS arm64 systems, do **not** overwrite EFI grub.cfg with a redirect shim
3. If regeneration is needed, use `grub2-mkconfig -o /boot/efi/EFI/redhat/grub.cfg`
4. Ensure `GRUB_DISABLE_OS_PROBER=true` is set before any `grub2-mkconfig` call
