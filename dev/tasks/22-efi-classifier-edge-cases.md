# Task 22 — collect-vm-info.yml EFI classifier edge cases

- **Priority**: 4 (Low)
- **Type**: Minor (dev tooling)
- **Script**: `dev/collect-vm-info.yml`
- **Repo**: https://github.com/jonathanbrenes/ALAR-jbrenes/tree/main/dev
- **Status**: FIXED

## Problem (resolved)

4 VMs showed `unknown/needs_review` in the EFI grub.cfg classifier due to heuristic gaps:

| VM | Root cause | Fix applied |
|:------|:------|:------|
| RHEL 7.8 | HAS_MENUENTRY > 5 missed exactly 5 menuentries | Changed threshold to > 3 |
| RHEL 7.8 | HAS_MKCONFIG pattern BEGIN.*grub-mkconfig didn't match BEGIN /etc/grub.d | Fixed regex pattern |
| RHEL 8.10 arm64 | Hybrid BLS + menuentry config (218 lines, blscfg + menuentries) | Added bls_full_config type |
| AlmaLinux 8.10 arm64 | Same hybrid pattern | Same fix |
| SLES 12 SP5 | normal redirect (bare normal command) not matched by 'normal ' grep | Added '^normal\$' pattern and redirect_method: normal |

## Current status

All fixes have been applied to `dev/collect-vm-info.yml`. All 97 VMs now classify correctly. No further action needed unless new edge cases are discovered when adding more VM images.

## No code changes required

This task is tracked for completeness. Close when acknowledged.
