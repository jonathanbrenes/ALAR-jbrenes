# Task 12 — initrd-impl.sh adds Hyper-V drivers unnecessarily

- **Priority**: 3 (Medium)
- **Type**: Bug
- **Script**: `src/action_implementation/initrd-impl.sh`
- **Repo**: https://github.com/jonathanbrenes/ALAR-jbrenes/tree/main/dev unconditionally adds `hv_vmbus`, `hv_netvsc`, `hv_storvsc` via `--add-drivers` (dracut) or appending to `/etc/initramfs-tools/modules` (Ubuntu). On 48 of 97 VMs these modules are built into the kernel and the flag is unnecessary.

Built-in modules confirmed on:
- All 38 Ubuntu images (20.04-25.10, x86_64 and aarch64)
- All 6 Azure Linux 3 images (x86_64 and aarch64)
- All aarch64 images across all distros
- Some SUSE x86_64 images

## Affected lines

### initrd-impl.sh — `recover_suse()` (line 31)

```bash
# Current (line 31)
dracut -f -v --add-drivers "hv_vmbus hv_netvsc hv_storvsc" /boot/$INITRD ${KERNVER}-$KERNBASE
```

### initrd-impl.sh — `recover_ubuntu()` (lines 52-54)

```bash
# Current (lines 52-54)
echo "hv_vmbus" >>/etc/initramfs-tools/modules
echo "hv_storvsc" >>/etc/initramfs-tools/modules
echo "hv_netvsc" >>/etc/initramfs-tools/modules
```

### initrd-impl.sh — `recover_redhat()` (line 67)

```bash
# Current (line 67)
dracut -f -v --add-drivers "hv_vmbus hv_netvsc hv_storvsc" /boot/initramfs-${kernel_version}.img ${kernel_version}
```

Note: `recover_azurelinux()` already handles this correctly — Azure Linux 3.0 path (line 86) skips `--add-drivers`.

## How to fix

Add a check before adding drivers:

```bash
# Helper function (add to helpers.sh or inline)
hyperv_builtin() {
    local kver="${1:-$(uname -r)}"
    grep -q hv_vmbus "/lib/modules/${kver}/modules.builtin" 2>/dev/null
}
```

Then in each distro function:

```bash
# recover_suse() — line 31
if hyperv_builtin "${KERNVER}-${KERNBASE}"; then
    dracut -f -v /boot/$INITRD ${KERNVER}-$KERNBASE
else
    dracut -f -v --add-drivers "hv_vmbus hv_netvsc hv_storvsc" /boot/$INITRD ${KERNVER}-$KERNBASE
fi

# recover_ubuntu() — lines 52-54
if ! hyperv_builtin "$kernel_version"; then
    echo "hv_vmbus" >>/etc/initramfs-tools/modules
    echo "hv_storvsc" >>/etc/initramfs-tools/modules
    echo "hv_netvsc" >>/etc/initramfs-tools/modules
fi

# recover_redhat() — line 67
if hyperv_builtin "$kernel_version"; then
    dracut -f -v /boot/initramfs-${kernel_version}.img ${kernel_version}
else
    dracut -f -v --add-drivers "hv_vmbus hv_netvsc hv_storvsc" /boot/initramfs-${kernel_version}.img ${kernel_version}
fi
```

## Related tasks

- Task 23 (confirmation that built-in scope extends beyond arm64)
