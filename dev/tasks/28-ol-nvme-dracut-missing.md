# Task 28 — Oracle Linux NVMe drivers missing in dracut on OL 7.9 and 8.2

- **Priority**: 2 (Medium)
- **Type**: Bug
- **Backlog**: #29
- **Script**: `src/action_implementation/initrd-impl.sh`

## Problem

Oracle Linux 7.9 and 8.2 do not have an `/etc/dracut.conf.d/azure.conf` file that includes NVMe drivers. All OL 8.10+ images have:

```
add_drivers+=" nvme pci-hyperv "
```

in `/etc/dracut.conf.d/azure.conf`, but OL 7.9 and 8.2 lack this entirely.

This means:
1. NVMe conversion (SCSI → NVMe) on OL 7.9/8.2 VMs will produce an initramfs without NVMe drivers
2. The VM will fail to boot after conversion because the root disk is no longer accessible

## Affected images

| Image | azure.conf NVMe | Impact |
|---|---|---|
| OL 7.9 (all generations) | Missing | NVMe conversion will fail |
| OL 8.2 (all generations) | Missing | NVMe conversion will fail |
| OL 8.10+ (all) | Present | OK |
| OL 9.x (all) | Present | OK |
| OL 10.x (all) | Present | OK |

## Fix

When regenerating initramfs on OL 7.9 or 8.2, ensure NVMe drivers are included:

```bash
# Option 1: Create azure.conf if missing
if [[ ! -f /etc/dracut.conf.d/azure.conf ]]; then
    echo 'add_drivers+=" nvme pci-hyperv "' > /etc/dracut.conf.d/azure.conf
fi

# Option 2: Pass drivers directly to dracut
dracut --force --add-drivers "nvme pci-hyperv" /boot/initramfs-$(uname -r).img $(uname -r)
```

## Verification

```bash
# After initramfs rebuild, verify NVMe module is included:
lsinitrd /boot/initramfs-$(uname -r).img | grep nvme
```
