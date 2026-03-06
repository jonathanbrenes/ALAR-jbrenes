# Azure VM Boot Reference Data

Consolidated from 45 Azure VM images collected across 3 regions.
Use this as context for any AI agent working on ALAR action scripts.

---

## Quick Reference Tables

### GRUB Commands by Distro Family

| Distro | grub-install | grub-mkconfig | update-grub | grubby |
|---|---|---|---|---|
| RHEL 7-10 | `grub2-install` | `grub2-mkconfig` | N/A | `grubby` |
| Debian 11-13 | `grub-install` | `grub-mkconfig` | `update-grub` | N/A |
| Ubuntu 24.04 | `grub-install` | `grub-mkconfig` | `update-grub` | N/A |
| SUSE 12-16 | `grub2-install` | `grub2-mkconfig` | N/A | N/A |

### GRUB Config Paths

| Distro | Main grub.cfg | EFI grub.cfg | Vendor dir |
|---|---|---|---|
| RHEL | `/boot/grub2/grub.cfg` | `/boot/efi/EFI/redhat/grub.cfg` | `redhat` |
| Debian | `/boot/grub/grub.cfg` | `/boot/efi/EFI/debian/grub.cfg` | `debian` |
| Ubuntu | `/boot/grub/grub.cfg` | `/boot/efi/EFI/ubuntu/grub.cfg` | `ubuntu` |
| SUSE | `/boot/grub2/grub.cfg` | `/boot/efi/EFI/BOOT/grub.cfg` | `BOOT` (no vendor-specific) |

### EFI grub.cfg Redirect Method

| Distro | Method | Command |
|---|---|---|
| RHEL 8+ | `configfile` | `search --no-floppy --set prefix --file /grub2/grub.cfg; configfile $prefix/grub.cfg` |
| RHEL 7.x | Full standalone | No redirect — full menuentry grub.cfg in EFI (DIVERGED from boot) |
| Debian/Ubuntu | `configfile` | `search.fs_uuid <UUID> root; set prefix=($root)'/boot/grub'; configfile $prefix/grub.cfg` |
| SUSE 15+ | `source` | `search --no-floppy --set prefix --file /grub2/grub.cfg; source "${prefix}/grub.cfg"` |
| SUSE 12 | `normal` | `search --no-floppy --set prefix --file /grub2/grub.cfg; set prefix=(${root})//grub2; normal` |

### BLS (Boot Loader Specification) Status

| Distro | GRUB_ENABLE_BLSCFG | Actual entries in /boot/loader/ | grubby available |
|---|---|---|---|
| RHEL 7.x | No | No | Yes (v8.28) |
| RHEL 8.x | Yes | Yes | Yes |
| RHEL 9.x | Yes | Yes | Yes |
| RHEL 10.x | Yes | Yes | Yes |
| Debian 11-13 | No | No | No |
| Ubuntu 24.04 | No | No | No |
| SUSE 12-16 | No | No | No |

### Package Names by Distro × Architecture

| Distro | x86_64 EFI packages | aarch64 EFI packages |
|---|---|---|
| RHEL | `grub2-efi-x64`, `shim-x64` | `grub2-efi-aa64`, `shim-aa64` |
| Debian | `grub-efi-amd64-bin`, `grub-efi-amd64-signed`, `shim-signed:amd64` | `grub-efi-arm64-bin`, `grub-efi-arm64-signed`, `shim-signed:arm64` |
| Ubuntu | `grub-efi-amd64-signed`, `shim-signed` | `grub-efi-arm64-signed`, `shim-signed` |
| SUSE 15+ | `grub2-x86_64-efi` | `grub2-arm64-efi` |

### EFI Binary Names

| Arch | GRUB binary | Shim binary | Boot binary |
|---|---|---|---|
| x86_64 | `grubx64.efi` | `shimx64.efi` | `BOOTX64.EFI` |
| aarch64 | `grubaa64.efi` | `shimaa64.efi` | `BOOTAA64.EFI` |

### Serial Console TTY

All arm64 hosts have `ttyS0`, `ttyS1`, AND `ttyAMA0` present as devices, but the active serial getty always runs on `ttyAMA0`. The kernel cmdline uses `console=ttyAMA0`.

