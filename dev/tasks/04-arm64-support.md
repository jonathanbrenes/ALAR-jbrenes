# Task 04 — No arm64 (aarch64) support in boot-related scripts

- **Priority**: 2 (High)
- **Type**: Enhancement
- **Scripts**: `grubfix-impl.sh`, `efifix-impl.sh`, `serialconsole-impl.sh`, `initrd-impl.sh`, `kernel-impl.sh`
- **Repo**: https://github.com/jonathanbrenes/ALAR-jbrenes/tree/main/dev

## Problem

All boot-related scripts assume x86_64. arm64 Azure VMs exist for RHEL 8-10, AlmaLinux 8-10, Debian 12-13, Ubuntu 20.04-25.10, SUSE 15+, and Azure Linux 3. They have different package names, grub targets, serial TTY, and Hyper-V driver requirements.

## Key differences (arm64 vs x86_64)

| Aspect | x86_64 | arm64 |
|---|---|---|
| Boot mode | BIOS or EFI | **Always EFI** |
| GRUB target | `i386-pc` (BIOS) / `x86_64-efi` | `arm64-efi` |
| RHEL EFI packages | `grub2-efi-x64 shim-x64` | `grub2-efi-aa64 shim-aa64` |
| Debian EFI packages | `grub-efi-amd64-signed` | `grub-efi-arm64-signed` |
| Ubuntu EFI packages | `grub-efi-amd64-signed shim-signed` | `grub-efi-arm64-signed shim-signed` |
| SUSE EFI packages | `grub2-x86_64-efi` | `grub2-arm64-efi` |
| Serial TTY | `ttyS0` | `ttyAMA0` |
| Hyper-V modules | Loadable (need dracut `--add-drivers`) | **Built-in** (skip `--add-drivers`) |

## Affected lines

### efifix-impl.sh

- **Line 27**: `yum reinstall -y grub2-efi-x64 shim-x64` — hardcoded x86_64 packages
- **Line 139**: `grub-install --target=x86_64-efi $device` — hardcoded grub target
- **Line 138**: `apt-get install -y --reinstall grub-efi` — needs arch-specific package

### grubfix-impl.sh

- **Line 23**: `grub2-install --target i386-pc` — only BIOS target, no arm64 EFI path

### serialconsole-impl.sh

- **Line 29**: `console=ttyS0,115200n8 earlyprintk=ttyS0,115200` — hardcoded `ttyS0`, should be `ttyAMA0` on arm64
- **Line 56**: Same hardcoded `ttyS0` in the fallback template

### initrd-impl.sh

- **Line 31**: `dracut -f -v --add-drivers "hv_vmbus hv_netvsc hv_storvsc"` — unnecessary on arm64 (built-in)
- **Line 52-54**: `echo "hv_vmbus"` etc. to initramfs-tools modules — unnecessary on arm64

## How to fix

Detect architecture at runtime with `uname -m` and branch accordingly:

```bash
ARCH=$(uname -m)

# Package selection
if [[ "$ARCH" == "aarch64" ]]; then
    EFI_PKGS="grub2-efi-aa64 shim-aa64"   # RHEL example
    GRUB_TARGET="arm64-efi"
    SERIAL_TTY="ttyAMA0"
else
    EFI_PKGS="grub2-efi-x64 shim-x64"
    GRUB_TARGET="x86_64-efi"
    SERIAL_TTY="ttyS0"
fi
```

For Hyper-V drivers, check `modules.builtin` before adding:
```bash
if ! grep -q hv_vmbus /lib/modules/$(uname -r)/modules.builtin 2>/dev/null; then
    dracut -f -v --add-drivers "hv_vmbus hv_netvsc hv_storvsc" ...
else
    dracut -f -v ...
fi
```
