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

for skill_dir in "$AI_SKILLS_DIR"/*/; do
  skill_name="$(basename "$skill_dir")"
  [[ "$skill_name" == .* ]] && continue
  [ -f "$skill_dir/SKILL.md" ] || continue

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
