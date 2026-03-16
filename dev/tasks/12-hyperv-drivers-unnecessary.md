# Task 12 — initrd-impl.sh adds Hyper-V drivers unnecessarily

- **Priority**: 3 (Medium)
- **Type**: Bug
- **Script**: `src/action_implementation/initrd-impl.sh`
`initrd-impl.sh` unconditionally adds `hv_vmbus`, `hv_netvsc`, `hv_storvsc` via `--add-drivers` (dracut) or appending to `/etc/initramfs-tools/modules` (Ubuntu). On 48 of 97 VMs (pre-OL data) these modules are built into the kernel and the flag is unnecessary.

Built-in modules confirmed on:
- All 38 Ubuntu images (20.04-25.10, x86_64 and aarch64)
- All 6 Azure Linux 3 images (x86_64 and aarch64)
- All aarch64 images across all distros
- Some SUSE x86_64 images

Oracle Linux (all 16 images) has Hyper-V modules as **loadable** (not built-in) — same as RHEL. The `--add-drivers` flag is still needed for OL.

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

## Detection methods

Two complementary approaches to detect built-in modules:

1. **On-disk**: `/lib/modules/<kver>/modules.builtin` — lists modules compiled into the kernel image. Works even when kernel is not running (e.g., chroot recovery).
2. **Runtime sysfs**: `/sys/module/<module_name>` — confirms the module is active in the running kernel. Built-in modules lack the `coresize` file; loadable modules have it. The `initstate` attribute shows `live` for loaded modules.

For ALAR recovery (chroot context), prefer the `modules.builtin` check since the target kernel may not be running. The sysfs check is collected by `collect-vm-info.yml` for validation.

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

## Data collection

`collect-vm-info.yml` collects Hyper-V module state via three methods:
- `lsmod` — loaded modules (`hyperv.loaded_modules`)
- `modules.builtin` / `.ko*` file search — on-disk type (`hyperv.module_types`)
- `/sys/module/<name>` sysfs — runtime state with `initstate` and `coresize` (`hyperv.sysfs_module`)
