# Task 17 — Azure Linux 3: GRUB commands and package names differ

- **Priority**: 3 (Medium)
- **Type**: Enhancement
- **Scripts**: All boot-related scripts when Azure Linux support is extended
- **Repo**: https://github.com/jonathanbrenes/ALAR-jbrenes/tree/main/dev

## Problem

Azure Linux 3 uses different tools and paths than other distros. The current `grubfix-impl.sh` and `efifix-impl.sh` have Azure Linux sections, but they need verification and may need updates as the bootfix unification proceeds.

## Azure Linux 3 specifics

| Aspect | Azure Linux 3 | RHEL | Ubuntu |
|---|---|---|---|
| Package manager | `tdnf` / `dnf` | `dnf` / `yum` | `apt-get` |
| GRUB install | `grub2-install` | `grub2-install` | `grub-install` |
| GRUB mkconfig | `grub2-mkconfig` | `grub2-mkconfig` | `update-grub` |
| GRUB path | `/boot/grub2/` | `/boot/grub2/` | `/boot/grub/` |
| Initramfs tool | `dracut` (v102) | `dracut` | `update-initramfs` |
| EFI packages (x86) | `grub2-efi-binary shim` | `grub2-efi-x64 shim-x64` | `grub-efi-amd64-signed shim-signed` |
| EFI packages (arm64) | `grub2-efi-binary shim` | `grub2-efi-aa64 shim-aa64` | `grub-efi-arm64-signed shim-signed` |
| EFI vendor dir | **none** (only `BOOT/`) | `redhat` | `ubuntu` |
| Hyper-V modules | **Built-in** | Loadable | **Built-in** |
| `/boot` partition | Separate (500MB ext4) | On root (or LVM) | On root |

Note: Azure Linux EFI packages are NOT arch-suffixed (`grub2-efi-binary` for both x86 and arm64).

## Affected lines

### grubfix-impl.sh — `recover_azurelinux()` (lines 62-79)

```bash
tdnf install gdisk -y
tdnf reinstall gdisk -y
tdnf install grub2-pc -y
tdnf reinstall grub2-pc -y
```

This section handles BIOS only. For unified bootfix, EFI packages need to use `grub2-efi-binary` and `shim`.

### efifix-impl.sh — `recover_azurelinux()` (lines 78-132)

Already handles Azure Linux 3 EFI correctly with `dnf install grub2-efi -y` and `dnf reinstall grub2-efi-binary -y`. Verify package names match latest Azure Linux 3 images.

### initrd-impl.sh — `recover_azurelinux()` (lines 73-88)

```bash
if test /boot/initrd.img*; then
    # AzureLinux 2.0 — with drivers
    dracut -f -H --add-drivers '...' /boot/initrd-${kernel_version} ${kernel_version}
else
    # AzureLinux 3.0 — no hyperv drivers (built-in)
    dracut -f -H /boot/initramfs-${kernel_version}.img ${kernel_version}
fi
```

Already handles the built-in driver case. Good.

## How to fix

1. In the unified bootfix (Task 01), add Azure Linux as a first-class distro branch
2. Use `tdnf`/`dnf` for package operations (check both — `tdnf` is native, `dnf` is also available)
3. Use `grub2-efi-binary` and `shim` for EFI packages (same for x86 and arm64)
4. Handle the `no_efi_grubcfg` pattern — write grub.cfg at `/boot/efi/boot/grub2/grub.cfg`

## Related tasks

- Task 08 (no EFI vendor dir)
- Task 09 (NVMe + separate /boot)
- Task 01 (bootfix unification)
