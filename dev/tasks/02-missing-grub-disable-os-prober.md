# Task 02 — Missing GRUB_DISABLE_OS_PROBER=true across multiple scripts

- **Priority**: 1 (Critical)
- **Type**: Bug
- **Impact**: Rescue VM's Ubuntu gets added to recovered VM's GRUB menu
- **Repo**: https://github.com/jonathanbrenes/ALAR-jbrenes/tree/main/dev

> **Note**: The grubfix/efifix fixes in this task will be superseded once Task 01 (bootfix unification) is completed. The initrd, kernel, and serialconsole fixes remain required independently.

## Problem

The rescue VM runs Ubuntu and has `os-prober` installed. When `grub2-mkconfig` or `update-grub` runs without `GRUB_DISABLE_OS_PROBER=true`, os-prober detects the rescue VM's Ubuntu and adds it as a menu entry in the recovered disk's grub.cfg.

## Affected lines

### grubfix-impl.sh

| Line | Current code | Fix |
|---|---|---|
| 43 | `grub2-mkconfig -o /boot/grub2/grub.cfg` | Prefix with `GRUB_DISABLE_OS_PROBER=true` |
| 57 | `update-grub` | Prefix with `GRUB_DISABLE_OS_PROBER=true` |
| 77 | `grub2-mkconfig -o /boot/grub2/grub.cfg` | Prefix with `GRUB_DISABLE_OS_PROBER=true` |

Note: Line 31 (`recover_redhat`) already has the prefix — only SUSE, Ubuntu, and AzureLinux sections are missing it.

### efifix-impl.sh

| Line | Current code | Fix |
|---|---|---|
| 72 | `grub2-mkconfig -o /boot/grub2/grub.cfg` | Prefix with `GRUB_DISABLE_OS_PROBER=true` |
| 129 | `grub2-mkconfig -o /boot/grub2/grub.cfg` | Prefix with `GRUB_DISABLE_OS_PROBER=true` |
| 139 | `update-grub` | Prefix with `GRUB_DISABLE_OS_PROBER=true` |

Note: Lines 30-31 (`recover_redhat`) already have the prefix.

### initrd-impl.sh

| Line | Current code | Fix |
|---|---|---|
| 34 | `grub2-mkconfig -o /boot/grub2/grub.cfg` | Prefix with `GRUB_DISABLE_OS_PROBER=true` |
| 55 | `grub-mkconfig -o /boot/grub/grub.cfg` | Prefix with `GRUB_DISABLE_OS_PROBER=true` |
| 56 | `grub-mkconfig -o /boot/efi/EFI/ubuntu/grub.cfg` | Prefix with `GRUB_DISABLE_OS_PROBER=true` |
| 68 | `grub2-mkconfig -o /boot/grub2/grub.cfg` | Prefix with `GRUB_DISABLE_OS_PROBER=true` |
| 88 | `grub2-mkconfig -o /boot/grub2/grub.cfg` | Prefix with `GRUB_DISABLE_OS_PROBER=true` |

None of the initrd-impl.sh calls have the prefix.

### kernel-impl.sh

| Line | Current code | Fix |
|---|---|---|
| 33 | `update-grub` | Prefix with `GRUB_DISABLE_OS_PROBER=true` |
| 41 | `grub2-mkconfig -o /boot/grub2/grub.cfg` | Prefix with `GRUB_DISABLE_OS_PROBER=true` |
| 51 | `grub2-mkconfig -o /boot/grub2/grub.cfg` | Prefix with `GRUB_DISABLE_OS_PROBER=true` |

Note: Lines 20-21 (`isRedHat`) already have the prefix.

### serialconsole-impl.sh

| Line | Current code | Fix |
|---|---|---|
| 66 | `grub2-mkconfig -o /boot/efi/EFI/${distro}/grub.cfg` | Prefix with `GRUB_DISABLE_OS_PROBER=true` |
| 69 | `grub2-mkconfig -o /boot/grub2/grub.cfg` | Prefix with `GRUB_DISABLE_OS_PROBER=true` |
| 95 | `update-grub` | Prefix with `GRUB_DISABLE_OS_PROBER=true` |
| 109 | `update-grub` | Prefix with `GRUB_DISABLE_OS_PROBER=true` |

## How to fix

Every `grub2-mkconfig` and `update-grub` call must be prefixed with `GRUB_DISABLE_OS_PROBER=true`. Example:

```bash
# Before
grub2-mkconfig -o /boot/grub2/grub.cfg

# After
GRUB_DISABLE_OS_PROBER=true grub2-mkconfig -o /boot/grub2/grub.cfg
```

This is harmless when os-prober is not installed (all Debian, SUSE, Azure Linux, arm64 Ubuntu images).
