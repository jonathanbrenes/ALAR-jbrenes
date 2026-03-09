# Task 18 — os-prober not installed on Ubuntu minimal images (24.04+)

- **Priority**: 3 (Medium)
- **Type**: Design consideration / Documentation
- **Scripts**: All scripts using `GRUB_DISABLE_OS_PROBER=true`
- **Repo**: https://github.com/jonathanbrenes/ALAR-jbrenes/tree/main/dev

## Problem

Not all Ubuntu images have `os-prober` installed. The pattern varies by offer type and version:

| Image type | os-prober installed |
|:------|:------|
| Ubuntu 20.04-22.04 server (x86) | Yes |
| Ubuntu 20.04-22.04 minimal (x86) | Yes |
| Ubuntu 20.04-22.04 Pro (x86) | Yes |
| Ubuntu 20.04-22.04 arm64 (all) | No |
| Ubuntu 24.04 server / Pro | Yes |
| Ubuntu 24.04 minimal / Pro-minimal | **No** |
| Ubuntu 25.10 server | Yes |
| Ubuntu 25.10 minimal | **No** |
| All arm64 minimal images | No |

## Impact

`GRUB_DISABLE_OS_PROBER=true` is still required on server images because the rescue VM has os-prober. On minimal images without os-prober, the flag is a no-op — harmless but unnecessary.

## No code change required

Using `GRUB_DISABLE_OS_PROBER=true` universally is the correct approach:
- When os-prober is present: prevents adding rescue VM to grub menu
- When os-prober is absent: ignored, no side effects

This task is for documentation/awareness only. The session rule "ALWAYS prefix grub2-mkconfig/update-grub with GRUB_DISABLE_OS_PROBER=true" remains correct regardless.

## Close condition

Acknowledge that no code change is needed. Keep using `GRUB_DISABLE_OS_PROBER=true` unconditionally.
