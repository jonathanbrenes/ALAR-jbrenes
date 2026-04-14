# ALAR2 — AI Workflow Guide

## Starter Prompt (Quick Copy/Paste)

Use this as the first message in Copilot Chat (or any AI agent):

```text
Use `dev/AI_WORKFLOW.md` as mandatory guidance for this session.
Also load `dev/vm-data-consolidated.json` for full VM reference data.
Check `dev/backlog.md` before making any changes.
```

ROLE:

- You are a senior systems engineer working on ALAR (Azure Linux Auto Recover).
- You write minimal, idiomatic, production-quality shell scripts and Rust code.
- You prefer safe APIs and surgical changes.

RULES:

1. Apply only minimal, surgical changes. Preserve current behavior unless explicitly requested.
2. No hardcoded credentials or example passwords in any file. Use `<your-secure-password>` placeholder in docs.
3. Always use the WSL terminal session for git and shell operations.
4. Before any commit, run `git diff --stat`, show the proposed commit message, and ask for approval.
5. After commit, ask separately whether to push.
6. If a request is ambiguous, ask 1-3 clarifying questions before editing.
7. Do not refactor unrelated sections or add features beyond what was asked.
8. Always prefix `grub2-mkconfig` and `update-grub` with `GRUB_DISABLE_OS_PROBER=true`.
9. Use `$efi_part_path` (non-empty = EFI) for boot mode detection — `/sys/firmware/efi` reflects the rescue VM, not the broken disk.
10. When listing VM images in tables or reports, sort by Publisher first, then by Offer/SKU.

REFERENCES:

- `dev/AI_WORKFLOW.md` — project conventions, distro reference, design system
- `dev/backlog.md` — known bugs and enhancements (23+ items)
- `dev/vm-data-consolidated.json` — raw data from 148 Azure VM images
- `dev/alar-bootfix-unification.instructions.md` — bootfix project plan
- `README.md` — user-facing documentation

When finished, provide: what changed, validation steps, and any risks.

---

## Quick Do / Don't

**Do**

- Check `dev/backlog.md` before modifying any action script.
- Use the distro tables in this file for correct commands, paths, and packages.
- Test with `dev/test-action.sh --dry-run` on a matching VM before live runs.
- Review diffs before committing.

**Don't**

- Don't refactor unrelated sections.
- Don't combine multiple large requests in one prompt.
- Don't hardcode passwords or credentials anywhere.
- Don't add features, comments, or type annotations beyond what was requested.
- Don't use `/sys/firmware/efi` for boot mode detection (it reflects the rescue VM).
- Don't omit `GRUB_DISABLE_OS_PROBER=true` from any `grub2-mkconfig` or `update-grub` call.

---

## Project Overview

ALAR (Azure Linux Auto Recover) recovers non-bootable Azure Linux VMs by running
repair actions inside a chroot on the broken VM's disk.

### How it works

1. A rescue VM (typically Gen1 Ubuntu) is created via `az vm repair create`
2. The broken VM's OS disk is attached as a **data disk** to the rescue VM
3. ALAR detects the distro, mounts partitions, prepares a chroot at `/srv/rescue-root/`
4. Environment variables are set (distro flags, disk paths, partition numbers)
5. Action scripts from `src/action_implementation/` are executed inside the chroot
6. After recovery, the disk is detached and reattached to the original VM

### Rescue VM implications

- The rescue VM is Gen1 Ubuntu — `/sys/firmware/efi` inside chroot reflects the rescue VM (BIOS), NOT the broken disk
- `os-prober` on the rescue VM detects its Ubuntu — `GRUB_DISABLE_OS_PROBER=true` is mandatory on ALL grub regeneration calls
- The broken disk appears as SCSI even if the original VM used NVMe
- Architecture always matches (x86_64 rescue for x86_64, arm64 for arm64)
- If both rescue and broken disk use LVM `rootvg`, ALAR renames the broken disk's VG to `oldvg`

---

## Architecture

