# Task 20 — sudo-impl.sh duplicate user detection false positives

- **Priority**: 4 (Low)
- **Type**: Minor bug
- **Script**: `src/action_implementation/sudo-impl.sh`
- **Repo**: https://github.com/jonathanbrenes/ALAR-jbrenes/tree/main/dev

## Problem

The duplicate user detection regex produces false positives for two cases:

1. **`ALL` keyword**: Lines like `ALL ALL=(ALL) ALL` — the regex captures the first `ALL` as a username. Seen on SLES 16.
2. **`packer` user**: The `packer` user is left over from image build tooling (HashiCorp Packer). This is an image artifact, not an ALAR issue — ALAR should ignore it.

## Affected lines

### sudo-impl.sh (lines 38-48)

```bash
for file in $sudoers_files; do
  while IFS= read -r line; do
    [[ "$line" =~ ^# ]] && continue
    [[ -z "$line" ]] && continue

    if [[ "$line" =~ ^([A-Za-z0-9._%-]+)[[:space:]]+ALL[[:space:]]*=\( ]]; then
      user="${BASH_REMATCH[1]}"

      case "$user" in
        User_Alias|Runas_Alias|Host_Alias|Cmnd_Alias|Defaults)
          continue
          ;;
      esac
```

**Line 43**: The regex `^([A-Za-z0-9._%-]+)[[:space:]]+ALL` matches `ALL ALL=(ALL) ALL` and captures the first `ALL` as a user.

**Lines 45-48**: The `case` filter skips known keywords (`User_Alias`, `Defaults`, etc.) but does NOT filter `ALL`.

## How to fix

Add `ALL` and `packer` to the case filter on line 45:

```bash
      case "$user" in
        User_Alias|Runas_Alias|Host_Alias|Cmnd_Alias|Defaults|ALL|packer)
          continue
          ;;
      esac
```

## Impact

- Without fix: false positive warnings for `ALL` (SLES 16) and `packer` (any image built with Packer)
- With fix: both are correctly skipped
- The `packer` user is an image build artifact — not relevant to ALAR recovery