| Arch | Active serial TTY | Getty service | Kernel params |
|---|---|---|---|
| x86_64 | `ttyS0` | `serial-getty@ttyS0.service` | `console=ttyS0,115200` |
| aarch64 | `ttyAMA0` | `serial-getty@ttyAMA0.service` | `console=ttyAMA0 earlycon=pl011,0xeffec000` |

### Boot Partition Layout

| Image type | Separate /boot | Boot on root | LVM |
|---|---|---|---|
| RHEL LVM (8/9/10) | Yes (xfs, ~1G) | No | Yes (rootvg) |
| RHEL raw (8/9/10) | No | Yes | No |
| RHEL 7.x | Yes (xfs, 494M) | No | Yes (rootvg) |
| Debian 11 Gen1 | Yes (separate partition) | No | No |
| Debian 12/13 | No | Yes | No |
| Ubuntu 24.04 | Yes (LABEL=BOOT, ext4) | No | No |
| SUSE 15 SP6/SP7 | Yes (xfs, ~1G) | No | No |
| SUSE 16 | No | Yes (btrfs subvols) | No |
| SUSE 12 SP5 | Yes (xfs, ~1G) | No | No |

### Filesystem Types

| Distro | Root FS | Boot FS |
|---|---|---|
| RHEL 7-10 | xfs | xfs |
| Debian 11-13 | ext4 | ext4 (when separate) |
| Ubuntu 24.04 | ext4 | ext4 |
| SUSE 12-15 | xfs | xfs |
| SUSE 16 | btrfs (with subvolumes) | btrfs (`@/boot/writable` subvol) |

### fstab Format

| Distro | Root mount | EFI mount |
|---|---|---|
| RHEL LVM | `/dev/mapper/rootvg-rootlv` | `UUID=...` |
| RHEL raw | `UUID=...` | `UUID=...` |
| Debian | `PARTUUID=...` | `PARTUUID=...` |
| Ubuntu | `UUID=...` (root), `LABEL=BOOT` (boot) | `UUID=...` |
| SUSE | `UUID=...` | `UUID=...` |

### Package Manager

| Distro | Primary | Secondary |
|---|---|---|
| RHEL 7.x | `yum` | — |
| RHEL 8+ | `dnf` | `yum` (symlink) |
| Debian/Ubuntu | `apt-get` | — |
| SUSE | `zypper` | — |

### resolv.conf Type

| Distro | Type | Target | Nameserver |
|---|---|---|---|
| RHEL 7-10 | Regular file | N/A | `168.63.129.16` |
| Debian 11 | Regular file | N/A | `168.63.129.16` |
| Debian 12+ | Symlink | `/run/systemd/resolve/resolv.conf` | `168.63.129.16` |
| Debian 13 | Symlink | `../run/systemd/resolve/stub-resolv.conf` | `127.0.0.53` |
| Ubuntu 24.04 | Symlink | `../run/systemd/resolve/stub-resolv.conf` | `127.0.0.53` |
| SUSE 12 SP5 | Regular file | N/A | `168.63.129.16` |
| SUSE 15+ | Symlink | `/run/netconfig/resolv.conf` | `168.63.129.16` |
| SUSE 16 Gen1 | Regular file | N/A (NetworkManager) | `168.63.129.16` |

### Hyper-V Module Status

| Kernel type | hv_vmbus/storvsc/netvsc | Location |
|---|---|---|
| Debian cloud kernels | Loadable modules | `/lib/modules/.../kernel/drivers/hv/` |
| RHEL 8+ (x86_64) | NOT FOUND as .ko, loaded via lsmod | Likely compiled-in or special path |
| RHEL (aarch64) | Loadable modules | Standard path |
| SUSE 15 SP7+ (azure kernel) | NOT FOUND, none loaded | Built into kernel |
| SUSE 12 SP5 | Only `hyperv_fb` loaded | Minimal module set |
| Ubuntu 24.04 | NOT FOUND as .ko | Built into azure kernel |

### sudo Permissions

| Distro | Setuid bits | Binary path |
|---|---|---|
| RHEL | `4111` | `/usr/bin/sudo` (or `/bin/sudo`) |
| Debian/Ubuntu | `4755` | `/usr/bin/sudo` |
| SUSE | `4755` | `/usr/bin/sudo` |

### os-prober Status