```text
src/action_implementation/   # Shell scripts — the actual recovery logic
  grubfix-impl.sh            # Gen1/BIOS boot repair
  efifix-impl.sh             # Gen2/EFI boot repair
  serialconsole-impl.sh      # Serial console configuration
  initrd-impl.sh             # Initramfs/initrd rebuild
  kernel-impl.sh             # Kernel rollback
  fstab-impl.sh              # fstab repair
  auditd-impl.sh             # Auditd HALT rule fix + disk space
  sudo-impl.sh               # Sudoers permissions fix
  helpers.sh                 # Shared utility functions (backup, checkPerm, etc.)
dev/                         # Development tools and reference data
  backlog.md                 # ← KNOWN BUGS AND ENHANCEMENTS (23 items)
  vm-data-consolidated.json  # ← RAW DATA FROM 132 VMs (load for full context)
  vm-reference-data.md       # Extended reference tables
  alar-bootfix-unification.instructions.md  # Bootfix project plan
  collect-vm-info.yml        # Ansible playbook to collect VM data (sanitizes inline)
  merge-vm-data.py           # Merge new results into vm-data-consolidated.json
  test-action.sh             # Test harness for running action scripts
```

---

## Environment Variables Available to Action Scripts

Set by the binary before script execution inside chroot:

| Variable | Description |
|---|---|
| `isRedHat` | `"true"` if RHEL, CentOS, Alma, Rocky, Oracle |
| `isUbuntu` | `"true"` if Ubuntu |
| `isDebian` | `"true"` if Debian |
| `isSuse` | `"true"` if SLES/openSUSE |
| `isAzureLinux` | `"true"` if Azure Linux / Mariner |
| `DISTRONAME` | Pretty name (e.g., `'Red Hat Enterprise Linux'`) |
| `DISTROVERSION` | VERSION_ID (e.g., `9.7`) |
| `DISTROSUBTYPE` | `CentOS`, `AlmaLinux`, `RockyLinux`, `OracleLinux`, or `None` |
| `RECOVER_DISK_PATH` | Device path of the broken disk (e.g., `/dev/sdc`) |
| `efi_part_path` | EFI partition device (e.g., `/dev/sdc1`) — **empty if no EFI** |
| `boot_part_path` | Boot partition device — **empty if boot is on root** |
| `EFI_PARTITION` | EFI partition number |
| `BOOT_PARTITION` | Boot partition number |
| `OS_PARTITION` | OS/root partition number |
| `isLVM` | `"true"` if LVM detected |

Architecture is NOT exported — detect with `uname -m` (returns `x86_64` or `aarch64`).
Boot mode: use `$efi_part_path` (non-empty = EFI) as primary signal, `/sys/firmware/efi` as fallback.

---

## Distro Quick Reference (from 148 VMs)

### GRUB Commands and Paths

| Distro | grub-install | grub-mkconfig | GRUB path | Vendor EFI dir |
|---|---|---|---|---|
| RHEL 7-10 | `grub2-install` | `grub2-mkconfig` | `/boot/grub2/` | `redhat` |
| Oracle Linux 7.9-10 | `grub2-install` | `grub2-mkconfig` | `/boot/grub2/` | `redhat` |
| AlmaLinux 8-10 | `grub2-install` | `grub2-mkconfig` | `/boot/grub2/` | `almalinux` |
| Debian 11-13 | `grub-install` | `update-grub` | `/boot/grub/` | `debian` |
| Ubuntu 20.04-25.10 | `grub-install` | `update-grub` | `/boot/grub/` | `ubuntu` |
| Azure Linux 3 | `grub2-install` | `grub2-mkconfig` | `/boot/grub2/` | **none** (BOOT only) |
| SUSE 12-16 | `grub2-install` | `grub2-mkconfig` | `/boot/grub2/` | `BOOT` |

### EFI grub.cfg Redirect

| Distro | Method | Note |
|---|---|---|
| RHEL 8+ | `configfile` | Redirect shim to `/boot/grub2/grub.cfg` |
| Oracle Linux 9-10 x86 | `configfile` | Redirect shim to `/boot/grub2/grub.cfg` (vendor dir `redhat`) |
| Oracle Linux 8.10/9/10 arm64 | `bls_full_config` | Full BLS config in EFI grub.cfg (no separate redirect) |
| Oracle Linux 7.9/8.2 | Full standalone | **DIVERGED** — same issue as RHEL 7 |
| AlmaLinux 8-10 | `configfile` | Same as RHEL 8+ (vendor dir is `almalinux`) |
| RHEL 7.x | Full standalone | **DIVERGED** — two different full configs |
| Debian/Ubuntu | `configfile` | Redirect shim to `/boot/grub/grub.cfg` |
| SUSE 15+ | `source` | **NOT configfile** — must use `source` for SUSE |
| SUSE 12 | `normal` | Minimal redirect pattern |
| Azure Linux 3 | None | **No EFI grub.cfg** — no vendor dir, grub.cfg at `/boot/efi/boot/grub2/grub.cfg` |

### BLS, Packages, and Serial TTY

