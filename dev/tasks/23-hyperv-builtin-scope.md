# Task 23 — Hyper-V modules built-in on all Ubuntu and Azure Linux 3

- **Priority**: 4 (Low)
- **Type**: Confirmation / expansion of Task 12
- **Script**: `src/action_implementation/initrd-impl.sh`
- **Repo**: https://github.com/jonathanbrenes/ALAR-jbrenes/tree/main/dev

Task 12 covers the fix (check `modules.builtin` before adding Hyper-V drivers). This task documents the full scope from the 148-VM analysis (including 16 Oracle Linux images).

## Built-in vs loadable module status

| Distro | Hyper-V modules | Count |
|:------|:------|:------|
| Ubuntu 20.04-25.10 (all x86 + arm64) | **Built-in** | 38 images |
| Azure Linux 3 (all x86 + arm64) | **Built-in** | 6 images |
| All aarch64 images (all distros) | **Built-in** | ~20 images |
| SUSE (some x86_64) | **Built-in** | varies |
| RHEL 7-10 (x86_64) | Loadable | requires --add-drivers |
| Oracle Linux 7.9-10 (all) | Loadable | requires --add-drivers |
| AlmaLinux 8-10 (x86_64) | Loadable | requires --add-drivers |
| Debian 11-13 (x86_64) | Loadable | requires initramfs-tools modules |

**Total**: 48/97 images have Hyper-V modules built in (pre-OL data). Oracle Linux adds 16 loadable images, bringing the total dataset to 148 images.

## Detection methods

The collector playbook (`collect-vm-info.yml`) now gathers Hyper-V module state via three methods:
- **`modules.builtin`** — on-disk check, works in chroot (used by the fix in Task 12)
- **`lsmod`** — shows loaded modules at runtime
- **`/sys/module/<name>`** — sysfs runtime check; built-in modules lack `coresize` file, loadable modules have it; `initstate` shows `live` for active modules

All three are stored in the JSON report under `hyperv.module_types`, `hyperv.loaded_modules`, and `hyperv.sysfs_module` respectively.

## No additional code change beyond Task 12

The fix in Task 12 (checking `modules.builtin`) covers all cases. This task confirms the scope:
- Not just arm64 needs the skip — x86_64 Ubuntu and Azure Linux 3 also need it
- The runtime check approach works for all distros
- The sysfs `/sys/module` data cross-validates the `modules.builtin` findings

## Close condition

Close when Task 12 is implemented. This task provides the evidence and scope.
