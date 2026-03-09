# Task 13 — Debian not recognized in get_efi_vendor_dir() grep pattern

- **Priority**: 3 (Medium)
- **Type**: Bug
- **Script**: Planned `helpers.sh` addition (also affects `efifix-impl.sh` current patterns)
- **Repo**: https://github.com/jonathanbrenes/ALAR-jbrenes/tree/main/dev

## Problem

The current EFI vendor directory detection in `efifix-impl.sh` uses grep patterns like:

```bash
ls /boot/efi/EFI | grep -i -E "centos|redhat"     # recover_redhat(), line 31
ls /boot/efi/EFI | grep -i -E "sles"               # recover_suse(), line 61
```

These patterns are incomplete:
- `recover_redhat()` misses `almalinux`, `rocky`, `oracle`
- `recover_suse()` uses `sles` but SUSE vendor dir is actually `BOOT`
- No pattern for `debian`
- No pattern for `ubuntu`
- No handling for Azure Linux 3 (no vendor dir at all)

## Affected lines

### efifix-impl.sh

- **Line 31**: `grep -i -E "centos|redhat"` — missing `almalinux`
- **Line 61**: `grep -i -E "sles"` — should be `BOOT` (see Task 07)
- **Lines 134-146**: `recover_ubuntu()` — doesn't detect EFI vendor dir at all

### kernel-impl.sh

- **Line 19**: `grep -i -E "centos|redhat"` — missing `almalinux`
- **Line 20**: Same pattern duplicated

## Vendor directories (from 97-VM data)

| Distro | EFI vendor dir |
|:------|:------|
| RHEL 7-10 | redhat |
| CentOS | centos |
| AlmaLinux 8-10 | almalinux |
| RockyLinux | rocky |
| Debian 11-13 | debian |
| Ubuntu 20.04-25.10 | ubuntu |
| SUSE 12-16 | BOOT |
| Azure Linux 3 | **none** (only /boot/efi/EFI/BOOT/) |

## How to fix

Create a helper function in `helpers.sh`:

```bash
get_efi_vendor_dir() {
    local dir
    for dir in $(ls /boot/efi/EFI/ 2>/dev/null); do
        case "${dir,,}" in
            redhat|centos|almalinux|rocky|oracle|debian|ubuntu|sles|boot)
                echo "$dir"
                return 0
                ;;
        esac
    done
    # Azure Linux 3: no vendor dir
    return 1
}
```

Then replace all `ls /boot/efi/EFI | grep ...` patterns with `get_efi_vendor_dir`.