| Distro | BLS entries | EFI packages (x86_64) | EFI packages (arm64) | Serial TTY |
|---|---|---|---|---|
| RHEL 7 | No | `grub2-efi-x64 shim-x64` | N/A | `ttyS0` |
| RHEL 8-10 | Yes | `grub2-efi-x64 shim-x64` | `grub2-efi-aa64 shim-aa64` | `ttyS0` / `ttyAMA0` |
| Oracle Linux 7.9 | No | `grub2-efi-x64 shim-x64` | N/A | `ttyS0` |
| Oracle Linux 8.10-10 | Yes | `grub2-efi-x64 shim-x64` | `grub2-efi-aa64 shim-aa64` | `ttyS0` / `ttyAMA0` |
| AlmaLinux 8-10 | Yes | `grub2-efi-x64 shim-x64` | `grub2-efi-aa64 shim-aa64` | `ttyS0` / `ttyAMA0` |
| Debian | No | `grub-efi-amd64-signed` | `grub-efi-arm64-signed` | `ttyS0` / `ttyAMA0` |
| Ubuntu | No | `grub-efi-amd64-signed shim-signed` | `grub-efi-arm64-signed shim-signed` | `ttyS0` / `ttyAMA0` |
| Azure Linux 3 | No | `grub2-efi-binary shim` | `grub2-efi-binary shim` | `ttyS0` / `ttyAMA0` |
| SUSE | No | `grub2-x86_64-efi` | `grub2-arm64-efi` | `ttyS0` / `ttyAMA0` |

### Other Distro-Specific Facts

| Distro | Package mgr | Root FS | sudo bits | os-prober installed |
|---|---|---|---|---|
| RHEL 7 | `yum` | xfs | `4111` | Yes — **critical** |
| RHEL 8+ | `dnf` | xfs | `4111` | Yes — **critical** |
| Oracle Linux 7.9 | `yum` | xfs | `4111` | Yes — **critical** |
| Oracle Linux 8.10-10 | `dnf` (`yum` available) | xfs | `4111` | Yes — **critical** |
| AlmaLinux 8-10 | `dnf` | xfs | `4111` | Yes — **critical** |
| Debian 11-13 | `apt-get` | ext4 | `4755` | No |
| Ubuntu 20.04-22.04 | `apt-get` | ext4 | `4755` | x86 server/minimal/Pro: Yes; arm64: No |
| Ubuntu 24.04 | `apt-get` | ext4 | `4755` | Server/Pro: Yes; Minimal: No |
| Ubuntu 25.10 | `apt-get` | ext4 | `4755` (sudo-rs via symlink) | Server: Yes; Minimal: No |
| Azure Linux 3 | `tdnf`/`dnf` | ext4 | `4755` | No |
| SUSE 12-15 | `zypper` | xfs | `4755` | No |
| SUSE 16 | `zypper` | **btrfs** (subvols) | `4755` | No |

---

## Critical Design Rules

1. **ALWAYS** prefix `grub2-mkconfig` and `update-grub` with `GRUB_DISABLE_OS_PROBER=true`
2. **Boot mode detection**: Use `$efi_part_path` (primary) — `/sys/firmware/efi` reflects the rescue VM, not the broken disk
3. **arm64 is always EFI** — no BIOS mode for aarch64 in Azure
4. **EFI grub.cfg must be a redirect shim** — `configfile` for RHEL/Debian/Ubuntu, `source` for SUSE
5. **GRUB path**: `/boot/grub2/` for RHEL/SUSE, `/boot/grub/` for Debian/Ubuntu
6. **BLS handling** for RHEL 8+, Oracle Linux 8.10+ — check `/boot/loader/entries/` for actual entries
7. **Serial TTY**: `ttyS0` for x86_64, `ttyAMA0` for aarch64 (all arm64 images confirmed)
8. **Hyper-V drivers**: Skip `--add-drivers` when modules are built-in (all Ubuntu 20.04-25.10, all Azure Linux 3, all aarch64, some SUSE x86); check `modules.builtin` at runtime
9. **SLES 16 uses btrfs** with `@/` subvolumes — fstab must preserve them
10. **sudo bits**: RHEL = `4111`, Debian/Ubuntu/SUSE/AzureLinux = `4755` (Ubuntu 25.10 uses a symlinked sudo)
11. **Azure Linux 3**: Uses `grub2-*` commands, `/boot/grub2/`, `tdnf`/`dnf`, dracut, no EFI vendor dir, NVMe-native with separate `/boot`
12. **SLES 16 btrfs**: `findmnt -o SOURCE /` returns path with subvolume brackets (e.g., `/dev/nvme0n1p3[/@/.snapshots/1/snapshot]`) — must strip `[...]` before passing to `lsblk` or other block device tools
13. **Oracle Linux** behaves like RHEL: `grub2-*` commands, `/boot/grub2/`, `redhat` EFI vendor dir, BLS on 8.10+, `4111` sudo, LVM with `rootvg`, UUID-based fstab, os-prober on all images. ALAR sees it as `DISTROSUBTYPE=OracleLinux` under `isRedHat=true`