| Distro | Installed | GRUB_DISABLE_OS_PROBER needed |
|---|---|---|
| RHEL 7-10 | Yes | **Critical** — rescue VM Ubuntu gets added |
| Ubuntu 24.04 | Yes | **Critical** — rescue VM Ubuntu gets added |
| Debian 11-13 | No (not available) | Not needed |
| SUSE 12-16 | No (not installed) | Not needed |

### GRUB Version by Distro

| Distro | GRUB version |
|---|---|
| RHEL 7.x | 2.02~beta2 |
| RHEL 8.x | 2.02~beta2 |
| RHEL 9.x | 2.06 |
| RHEL 10.x | 2.12 |
| Debian 11 | 2.06 |
| Debian 12 | 2.06 |
| Debian 13 | 2.12 |
| Ubuntu 24.04 | 2.12 |
| SUSE 12 SP5 | 2.02 |
| SUSE 15 SP6/SP7 | 2.12 |
| SUSE 16 | 2.12 |

### Debian arm64 Special Parameters

Debian 12/13 arm64 images include extra kernel parameters in `/etc/default/grub.d/`:
- `10_cloud_azure_arm64.cfg`: `initcall_blacklist=arm_pmu_acpi_init transparent_hugepage=madvise`
- `20_console.cfg`: `console=ttyAMA0 earlycon=pl011,0xeffec000`

These must be preserved by the serialconsole action.

---

## Key Design Rules for ALAR Scripts

1. **Always** prefix `grub2-mkconfig` and `update-grub` with `GRUB_DISABLE_OS_PROBER=true`
2. **Detect boot mode** via `/sys/firmware/efi` — NOT `/boot/efi` presence (Gen1 BIOS VMs have `/boot/efi` mounted)
3. **Detect architecture** via `uname -m` — returns `x86_64` or `aarch64`
4. **arm64 is always EFI** — no BIOS mode exists for aarch64 in Azure
5. **EFI grub.cfg should be a redirect shim** — use `configfile` for RHEL/Debian/Ubuntu, `source` for SUSE
6. **GRUB path**: `/boot/grub2/` for RHEL/SUSE, `/boot/grub/` for Debian/Ubuntu
7. **BLS handling** only needed for RHEL 8+ (`isRedHat=true` and `/boot/loader/entries/` exists)
8. **Serial TTY**: `ttyS0` for x86_64, `ttyAMA0` for aarch64 (all 7 arm64 images confirmed)
9. **Hyper-V drivers**: Add with `--add-drivers` on x86_64 only; skip on aarch64 (built-in)
10. **SLES 16 uses btrfs** with subvolumes — fstab rebuild must account for `@/` subvol entries

---

## Rescue VM Considerations

When using `az vm repair`, a Gen2 broken VM can be rescued using a **Gen1 Ubuntu** rescue VM.
This has critical implications:

- **os-prober contamination**: The rescue VM's Ubuntu will be detected by `os-prober` during `grub2-mkconfig`. This is why `GRUB_DISABLE_OS_PROBER=true` is mandatory on ALL grub regeneration calls.
- **Boot mode detection inside chroot**: `/sys/firmware/efi` inside the chroot reflects the **rescue VM's** boot mode (Gen1 = BIOS), not the broken disk's. The broken disk's boot mode must be detected from its partition layout (presence of EFI partition type `EF00`) or the `efi_part_path` environment variable set by ALAR.
- **Architecture mismatch**: arm64 VMs can only be rescued by arm64 rescue VMs. x86_64 VMs can only be rescued by x86_64 rescue VMs. Azure handles this automatically.
- **Disk device path**: The broken disk is attached as a data disk (typically `/dev/sdc` or LUN0). ALAR resolves this via `/dev/disk/azure/scsi1/lun0` and passes it as `$RECOVER_DISK_PATH`.
- **NVMe on rescue VM**: Even if the broken VM used NVMe, the attached data disk on the rescue VM appears as SCSI. The NVMe partition naming (`nvme0n1p*`) from the original VM does NOT apply to the recovery scenario.
- **LVM on both**: If both the rescue VM and the broken disk use LVM with `rootvg`, ALAR renames the broken disk's VG to `oldvg` during recovery to avoid conflicts. Only RHEL 7.x and 8.x rescue VMs are supported for LVM-on-LVM scenarios.
