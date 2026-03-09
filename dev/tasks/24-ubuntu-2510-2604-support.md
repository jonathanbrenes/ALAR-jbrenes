# Task 24 — Ubuntu 25.10 support in preparation for 26.04 LTS

- **Priority**: 4 (Low / Nice to have)
- **Type**: Enhancement
- **Scripts**: Multiple action scripts
- **Repo**: https://github.com/jonathanbrenes/ALAR-jbrenes/tree/main/dev

## Problem

Ubuntu 25.10 introduces changes that will likely carry into 26.04 LTS. Since 26.04 will be a long-term support release, ensuring ALAR handles these changes is forward-looking but not urgent — current impact is minimal since 25.10 is a non-LTS interim release.

## Known differences in Ubuntu 25.10

| Aspect | Ubuntu 24.04 | Ubuntu 25.10 |
|:------|:------|:------|
| sudo implementation | Traditional sudo | sudo-rs (Rust) via alternatives symlink |
| sudo binary path | /usr/bin/sudo (direct) | /usr/bin/sudo → /etc/alternatives/sudo → /usr/lib/cargo/bin/sudo |
| sudo permissions | 4755 | 4755 (on the real binary) |
| os-prober (server) | Installed | Installed |
| os-prober (minimal) | Not installed | Not installed |
| Hyper-V modules | Built-in | Built-in |
| GRUB | grub-install / update-grub | Same |
| EFI vendor dir | ubuntu | ubuntu |

## What needs attention

1. **sudo-rs symlink chain** (Task 16): `sudo-impl.sh` must resolve symlinks with `readlink -f` before applying permissions
2. **No other breaking changes identified** in the 97-VM analysis for Ubuntu 25.10 vs 24.04

## No immediate action required

This task is for tracking purposes. The sudo-rs fix (Task 16) is the only code change needed. All other ALAR action scripts work identically on Ubuntu 25.10 as on 24.04.

When Ubuntu 26.04 LTS is released, re-run `dev/collect-vm-info.yml` against it and compare with the 25.10 data to identify any additional changes.

## Related tasks

- Task 16 (sudo-rs symlink)
- Task 18 (os-prober on minimal images)