---

## Working on ALAR — Guidance by Task

### Modifying any action script
1. Read the script from `src/action_implementation/<name>-impl.sh`
2. Check `dev/backlog.md` for known bugs related to that script
3. Use the distro tables above for correct commands/paths
4. Test with `dev/test-action.sh --dry-run` on a matching VM

### Working on boot actions (grubfix, efifix, serialconsole, initrd, kernel)
- Read `dev/alar-bootfix-unification.instructions.md` for the bootfix project plan
- The plan covers unifying grubfix + efifix, adding arm64, BLS, and os-prober fixes

### Adding support for a new distro or image
1. Run `dev/collect-vm-info.yml` against the new VM (output is pre-sanitized)
2. Merge with `python dev/merge-vm-data.py results.json -o dev/vm-data-consolidated.json`
3. Update tables above and `dev/backlog.md` if new issues found

### Checking known bugs
- Read `dev/backlog.md` — 23 items: Critical (3), High (7), Medium (7), Low (6)
- Items 1-3 are most impactful: bootfix unification, missing `GRUB_DISABLE_OS_PROBER`, typos
- Item #23: BLS entries deleted — recovery when `/boot/loader/entries/` is missing on RHEL 8+
- Items 17-22 are from the 132-VM analysis: sudo-rs symlink, Azure Linux 3 EFI/NVMe/packages, os-prober patterns, Hyper-V built-in scope

### Testing changes
1. Deploy a test VM matching target distro/arch/generation
2. `sudo ./dev/test-action.sh <action> --script-dir /path/to/scripts --dry-run`
3. Verify environment, then run without `--dry-run`
4. Reboot VM and verify it boots

---

## Git Workflow Rules

These rules apply to all git operations in this repository.

### Commit Process

- Before any commit, run `git diff --stat` to review changes.
- Show the exact proposed commit message and ask for approval before committing.
- After approval and commit, ask separately whether to push.
- When outputting markdown content for commits or pull requests, present it inside a fenced `text` code block.

### Commit Message Format

- Use a short subject line (50 chars or less).
- If a body is needed, separate it from the subject with a blank line.
- Use bullet points in the body for multiple changes.
- If the commit message is longer than a simple one-liner, write it to a temporary file (e.g., `.commit_msg.md`) and commit with `git commit -F .commit_msg.md`.
- Delete the temporary file after the commit succeeds.

### Terminal

- Always use the WSL terminal session for git operations.
- Use `/mnt/c/Users/<username>/...` paths (not `~/Repos/`).

### Project-Specific Rules

- Update `dev/README.md` only for major behavior/workflow changes.
- When listing VM images in tables or reports, always sort by Publisher first, then by Offer/SKU.
- All files under `dev/` must be UTF-8 without BOM. Before committing, verify no BOM is present (first 3 bytes must not be `EF BB BF`).

### `.gitattributes` Rules

Every repository must include a `.gitattributes` file. Use this baseline plus project-specific extensions:

```text
# Normalize all text files to LF (Linux targets)
* text=auto eol=lf

# Force LF for common text formats
*.sh text eol=lf
*.md text eol=lf
*.yml text eol=lf
*.yaml text eol=lf
*.json text eol=lf
*.conf text eol=lf
*.html text eol=lf
*.css text eol=lf
*.js text eol=lf
*.py text eol=lf

# Rust-specific
*.rs text eol=lf
*.toml text eol=lf

# Shell helpers
*.awk text eol=lf

# Force CRLF for Windows-only scripts
*.bat text eol=crlf
*.ps1 text eol=crlf

# Binary files — do not normalize
*.png binary
*.jpg binary
*.jpeg binary
*.gif binary
*.ico binary
*.pdf binary
*.zip binary
*.gz binary
*.7z binary
```

### `.gitignore` Rules

Every repository must include a `.gitignore` file. Use this baseline and add project-specific patterns:

