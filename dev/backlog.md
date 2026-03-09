# ALAR Action Scripts — Backlog

Tracks known bugs, enhancements, and technical debt across all ALAR action scripts.
Findings are based on code review and data collected from 97 Azure VM images.

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

### 25. `fstab-impl.sh` LVM branch fails on RHEL 9/10 (UUID-based fstab)
- **Type**: Bug
- **Impact**: On RHEL 9+ and RHEL 10 LVM images, fstab uses UUIDs instead of `/dev/mapper/rootvg-*` device paths. The LVM branch (lines 93-99) greps for `rootvg-rootlv`, `rootvg-homelv`, etc. — these patterns match nothing on RHEL 9/10, producing an **empty fstab** that prevents boot.
- **Confirmed**: RHEL 8 LVM uses `/dev/mapper/rootvg-*` (works), RHEL 9/10 LVM use `UUID=...` (broken)
- **Fix**: Match by mount point instead of device name: `awk '/[[:space:]]+\/[[:space:]]+/ {print}'` for root, `awk '/[[:space:]]+\/home[[:space:]]+/ {print}'` for /home, etc.

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
- **Detection**: Check only `GRUB_ENABLE_BLSCFG=true` in `/etc/default/grub` — do NOT require `/boot/loader/entries/` to exist (it may have been deleted and need recovery, see #23)

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

### 9. `initrd-impl.sh` adds Hyper-V drivers unnecessarily on Ubuntu, Azure Linux, and arm64
- **Type**: Bug
- **Impact**: Hyper-V drivers (`hv_vmbus`, `hv_storvsc`, `hv_netvsc`) are built-in on all 38 Ubuntu images (20.04-25.10, x86 and arm64), all 6 Azure Linux 3 images, and some SUSE x86; `--add-drivers` is unnecessary and may fail silently
- **Fix**: Skip `--add-drivers` when Hyper-V modules are built-in; check `/lib/modules/$(uname -r)/modules.builtin` for `hv_vmbus` before adding drivers

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
- **Impact**: 4 VMs showed `unknown/needs_review` due to classifier heuristic gaps
- **Root causes and fixes** — **FIXED**:
  - RHEL 7.8: `HAS_MENUENTRY > 5` missed exactly 5 menuentries → changed to `> 3`
  - RHEL 7.8: `HAS_MKCONFIG` pattern `BEGIN.*grub-mkconfig` didn't match `BEGIN /etc/grub.d` markers → fixed pattern
  - RHEL 8.10 arm64 / AlmaLinux 8.10 arm64: hybrid BLS + menuentry config (218 lines, `blscfg` + menuentries, no separate `/boot/grub2/grub.cfg`) → added `bls_full_config` type
  - SLES 12 SP5: `normal` redirect (4-line shim using bare `normal` command) not matched by `'normal '` grep → added `'^normal$'` pattern and `redirect_method: normal`

---

## Findings from 97-VM Analysis

### 17. Ubuntu 25.10 uses sudo-rs via alternatives symlink chain
- **Type**: Enhancement
- **Priority**: Medium
- **Impact**: Ubuntu 25.10 replaced traditional sudo with `sudo-rs` (Rust): `/usr/bin/sudo` → `/etc/alternatives/sudo` → `/usr/lib/cargo/bin/sudo`; `sudo-impl.sh` must resolve symlinks before `chmod` to fix the real binary
- **Affected**: `sudo-impl.sh`, `collect-vm-info.yml` (`find -type f` missed symlink — **FIXED**)
- **Fix**: Use `readlink -f /usr/bin/sudo` to find real binary before chmod; playbook already fixed with `( -type f -o -type l )` + `readlink -f`

### 18. Azure Linux 3 — No EFI vendor directory
- **Type**: Bug
- **Priority**: High
- **Impact**: Azure Linux 3 has no vendor-specific EFI directory — only `BOOT/`; grub.cfg at `/boot/efi/boot/grub2/grub.cfg` (lowercase); no EFI redirect shim (`status: no_efi_grubcfg`)
- **Affected**: `efifix-impl.sh`, planned `get_efi_vendor_dir()`
- **Fix**: Handle AzureLinux as special case — no vendor dir, grub.cfg in non-standard path

### 19. Azure Linux 3 — NVMe native boot with separate `/boot` partition
- **Type**: Design consideration
- **Priority**: High
- **Impact**: Azure Linux 3 uses NVMe (`/dev/nvme0n1`) with 3-partition layout: EFI (p1, 64MB), `/boot` (p2, 500MB ext4), root (p3); unique among all distros
- **Affected**: Partition detection, mount logic
- **Fix**: Ensure ALAR handles separate `/boot` on NVMe correctly when disk is re-attached as SCSI data disk

### 20. Azure Linux 3 — GRUB commands and package names differ from other distros
- **Type**: Enhancement
- **Priority**: Medium
- **Impact**: Uses `grub2-install`/`grub2-mkconfig` (no `update-grub`), GRUB path `/boot/grub2/`, pkg mgr `tdnf`/`dnf`, dracut (v102) for initramfs, EFI packages `grub2-efi-binary`/`shim` (not arch-suffixed like RHEL)
- **Affected**: All boot-related scripts when Azure Linux support is extended
- **Fix**: Add AzureLinux-specific paths and package names to boot scripts

### 21. os-prober not installed on Ubuntu minimal images (24.04+)
- **Type**: Design consideration
- **Priority**: Medium
- **Impact**: Ubuntu 24.04+ minimal and Pro minimal images do NOT have os-prober; server and Pro (non-minimal) images still do; all arm64 minimal images lack it too
- **Affected**: `GRUB_DISABLE_OS_PROBER=true` is still required on server images but is a no-op on minimal
- **Fix**: No code change needed — `GRUB_DISABLE_OS_PROBER=true` is harmless when os-prober absent; update documentation

### 22. Hyper-V modules built-in on all Ubuntu and Azure Linux 3 (not just arm64)
- **Type**: Confirmation / expansion of #9
- **Priority**: Low
- **Impact**: All 38 Ubuntu images (20.04-25.10, x86_64 and aarch64) and all 6 Azure Linux 3 images have `hv_vmbus`/`hv_storvsc` built into the kernel; some SUSE x86 images also have built-in modules (48/97 total)
- **Affected**: `initrd-impl.sh`
- **Fix**: Same as #9 — check `modules.builtin` instead of assuming only arm64 needs the skip

### 23. Recovery when `/boot/loader/entries/` is deleted on BLS systems
- **Type**: Enhancement
- **Priority**: High
- **Impact**: RHEL 8+/AlmaLinux 8+ use BLS (`GRUB_ENABLE_BLSCFG=true`); if `/boot/loader/entries/` is removed, GRUB finds no boot entries and the VM fails to boot. All 34 BLS-enabled images have `grubby` available.
- **Affected**: `grubfix-impl.sh`, `efifix-impl.sh`, planned bootfix
- **Recovery approach**:
  1. Detect BLS is enabled (`GRUB_ENABLE_BLSCFG=true` in `/etc/default/grub`) but entries are missing
  2. Recreate `/boot/loader/entries/` directory
  3. For each installed kernel in `/lib/modules/*/`, run `kernel-install add <version> /boot/vmlinuz-<version>` to regenerate BLS entries
  4. Alternatively, use `grubby --info=ALL` to verify and `grubby --set-default` to set the default kernel
  5. Regenerate `grub.cfg` with `GRUB_DISABLE_OS_PROBER=true grub2-mkconfig -o /boot/grub2/grub.cfg`
