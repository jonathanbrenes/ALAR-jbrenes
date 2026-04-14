# ALAR2 — AI Workflow Guide

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
11. Never commit or push directly to `main`. All work must happen on a dev branch. If the current branch is `main`, ask the user for a custom branch name or use the default `dev_<user>`.
12. Be concise. No preambles, no restating the request, no "Here's what I did" summaries unless asked.
13. Suppress verbose tool output. Use flags that minimize output (e.g., `--quiet`, `-q`). Do not echo full file contents after editing.
14. Do not repeat code that was not changed. When explaining edits, mention only the lines that changed.
15. Skip obvious confirmations. Do not say "I'll now edit the file" — just edit it.
16. Show only changed lines in explanations — not the full file or large surrounding blocks.
17. For terminal commands, pipe through `tail`, `head`, or `grep` when only specific output matters. Avoid dumping full logs.
18. Do not re-read files already visible in the conversation context.
19. Combine independent edits into a single multi-edit operation instead of sequential single edits.
20. When answering questions, lead with the answer. Skip background explanation unless asked.

REFERENCES:

- `.github/copilot-instructions.md` — this file (auto-loaded by Copilot Chat)
- `dev/backlog.md` — known bugs and enhancements (23+ items)
- `dev/vm-data-consolidated.json` — raw data from 148 Azure VM images
- `dev/alar-bootfix-unification.instructions.md` — bootfix project plan
- `README.md` — user-facing documentation
- Template source: [copilot-instructions-template](https://github.com/jbrenes_microsoft/copilot-instructions-template) — upstream template repository

When finished, provide: what changed, validation steps, and any risks.

---

## Quick Do / Don't

**Do**

- Check `dev/backlog.md` before modifying any action script.
- Use the distro tables in this file for correct commands, paths, and packages.
- Test with `dev/test-action.sh --dry-run` on a matching VM before live runs.
- Review diffs before committing.
- Prefer one multi-file edit over multiple single-file edits.
- Use `--quiet` or `-q` flags on git and package manager commands.

**Don't**

- Don't refactor unrelated sections.
- Don't combine multiple large requests in one prompt.
- Don't hardcode passwords or credentials anywhere.
- Don't add features, comments, or type annotations beyond what was requested.
- Don't use `/sys/firmware/efi` for boot mode detection (it reflects the rescue VM).
- Don't omit `GRUB_DISABLE_OS_PROBER=true` from any `grub2-mkconfig` or `update-grub` call.
- Don't restate the user's request before acting.
- Don't display full file contents after small edits.
- Don't add filler phrases like "Sure!", "Absolutely!", "Great question!".
- Don't echo back unchanged code blocks after edits.
- Don't explain what standard commands do (e.g., `git add`, `cd`).
- Don't narrate each step before doing it — just do it and confirm.
- Don't list unchanged files in summaries.

---

## Output Rules

- Responses must be concise. Target 1-3 sentences for simple tasks.
- After file edits, confirm with one line (e.g., "Updated `file.js` — added validation.").
- For multi-step work, use a brief numbered checklist, not prose paragraphs.
- Terminal output: only show the relevant lines. Truncate or filter verbose output.
- Never repeat the user's request back to them.
- Never start responses with filler ("Sure!", "Absolutely!", "Great question!").

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

## Session Persistence (`localStorage`)

The ARM Template Builder (`dev/test-lab-builder.html`) uses `localStorage` to survive refreshes and tab closes.

| Event | Action |
|---|---|
| User interaction (answer, navigate) | Save session to `localStorage` |
| Page load (valid session exists) | Restore and resume |
| Session complete or reset | Clear `localStorage` |

Store under a unique key (e.g., `appname_session`) as JSON. Include all state needed to resume: current position, user inputs, and any timers.

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

### Branch Strategy

- **Never push directly to `main`.** The `main` branch is protected and represents production-ready code.
- All changes must be made on a dev branch.
- If the current branch is `main`, ask the user for a custom branch name. If no preference is given, create `dev_<user>` (e.g., `dev_jbrenes`).
- Merge to `main` only through pull requests after review.

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

### Changelog Format

- Version header: `## [X.Y.Z] - YYYY-MM-DD` (ISO 8601 dates).
- Section headers under each version: `### Added`, `### Changed`, `### Fixed`, `### Removed`.
- One entry per calendar day; append to today's entry if one already exists.
- Each bullet is a feature/fix description in prose with backticks for code references.

### Files

- All files must be UTF-8 without BOM.
- One H1 title per file.
- End every file with a single trailing newline.

---

## Visual Design System (Frontend Reference)

This section documents every visual token, font, color, spacing value, and component pattern used in the ARM Template Builder UI (`dev/test-lab-builder.html`). Use this as the authoritative reference when creating pages that must match the existing look and feel.

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

---

## Keyboard Navigation and Accessibility

Every interactive element in `dev/test-lab-builder.html` must be fully operable with keyboard only.

### Escape Key — Cascade Priority

A single global `Escape` handler fires in priority order. Each step checks whether the component is open before acting. Add new entries at the appropriate priority when creating overlays or panels.

| Priority | Component | Action |
|---|---|---|
<!-- Fill in as components are built. Example:
| 1 | Modal dialog | Closes modal, returns focus to trigger button |
| 2 | Dropdown menu | Closes menu, returns focus to toggle |
| 3 | Tooltip / balloon | Hides, sets `aria-hidden="true"` |
-->

### Enter Key

| Context | Action |
|---|---|
<!-- Fill in as components are built. Example:
| Confirmation dialog focused | Confirms action |
| Search input focused | Submits search |
-->

### Tab Key — Focus Trapping

| Component | Behavior |
|---|---|
<!-- Fill in as components are built. Example:
| Modal dialog | `Tab`/`Shift+Tab` cycles between first and last focusable element inside the modal |
-->

### Arrow Keys

| Component | Keys | Behavior |
|---|---|---|
<!-- Fill in as components are built. Example:
| Tab bar (`role="tablist"`) | `ArrowRight` / `ArrowLeft` | Cycle through tabs with wrap-around |
-->

### Click-Outside-to-Close

| Component | Mechanism |
|---|---|
<!-- Fill in as components are built. Example:
| Dropdown menu | Global `document` click listener — if target is not inside `.menu-wrap`, closes menu |
-->

### Focus Management Rules

| Pattern | Details |
|---|---|
| **Dialog open** | On open, find the first focusable element inside the dialog and call `.focus()`. |
| **Dialog close** | On close, return focus to the button or element that triggered the dialog. |
| **Add item** | After dynamically adding an item (e.g., a new card or row), focus the first input inside the new element. |
| **Confirmation dialog** | After building the overlay, focus the confirm button. |
| **Roving tabindex** | For tab-like patterns: active item gets `tabIndex = 0`, all others `-1`. Arrow keys update active index and call `.focus()`. |

### ARIA Attributes

| Attribute | Where | Purpose |
|---|---|---|
| `role="dialog"` | Modal overlays, panels | Dialog semantics |
| `aria-modal="true"` | Modal overlays | Marks as modal |
| `aria-label` | Dialogs, icon-only buttons | Descriptive label for screen readers |
| `aria-hidden` | Hidden content | Toggled on show/hide |
| `aria-expanded` | Toggle buttons | `"true"` / `"false"` |
| `aria-controls` | Toggle buttons | Points to the controlled panel's `id` |
| `aria-live="polite"` | Status regions | Live region for screen reader announcements |
| `aria-atomic="true"` | Status regions | Entire region is announced on change |
| `role="tablist"` / `role="tab"` | Tab bars | Tab navigation semantics |
| `aria-selected` | Tab buttons | `"true"` on active, `"false"` on inactive |
| `tabindex="-1"` | Inactive tabs, programmatic targets | Focusable via JS but not in tab order |
| `tabindex="0"` | Active tab, custom focusable elements | In natural tab order |

### Screen Reader Support

| Feature | Element | Details |
|---|---|---|
| `.sr-only` CSS class | Various | Visually hidden: `position:absolute; width:1px; height:1px; clip:rect(0,0,0,0); overflow:hidden` |
| Status announcements | `aria-live` regions | Dynamic updates announced automatically |

### Rules for New Components

1. Every overlay or dialog must close on `Escape` — add it to the cascade table with the correct priority.
2. Modal dialogs must trap `Tab`/`Shift+Tab` between the first and last focusable elements inside.
3. On dialog open, focus the first focusable element. On close, return focus to the trigger.
4. Use `role="dialog"` and `aria-modal="true"` for modals; always include an `aria-label`.
5. Toggle buttons need `aria-expanded` and `aria-controls` on the trigger.
6. Dynamic status updates must write to an `aria-live="polite" aria-atomic="true"` region.
7. Tab-like navigation must use `role="tablist"/"tab"`, `aria-selected`, and roving `tabindex`.
8. Visually hidden text for screen readers must use `.sr-only`, never `display:none` (which hides from assistive tech too).
9. All interactive elements must be reachable and operable via keyboard alone — no mouse-only interactions.

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