```text
# Editor and IDE
.vscode/
.idea/
*.suo
*.user
.vs/

# OS files
.DS_Store
Thumbs.db

# Temporary files
*.tmp
*.bak
*~
.commit_msg.md

# Python
__pycache__/
*.py[cod]
*$py.class
.venv/
venv/
env/
*.egg-info/
.eggs/
dist/
build/

# Rust
target/
**/*.rs.bk
Cargo.lock

# Logs
*.log
```

---

## Markdown Style Rules

Follow these conventions in all `.md` files in this project.

### Headings

- One `#` (H1) per file as the document title.
- `##` (H2) for top-level sections, `###` (H3) for subsections. Use `####` (H4) only for numbered step-by-step detail within feature specs.
- No trailing punctuation on headings.
- One blank line before and after every heading.

### Lists

- Use `-` for unordered lists (never `*` or `+`).
- Use `1. 2. 3.` for ordered lists.
- Compact style: no blank lines between items within a list.
- One blank line before and after a list block.
- End list items with a period when they are full sentences; omit for fragments.

### Code

- Wrap filenames, variable names, function names, CLI commands, and config keys in inline backticks.
- Use fenced code blocks with a language tag for multi-line examples: `bash`, `text`, `json`, `yaml`, `powershell`.
- Never use a bare fenced block without a language tag.

### Tables

- Pipe-delimited: `| Header | Header |`.
- Separator row uses hyphens only: `|---|---|`.
- One blank line before and after every table.
- Keep cells concise; use backticks for code within cells.

### Emphasis

- Use `**bold**` for key concepts being introduced or emphasized.
- Prefer backticks over bold for technical terms.
- Avoid italic; use backticks or bold instead.

### Links

- Always use inline format: `[Display Text](URL)`.
- No bare URLs.
- Internal anchor links use lowercase-hyphenated IDs.

### Spacing and Whitespace

- Single blank line between sections, after headings, and around tables/code blocks.
- No double-blank-line gaps.
- No trailing whitespace on any line.
- Semantic line breaks (content-driven wrapping); no hard line-length limit.

### Files

- All files must be UTF-8 without BOM.
- One H1 title per file.
- End every file with a single trailing newline.

---

## Conventions

- **No hardcoded credentials** — use interactive prompts or SSH keys.
- **No example passwords** in docs — use `<your-secure-password>` placeholder.
- **GRUB regeneration** — always prefix with `GRUB_DISABLE_OS_PROBER=true`.
- **Boot mode detection** — use `$efi_part_path` (non-empty = EFI), never `/sys/firmware/efi`.
- **arm64 is always EFI** — no BIOS mode for aarch64 in Azure.
- **EFI grub.cfg** must be a redirect shim — `configfile` for RHEL/Debian/Ubuntu, `source` for SUSE.
- **Hyper-V drivers** — skip `--add-drivers` when modules are built-in; check `modules.builtin` at runtime.
- **Serial TTY** — `ttyS0` for x86_64, `ttyAMA0` for aarch64.


## Visual Design System (Frontend Reference)

This section documents every visual token, font, color, spacing value, and component pattern used in the ARM Template Builder UI. Use this as the authoritative reference when creating pages that must match the existing look and feel.

### CSS Custom Properties (`:root`)

| Variable | Value | Purpose |
|---|---|---|
| `--bg` | `#ffffff` | Page background |
| `--card` | `#ffffff` | Card background |
| `--border` | `#edebe9` | Default border color |
| `--text` | `#201f1e` | Primary text color |
| `--muted` | `#605e5c` | Secondary / hint text |
| `--primary` | `#0078d4` | Primary action (Azure blue) |
| `--danger` | `#b91c1c` | Danger / destructive actions |
| `--headerBg` | `#0078d4` | Header background |
| `--headerText` | `#ffffff` | Header text |
| `--mono` | `ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace` | Monospace font stack |
| `--sans` | `system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji", "Segoe UI Emoji"` | Sans-serif font stack |

### Typography

| Context | Font | Size | Weight | Line-height |
|---|---|---|---|---|
| Body | `var(--sans)` | `14px` | normal | default |
| Header title | `var(--sans)` | inherit | `800` | default |
| Card title / `h3` | `var(--sans)` | `16px` | `700` | default |
| Labels | `var(--sans)` | `12px` | `900` | default |
| Inputs / selects | `var(--sans)` | `14px` | normal | default |
| Textarea | `var(--mono)` | `12px` | normal | `1.35` |
| Tabs | `var(--sans)` | `13px` | `900` | default |
| Muted text | `var(--sans)` | `13px` | normal | default |
| Error text | `var(--sans)` | `12px` | `700` | default |
| Pills | `var(--sans)` | `12px` | `900` | default |
| Toast | `var(--sans)` | `13px` | normal | `1.35` |
| Toast title | `var(--sans)` | `13px` | `900` | `1.35` |
| Help balloon | `var(--sans)` | `13px` | `400` | `1.45` |
| `code.inline` | `var(--mono)` | `12px` | normal | default |
| Summary table | `var(--sans)` | `12px` | normal | default |
| Summary table `th` | `var(--sans)` | `12px` | `900` | default |

