# Task 29 — Oracle Linux os-prober installed on ALL images

- **Priority**: 3 (Low)
- **Type**: Confirmation
- **Backlog**: #30
- **Script**: All boot scripts (`grubfix-impl.sh`, `efifix-impl.sh`, `initrd-impl.sh`, `serialconsole-impl.sh`, `kernel-impl.sh`)
- **Related**: Task 02

## Confirmation

All 16 Oracle Linux images (7.9 through 10.0, all architectures and generations) have `os-prober` installed. This matches the RHEL pattern.

`GRUB_DISABLE_OS_PROBER=true` must be present in `/etc/default/grub` before any `grub2-mkconfig` call on Oracle Linux, or the rescue VM's Ubuntu will appear in the recovered VM's GRUB menu.

## Current code path

Oracle Linux is handled via `isRedHat=true` in the scripts. The `recover_redhat()` function in `grubfix-impl.sh` already prepends `GRUB_DISABLE_OS_PROBER=true` (added in Task 02 scope). Since OL uses the same RHEL code path, it is covered — no new code needed for grubfix.

However, per Task 02, other scripts (`efifix-impl.sh`, `initrd-impl.sh`, `serialconsole-impl.sh`, `kernel-impl.sh`) may still lack this prefix. This task confirms OL requires the same treatment as RHEL across all scripts.

## Data summary

| Image | os-prober installed | os-prober package |
|---|---|---|
| OL 7.9 | Yes | grub2-tools |
| OL 8.2 | Yes | grub2-tools |
| OL 8.10 | Yes | grub2-tools |
| OL 9.5/9.6 | Yes | grub2-tools |
| OL 10.0 | Yes | grub2-tools |

## Action

No new code change needed specifically for this task — OL flows through the RHEL path. Ensure Task 02 fixes cover all scripts, which will automatically handle OL.
