#!/usr/bin/env bash
# Setup script for ai-skills + gstack
# Installs both skill sets into ~/.claude/skills/ via symlinks.
# Idempotent — safe to re-run.

set -euo pipefail

SKILLS_DIR="$HOME/.claude/skills"
AI_SKILLS_DIR="$(cd "$(dirname "$0")" && pwd)"
GSTACK_DIR="$HOME/Projects/gstack"
GSTACK_REPO="https://github.com/garrytan/gstack.git"

echo "=== ai-skills setup ==="
echo ""

AGENTS_DIR="$HOME/.agents"          # owned by the ax installer (Necmttn/ax)

# Ensure ~/.claude/skills exists
mkdir -p "$SKILLS_DIR"

# Resolve a skill entry to the repo that actually backs it.
# Handles both install shapes: a dir symlink (ai-skills) and a real dir
# holding a SKILL.md symlink (gstack, ax).
skill_source() {
  local target="$1" resolved=""
  if [ -L "$target" ]; then
    resolved="$(readlink -f "$target" 2>/dev/null || true)"
  elif [ -e "$target/SKILL.md" ]; then
    resolved="$(readlink -f "$target/SKILL.md" 2>/dev/null || true)"
  fi
  case "$resolved" in
    "$AI_SKILLS_DIR"/*) echo "ai-skills" ;;
    "$GSTACK_DIR"|"$GSTACK_DIR"/*) echo "gstack" ;;
    "$AGENTS_DIR"/*)    echo "ax" ;;
    "")                 echo "broken" ;;
    *)                  echo "other" ;;
  esac
}

# --- gstack (runs FIRST: its setup force-relinks every name it owns) ---
echo "1. Setting up gstack..."

if [ -d "$GSTACK_DIR" ]; then
  echo "   gstack repo found at $GSTACK_DIR"
  echo "   Pulling latest..."
  (cd "$GSTACK_DIR" && git pull --ff-only 2>/dev/null || echo "   (pull skipped — may have local changes)")
else
  echo "   Cloning gstack to $GSTACK_DIR..."
  git clone "$GSTACK_REPO" "$GSTACK_DIR"
fi

# Link the gstack repo root — carved skills Read sections via this exact path.
ln -snf "$GSTACK_DIR" "$SKILLS_DIR/gstack"

# gstack's own setup creates the per-skill dirs (real dir + SKILL.md symlink),
# so new upstream skills appear here without manual linking.
if [ -x "$GSTACK_DIR/setup" ]; then
  echo "   Running gstack setup..."
  (cd "$GSTACK_DIR" && ./setup)
fi

echo ""

# --- ai-skills (runs AFTER gstack so our names win on collision) ---
echo "2. Linking ai-skills into $SKILLS_DIR..."

# Directories under ai-skills that are deliberately NOT skills.
NON_SKILL_DIRS=" templates plans scripts "

skipped_loudly=0
for skill_dir in "$AI_SKILLS_DIR"/*/; do
  skill_name="$(basename "$skill_dir")"
  [[ "$skill_name" == .* ]] && continue
  case "$NON_SKILL_DIRS" in *" $skill_name "*) continue ;; esac

  # A directory with no SKILL.md is never a skill, no matter what it contains.
  # Claude Code will NOT reliably register skills nested one level deeper, so a
  # container dir silently publishes some of its children and drops the rest.
  # That is exactly how kalpa/ shipped 6 skills of which 2 registered and one
  # (review) lost its name to gstack. Fail loudly instead of skipping.
  if [ ! -f "$skill_dir/SKILL.md" ]; then
    nested="$(find "$skill_dir" -mindepth 2 -maxdepth 2 -name SKILL.md 2>/dev/null | wc -l | tr -d ' ')"
    if [ "$nested" -gt 0 ]; then
      echo "   !! $skill_name — NOT A SKILL but contains $nested nested SKILL.md file(s)."
      echo "      Nested skills do not register reliably. Flatten them to top-level"
      echo "      dirs with namespaced names (e.g. ${skill_name}-<child>) so each is"
      echo "      registered, then re-run setup."
    else
      echo "   !! $skill_name — no SKILL.md, not linked. Add one or list it in"
      echo "      NON_SKILL_DIRS in setup.sh if it is deliberately not a skill."
    fi
    skipped_loudly=$((skipped_loudly + 1))
    continue
  fi

  # Frontmatter `name` must match the directory — Claude Code resolves by dir.
  fm_name="$(sed -n 's/^name: *//p' "$skill_dir/SKILL.md" | head -1)"
  if [ -n "$fm_name" ] && [ "$fm_name" != "$skill_name" ]; then
    echo "   !! $skill_name — frontmatter name is '$fm_name'. These must match."
    skipped_loudly=$((skipped_loudly + 1))
  fi

  target="$SKILLS_DIR/$skill_name"
  src="$(skill_source "$target")"

  if [ ! -e "$target" ] && [ ! -L "$target" ]; then
    ln -snf "$skill_dir" "$target"
    echo "   $skill_name — linked"
  elif [ "$src" = "ai-skills" ]; then
    :   # already correct
  else
    # Someone else claimed one of our names. Park theirs, take the name back.
    if [ "$src" != "broken" ]; then
      mv "$target" "$SKILLS_DIR/${src}-${skill_name}"
      echo "   $skill_name — RECLAIMED from $src (theirs parked as ${src}-${skill_name})"
    else
      rm -rf "$target"
      echo "   $skill_name — repaired (was a broken link)"
    fi
    ln -snf "$skill_dir" "$target"
  fi