Text rendering: `-webkit-font-smoothing: antialiased`.

### Color Palette

| Color | Usage |
|---|---|
| `#ffffff` | Backgrounds (page, card, inputs, buttons, overlays) |
| `#201f1e` | Primary text (`--text`) |
| `#605e5c` | Muted/secondary text (`--muted`) |
| `#0078d4` | Primary action, header bg, active tab border/text (`--primary`) |
| `#b91c1c` | Danger text, error messages (`--danger`) |
| `#edebe9` | Default border color (`--border`) |
| `#eef2ff` | Active tab background |
| `#f8f8f8` | Summary table `th` background |
| `#f7f7f7` | Default pill background |
| `#f3f4f6` | `code.inline` background |
| `#e5e7eb` | `code.inline` border |
| `#111827` | Toast background |
| `#fff7e6` | Warning pill / deploy flow background |
| `#f3d08b` | Warning pill / deploy flow border |
| `#ecfdf3` | OK pill background |
| `#b7e3c4` | OK pill border |
| `#e8f0f8` | Chip button background |
| `#c9d8e6` | Chip button border |
| `rgba(0,0,0,0.04)` | Card shadow |
| `rgba(0,0,0,0.12)` | Help balloon/dropdown shadow |
| `rgba(0,0,0,0.18)` | Toast/extra options shadow |
| `rgba(0,0,0,0.22)` | Modal/dialog shadow |
| `rgba(0,0,0,0.35)` | Reset overlay backdrop |

### Spacing

| Element | Value |
|---|---|
| Header padding | `12px 16px` |
| Container padding | `16px`, max-width `1500px`, centered |
| Card padding | `12px` |
| Grid gap | `12px` |
| Row gap | `8px` |
| Form gap | `10px` |
| Tab padding | `6px 10px` |
| Input/select/textarea padding | `10px` |
| Button padding | `8px 10px` |
| Label margin-bottom | `6px` |
| Section margin-top | `12px` |
| Pill padding | `2px 8px` |
| Toast position | `fixed; right: 16px; bottom: 16px` |
| Toast padding | `10px 12px` |
| Summary table cell padding | `6px 8px` |

### Borders and Radii

| Element | Border | Radius |
|---|---|---|
| Card | `1px solid var(--border)` | `10px` |
| Inputs/selects/textarea | `1px solid var(--border)` | `8px` |
| Buttons | `1px solid var(--border)` | `8px` |
| Primary button | `1px solid var(--primary)` | `8px` |
| Tabs (pill-style) | `1px solid var(--border)` | `999px` |
| Active tab | `1px solid var(--primary)` | `999px` |
| Pills | `1px solid var(--border)` | `999px` |
| Help balloon | `1px solid var(--border)` | `10px` |
| Toast | `1px solid var(--border)` | `10px` |
| Modal windows | `1px solid var(--border)` | `12px` |
| Filter panel | `1px solid var(--border)` | `10px` |
| Chip buttons | `1px solid #c9d8e6` | `999px` |
| `code.inline` | `1px solid #e5e7eb` | `6px` |

### Shadows

| Element | Value |
|---|---|
| Header | `inset 0 -1px 0 rgba(255,255,255,0.18)` |
| Card | `0 1px 2px rgba(0,0,0,0.04)` |
| Help balloon | `0 8px 24px rgba(0,0,0,0.12)` |
| Toast | `0 10px 25px rgba(0,0,0,0.18)` |
| Modal windows | `0 20px 40px rgba(0,0,0,0.22)` |
| Filter panel | `0 12px 28px rgba(0,0,0,0.16)` |
| Dropdown menus | `0 4px 12px rgba(0,0,0,0.12)` |

### Layout

- Global: `* { box-sizing: border-box }`, `body { margin: 0; scrollbar-gutter: stable }`
- Container: `max-width: 1500px; margin: 0 auto; padding: 16px`
- Header: `position: sticky; top: 0; z-index: 100; display: flex; align-items: center; gap: 12px`
- Main grid: `1fr` then `1fr 1fr` at `>=1100px`
- Form grid: `1fr` then `1fr 1fr` at `>=720px`
- Card: `min-height: 420px; overflow: clip`
- Textarea: `min-height: 340px; resize: vertical`

