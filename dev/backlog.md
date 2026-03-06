# ALAR Action Scripts — Backlog

Tracks known bugs, enhancements, and technical debt across all ALAR action scripts.
Findings are based on code review and data collected from 45 Azure VM images.

---

## Critical — Must Fix

### 1. `grubfix-impl.sh` + `efifix-impl.sh`: Unify into bootfix
- **Type**: Enhancement
- **Impact**: Reduces maintenance, adds arm64 + BLS support
- **Details**: See `alar-bootfix-unification.instructions.md` for full plan
- **Status**: Planned (Phase 1-3)

### 2. Missing `GRUB_DISABLE_OS_PROBER=true` across multiple scripts
- **Type**: Bug
- **Impact**: Rescue VM's Ubuntu gets added to recovered VM's grub menu
- **Affected**:
  - `grubfix-impl.sh`: SUSE, Ubuntu, AzureLinux sections
  - `efifix-impl.sh`: SUSE, Ubuntu, AzureLinux sections
  - `initrd-impl.sh`: ALL distros
  - `kernel-impl.sh`: SUSE, Ubuntu, AzureLinux sections
- **Fix**: Use `GRUB_DISABLE_OS_PROBER=true` on every `grub2-mkconfig` / `update-grub` call

### 3. Multiple typos in grubfix/efifix causing failures
- **Type**: Bug
- `grubfix-impl.sh` `recover_ubuntu()`: `resolve-pre` → `resolv-pre` (function undefined)
- `grubfix-impl.sh` `recover_suse()`: `"{$RECOVER_DISK_PATH}"` → `"${RECOVER_DISK_PATH}"`
- `efifix-impl.sh` `resolv-after()`: `resolve.conf` → `resolv.conf`
- `efifix-impl.sh` `recover_ubuntu()`: `resolve-pre` → `resolv-pre`
- `efifix-impl.sh` `recover_ubuntu()`: uses `$new_efi_uuid` but variable is `$new_uuid`
- `efifix-impl.sh` `recover_ubuntu()`: missing EFI partition existence check

---

## High Priority — Should Fix

### 4. No arm64 (aarch64) support in any boot-related script
- **Type**: Enhancement
- **Impact**: arm64 Azure VMs (RHEL, Debian, Ubuntu, SUSE) cannot be recovered
- **Affected**: grubfix, efifix, serialconsole, initrd, kernel
- **Key differences**: Package names (`grub2-efi-aa64`), grub target (`arm64-efi`), serial TTY (`ttyAMA0`), Hyper-V drivers built-in

### 5. No BLS (Boot Loader Specification) handling
- **Type**: Enhancement
- **Impact**: RHEL 8.x+ uses BLS entries in `/boot/loader/entries/`
- **Affected**: serialconsole (must update BLS entry options), kernel (must use `grubby --set-default`)

### 6. EFI grub.cfg written as full standalone instead of redirect shim
- **Type**: Bug (in efifix-impl.sh for RedHat)
- **Impact**: Creates two diverging grub.cfg files; RHEL 7.x already has this problem
- **Fix**: Write EFI grub.cfg as redirect shim, generate main config only to `/boot/grub2/grub.cfg`

### 7. SUSE uses `source` not `configfile` in EFI grub.cfg
- **Type**: Design consideration
- **Impact**: Bootfix must not force `configfile`-based redirect on SUSE
- **Fix**: Detect distro and use appropriate redirect method

---

## Medium Priority — Improvements

### 8. `resolv-pre()` / `resolv-after()` fragile on symlink systems
- **Type**: Enhancement
- **Impact**: Debian 12+, Ubuntu, SUSE use symlinked resolv.conf
- **Fix**: Add `trap` for cleanup; handle symlink restore correctly

### 9. `initrd-impl.sh` adds Hyper-V drivers on arm64 unnecessarily
- **Type**: Bug
- **Impact**: arm64 cloud kernels have Hyper-V drivers built-in; `--add-drivers` may fail silently
- **Fix**: Skip driver addition on aarch64

### 10. Debian not recognized in `get_efi_vendor_dir()` grep pattern
- **Type**: Bug (in planned helpers.sh)
- **Impact**: Would fail to find `/boot/efi/EFI/debian/`
- **Fix**: Add `debian` to the grep pattern

### 11. Boot mode detection using `/boot/efi` presence instead of `/sys/firmware/efi`
- **Type**: Bug (in planned helpers.sh)
- **Impact**: Gen1 BIOS VMs still have `/boot/efi` mounted — would misdetect as EFI
- **Fix**: Use `[ -d /sys/firmware/efi ]` only

### 12. SLES 12 SP5 slow serial baud rate (38400 vs 115200)
- **Type**: Design consideration
- **Impact**: serialconsole action should not blindly overwrite existing serial settings
- **Fix**: Preserve existing baud rate if already configured

---

## Low Priority — Nice to Have

### 13. `fstab-impl.sh` doesn't handle btrfs subvolumes (SLES 16)
- **Type**: Enhancement
- **Impact**: SLES 16 uses btrfs with `@/` subvolumes; fstab rebuild may omit them

### 14. `sudo-impl.sh` duplicate user detection reports `ALL` as a user on SLES 16
- **Type**: Minor bug
- **Impact**: False positive — `ALL ALL=(ALL) ALL` line matched as user `ALL`
- **Fix**: Filter out `ALL` from the duplicate detection regex

### 15. Kernel rollback on BLS systems should use `grubby --set-default`
- **Type**: Enhancement
- **Impact**: `kernel-impl.sh` modifies `GRUB_DEFAULT` which is less reliable on BLS

### 16. `collect-vm-info.yml` EFI classifier edge cases
- **Type**: Minor
- **Impact**: RHEL 7.x/8.x arm64 and SLES 12 SP5 show `unknown/needs_review`
- **Fix**: Add patterns for RHEL 7 full standalone and SLES 12 `normal` redirect