done

[ "$skipped_loudly" -gt 0 ] && echo "   ($skipped_loudly issue(s) above — skills listed there are NOT installed)"

# --- asset shims for reclaimed names -------------------------------------------
# When we take a bare name from gstack, any of ITS files that referenced the name
# self-referentially now resolve into OUR directory and 404.
#
# gstack's review/SKILL.md is inconsistent with itself: 8 asset paths use
# `~/.claude/skills/gstack/review/...` (which still works, via the repo-root link)
# but 2 use `~/.claude/skills/review/...` — checklist.md and greptile-triage.md.
# Our /review invokes that engine, so those two must resolve.
#
# Fix at the install layer, not by editing gstack (upstream-tracking) and not by
# committing absolute symlinks into ai-skills. Convert the reclaimed name into
# gstack's own install shape — a real dir holding a SKILL.md symlink — and add the
# shimmed assets beside it.
shim_reclaimed_assets() {
  local name="$1"; shift
  local ours="$AI_SKILLS_DIR/$name/SKILL.md"
  [ -f "$ours" ] || return 0

  local target="$SKILLS_DIR/$name"
  if [ -L "$target" ]; then rm -f "$target"; fi
  mkdir -p "$target"
  ln -snf "$ours" "$target/SKILL.md"

  local shimmed=0 asset
  for asset in "$@"; do
    if [ -e "$GSTACK_DIR/$name/$asset" ]; then
      ln -snf "$GSTACK_DIR/$name/$asset" "$target/$asset"
      shimmed=$((shimmed + 1))
    fi
  done
  echo "   $name — install shape converted; $shimmed gstack asset(s) shimmed"
}

echo ""
echo "2b. Shimming assets for reclaimed names..."
if [ -f "$AI_SKILLS_DIR/review/SKILL.md" ] && [ -d "$GSTACK_DIR/review" ]; then
  shim_reclaimed_assets review checklist.md greptile-triage.md
else
  echo "   none"
fi

echo ""

# --- prune ai-skills links whose source is gone (renames, flattenings) ---
# A dir symlink into ai-skills that no longer resolves is a leftover from a
# rename. Claude Code may still half-discover through it, so remove it.
echo "2c. Pruning stale ai-skills links..."
pruned=0
for entry in "$SKILLS_DIR"/*; do
  [ -L "$entry" ] || continue
  raw="$(readlink "$entry")"
  case "$raw" in "$AI_SKILLS_DIR"/*) ;; *) continue ;; esac
  [ -f "$raw/SKILL.md" ] && continue
  rm -f "$entry"
  echo "   $(basename "$entry") — pruned (source $raw no longer a skill)"
  pruned=$((pruned + 1))
done
[ "$pruned" -eq 0 ] && echo "   none"

echo ""

# --- collision guard: ax installs several un-namespaced names ---
# ax owns ~/.agents and re-links on every update, so a bare name it shares with
# gstack/ai-skills flips to whichever installer ran last. Namespace ax's copy and
# hand the bare name back to the canonical source.
echo "3. Arbitrating ax name collisions..."

collisions=0
for entry in "$SKILLS_DIR"/*/; do
  name="$(basename "$entry")"
  [ "$(skill_source "$SKILLS_DIR/$name")" = "ax" ] || continue

  canonical=""
  [ -f "$GSTACK_DIR/$name/SKILL.md" ]    && canonical="$GSTACK_DIR/$name"
  [ -f "$AI_SKILLS_DIR/$name/SKILL.md" ] && canonical="$AI_SKILLS_DIR/$name"
  [ -n "$canonical" ] || continue

  collisions=$((collisions + 1))
  mv "$SKILLS_DIR/$name" "$SKILLS_DIR/ax-$name"
  if [ "$canonical" = "$AI_SKILLS_DIR/$name" ]; then
    ln -snf "$canonical" "$SKILLS_DIR/$name"
  else
    mkdir -p "$SKILLS_DIR/$name"
    ln -snf "$canonical/SKILL.md" "$SKILLS_DIR/$name/SKILL.md"
  fi
  echo "   $name — ax copy renamed to ax-$name; $name restored to $(basename "$(dirname "$canonical")")"
done
[ "$collisions" -eq 0 ] && echo "   none"

echo ""
echo "=== Done ==="
echo ""
echo "Installed skills by source:"
for entry in "$SKILLS_DIR"/*/; do
  name="$(basename "$entry")"
  printf "   %-26s %s\n" "$name" "$(skill_source "$SKILLS_DIR/$name")"
done