Responsive breakpoints:
- `720px` — form two-column
- `900px` — filter panel two-column
- `980px` — extra options two-column
- `1100px` — main grid two-column

### Form Controls

| Control | Padding | Font | Background |
|---|---|---|---|
| `input, select` | `10px` | `14px var(--sans)` | `#fff` |
| `textarea` | `10px` | `12px var(--mono)`, lh `1.35` | `#fff` |
| `button` | `8px 10px` | `400 weight` | `#fff` |
| `button.primary` | `8px 10px` | `400 weight` | `var(--primary)`, text `#fff` |
| `button.danger` | `8px 10px` | `400 weight` | `#fff`, text `var(--danger)` |
| Disabled state | — | — | `opacity: 0.55; cursor: not-allowed` |

All inputs/selects/textareas are `width: 100%`.

### Component Patterns

- **Card**: White bg, rounded 10px, 1px border, subtle shadow, min-height 420px.
- **Tabs** (pill-style): Horizontal scroll, fully rounded (`999px`), active tab has primary border + blue text on `#eef2ff` bg.
- **Toast**: Fixed bottom-right, dark bg (`#111827`), slides up with `opacity .18s ease, transform .18s ease`.
- **Modal / expanded view**: Fixed `inset: 12px`, full-screen overlay, rounded 12px, heavy shadow.
- **Filter panel**: Absolutely positioned dropdown, focus-trapped, with OK/Cancel actions.
- **Pills**: Inline-block, rounded `999px`, variants: default (gray), `.warn` (yellow `#fff7e6`/`#f3d08b`), `.ok` (green `#ecfdf3`/`#b7e3c4`).
- **Button group**: Adjacent buttons with collapsed borders, first/last get outer radii.
- **Summary table**: `table-layout: fixed; width: 100%; border-collapse: collapse`, `th` bg `#f8f8f8`.

### Z-index Layers

| z-index | Element |
|---|---|
| `2` | Copy button overlay inside textarea |
| `30` | Help balloon |
| `40` | Size filter panel |
| `50` | Dropdown menu |
| `90` | Extra options panel |
| `100` | Sticky header |
| `110` | Expanded JSON modal |
| `9999` | Toast, reset overlay |
| `10001` | Deploy flow inline |

### Theme

Single light theme only. No dark mode, custom scrollbar styling, or print styles.

## Keyboard Navigation and Accessibility

This section documents every keyboard shortcut, focus management pattern, ARIA attribute, and screen reader feature. Follow these conventions when adding new components.

### Escape Key — Cascade Priority

The global `Escape` handler fires in this order. Each step checks if the component is open before acting. The grading expanded window returns early; all others continue down the chain.

| Priority | Component | Action |
|---|---|---|
| 1 | Size filter panel (local trap) | Closes panel, returns focus to trigger button |
| 2 | Reset confirmation overlay (temporary handler) | Dismisses overlay, removes itself |
| 3 | JSON flow window | Closes expanded JSON view |
| 4 | VM Summary flow window | Closes expanded summary view |
| 5 | Grading expanded window | Closes expanded playbook view, **returns early** |
| 6 | Grading flow window | Closes grading designer, returns focus to trigger button |
| 7 | Extra options panel | Closes panel, saves state |
| 8 | Filter panel (fallback) | Closes if still open |
| 9 | Help balloon | Hides balloon, sets `aria-hidden="true"` |

### Enter Key

| Context | Action |
|---|---|
| Reset confirmation overlay | Confirms reset: clears `localStorage` and reloads page |

### Tab Key — Focus Trapping

| Component | Behavior |
|---|---|
| Size filter panel | `Tab`/`Shift+Tab` cycles between first and last focusable element inside the panel. Focusable selector: `select, button, input, [tabindex]:not([tabindex="-1"])` |
| Grading flow window | Same focus-trap pattern. Focusable selector: `input, select, textarea, button, [tabindex]:not([tabindex="-1"])` filtered by `!el.disabled && el.offsetParent !== null` |

### Arrow Keys / Home / End

| Component | Keys | Behavior |
|---|---|---|
| VM tab bar (`role="tablist"`) | `ArrowRight` / `ArrowLeft` | Cycle through VM tabs with wrap-around |
| VM tab bar | `Home` | Jump to first tab |
| VM tab bar | `End` | Jump to last tab |

After arrow navigation, the new tab is rendered and receives `.focus()`.

