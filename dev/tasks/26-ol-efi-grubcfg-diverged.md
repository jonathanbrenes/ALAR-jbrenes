# Task 26 — Oracle Linux EFI grub.cfg DIVERGED on OL 7.9 and 8.2

- **Priority**: 2 (Medium)
- **Type**: Bug
- **Backlog**: #27
- **Script**: `src/action_implementation/efifix-impl.sh`
- **Related**: Task 06

> **Note**: Same root cause as Task 06 (RHEL 7.x DIVERGED). Once Task 01 (bootfix unification) addresses the redirect shim, this is resolved for OL too.

## Problem

Oracle Linux 7.9 Gen2 and 8.2 Gen2 have **full_standalone / DIVERGED** EFI grub.cfg files at `/boot/efi/EFI/redhat/grub.cfg`. Instead of a one-line `configfile` redirect to `/boot/grub2/grub.cfg`, they contain a complete standalone GRUB config.

This means:
1. Two separate grub.cfg files can drift out of sync
2. `grub2-mkconfig` only regenerates `/boot/grub2/grub.cfg` — the EFI copy is stale
3. Any repair that only fixes `/boot/grub2/grub.cfg` leaves the VM booting from the old EFI config

OL uses the `redhat` EFI vendor directory (not `oracle`), so the existing grep pattern `centos|redhat` already matches.

## Affected images

| Image | EFI grub.cfg type |
|---|---|
| OL 7.9 Gen2 x86_64 | DIVERGED (full standalone) |
| OL 8.2 Gen2 x86_64 | DIVERGED (full standalone) |
| OL 9.5/9.6 Gen2 x86_64 | configfile redirect (correct) |
| OL 10.0 Gen2 x86_64 | configfile redirect (correct) |
| OL arm64 (8.10/9.x/10.x) | bls_full_config (see Task 27) |

## Fix

Same approach as Task 06:
1. During repair, always write the EFI grub.cfg as a redirect shim pointing to `/boot/grub2/grub.cfg`
2. Then regenerate `/boot/grub2/grub.cfg` with `grub2-mkconfig`
3. OL vendor dir is `redhat` — no new grep pattern needed

## Verification

```bash
# After repair, EFI grub.cfg should be a short redirect:
cat /boot/efi/EFI/redhat/grub.cfg
# Expected: configfile (hd0,...)/boot/grub2/grub.cfg
```
