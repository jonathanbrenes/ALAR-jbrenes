# Task 23 — Hyper-V modules built-in on all Ubuntu and Azure Linux 3

- **Priority**: 4 (Low)
- **Type**: Confirmation / expansion of Task 12
- **Script**: `src/action_implementation/initrd-impl.sh`
- **Repo**: https://github.com/jonathanbrenes/ALAR-jbrenes/tree/main/dev

Task 12 covers the fix (check `modules.builtin` before adding Hyper-V drivers). This task documents the full scope from the 97-VM analysis.

## Built-in vs loadable module status

| Distro | Hyper-V modules | Count |
|---|---|---|
| Ubuntu 20.04-25.10 (all x86 + arm64) | **Built-in** | 38 images |
| Azure Linux 3 (all x86 + arm64) | **Built-in** | 6 images |
| All aarch64 images (all distros) | **Built-in** | ~20 images |
| SUSE (some x86_64) | **Built-in** | varies |
| RHEL 7-10 (x86_64) | Loadable | requires `--add-drivers` |
| AlmaLinux 8-10 (x86_64) | Loadable | requires `--add-drivers` |
| Debian 11-13 (x86_64) | Loadable | requires initramfs-tools modules |

**Total**: 48/97 images have Hyper-V modules built in.

## No additional code change beyond Task 12

The fix in Task 12 (checking `modules.builtin`) covers all cases. This task confirms the scope:
- Not just arm64 needs the skip — x86_64 Ubuntu and Azure Linux 3 also need it
- The runtime check approach works for all distros

## Close condition

Close when Task 12 is implemented. This task provides the evidence and scope.