### Click-Outside-to-Close

| Component | Mechanism |
|---|---|
| Help balloon | Global `document` click listener — if target is not inside `.help-wrap`, closes and sets `aria-hidden="true"` |
| Reset confirmation | Overlay `onclick` — if `e.target` is the backdrop itself, removes the overlay |

### Focus Management Rules

| Pattern | Details |
|---|---|
| **Roving tabindex on VM tabs** | Active tab gets `tabIndex = 0`, all others `-1`. Arrow keys update active index, re-render, and call `.focus()` on new tab. |
| **Dialog open** | On open, find first focusable element inside the dialog and call `.focus()`. |
| **Dialog close** | On close, return focus to the button that triggered the dialog (e.g., filter panel returns to `#addSizeFilterBtn`, grading returns to `#openGradingFlowBtn`). |
| **Add item** | After adding a new item (e.g., grading check), focus the first input inside the newly added card. |
| **Confirmation dialog** | After building the overlay, focus the confirm button. |

### ARIA Attributes Used

| Attribute | Where | Purpose |
|---|---|---|
| `role="tablist"` | `#tabs` div | VM tab bar container |
| `role="tab"` | Each VM tab button | Individual tab semantics |
| `aria-selected` | Each VM tab button | `"true"` on active, `"false"` on inactive |
| `role="dialog"` | Help balloon, filter panel, JSON flow, VM summary flow, grading flow, grading expanded | Dialog semantics |
| `aria-modal="true"` | Filter panel, JSON flow, VM summary flow, grading flow, grading expanded | Marks as modal |
| `aria-label` | All dialogs, maximize/minimize buttons | Descriptive label for screen readers |
| `aria-hidden` | Help balloon, share field wrappers, control VM lock overlay | Toggled on show/hide |
| `aria-controls` | Extra options toggle button | Points to `extraOptionsPanel` |
| `aria-expanded` | Extra options toggle button | `"true"` / `"false"` |
| `aria-live="polite"` | `#sizeFilterLive`, `#deployFlowInline`, `#toast` | Live region for screen reader announcements |
| `aria-atomic="true"` | Same as above | Entire region is announced on change |
| `tabindex="-1"` | Grading flow/expanded windows, inactive VM tabs | Programmatically focusable but not in tab order |
| `tabindex="0"` | Active VM tab | In natural tab order |

### Screen Reader Support

| Feature | Element | Details |
|---|---|---|
| `.sr-only` CSS class | Various | Visually hidden: `position:absolute; width:1px; height:1px; clip:rect(0,0,0,0)` |
| Filter result count | `#sizeFilterLive` | `aria-live="polite"` region announces e.g. *"3 of 45 VM sizes match current filters."* |
| Deploy flow messages | `#deployFlowInline` | `aria-live="polite"` region |
| Toast notifications | `#toast` | `aria-live="polite"` region, announced automatically |

### Header Buttons

The sticky header contains the app title on the left and action buttons on the right inside a `.help-wrap` container. All header buttons share a translucent "ghost" style to sit on the blue `--headerBg` background.

| Button | ID | Label | Purpose |
|---|---|---|---|
| Extra options | `#toggleExtraOptionsBtn` | `Extra options` | Opens the Extra Options panel (network config, storage toggles, NSG rules). Uses `aria-controls="extraOptionsPanel"` and `aria-expanded`. |
| Help | `#helpBtn` | `Help` | Toggles the help balloon dropdown with feature/usage summary. |

**Shared ghost-button style** (applies to both `#helpBtn` and `#toggleExtraOptionsBtn`):

| Property | Value |
|---|---|
| Border | `1px solid rgba(255,255,255,0.45)` |
| Background | `rgba(255,255,255,0.14)` |
| Background (hover) | `rgba(255,255,255,0.22)` |
| Color | `#fff` |
| Font size | `10px` |
| Padding | `3px 6px` |
| Border radius | `8px` (inherited from base button) |

**Extra options active state** (`aria-expanded="true"`): `border-color: #ffffff; background: rgba(255,255,255,0.30)`.

**Help balloon** (`.help-balloon`): Absolute dropdown positioned below the header (`top: calc(100% + 8px); right: 0`), width `min(520px, 90vw)`, white bg, `10px` radius, `z-index: 30`, `0 8px 24px rgba(0,0,0,0.12)` shadow. Toggled via `.show` class. Inner content: `h4` at `14px/700`, `ul` with `margin: 0 0 0 16px`, `li` with `4px` vertical margin, body at `13px/400/1.45`.