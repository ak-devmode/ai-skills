# ai-skills

Custom Claude Code skills for the PMG/Kalpa team. Includes our own skills plus automated setup for [gstack](https://github.com/garrytan/gstack) (Garry Tan's skill suite).

## 1. What's included

### 1.1 Our skills (this repo)

| Skill | Description |
|-------|-------------|
| `/scope` | Task scoping and multi-skill orchestration |
| `/scope-review` | Review a team scope/PRD/plan at the right altitude, in Alex's voice |
| `/plan` | Single-session execution from a plan file |
| `/prd` | Product Requirements Document generator |
| `/markdown-style` | Structured markdown document creation |
| `/md2docx` | Convert markdown to brand-styled `.docx` (Word/Google Docs); `--bilingual` ID/EN contract mode |
| `/repo-cleanup` | Branch hygiene: classify, prune merged, flag in-flight (current repo) |
| `/repo-cleanup-all` | Alias for `/repo-cleanup --all` — fleet sweep across a GitHub org/user |
| `/kalpa/*` | Kalpa-specific skills (coding standards, API gen, migrations, FHIR) |

### 1.2 gstack skills (installed automatically)

gstack adds 25+ skills including `/review`, `/ship`, `/qa`, `/browse`, `/investigate`, `/retro`, and more. See the [gstack README](https://github.com/garrytan/gstack) for the full list.

## 2. Setup

### 2.1 Quick start

```bash
# Clone this repo
git clone https://github.com/ak-devmode/ai-skills.git ~/Projects/ai-skills

# Run setup (installs both ai-skills + gstack)
cd ~/Projects/ai-skills && ./setup.sh
```

The setup script:
- Symlinks each skill folder from this repo into `~/.claude/skills/`
- Clones [garrytan/gstack](https://github.com/garrytan/gstack) to `~/Projects/gstack` (or pulls latest if already cloned)
- Symlinks gstack into `~/.claude/skills/gstack`
- Runs gstack's own setup script

### 2.2 Manual setup

If you prefer to do it by hand:

```bash
# 1. Clone both repos
git clone https://github.com/ak-devmode/ai-skills.git ~/Projects/ai-skills
git clone https://github.com/garrytan/gstack.git ~/Projects/gstack

# 2. Create skills directory
mkdir -p ~/.claude/skills

# 3. Symlink ai-skills
ln -s ~/Projects/ai-skills/scope ~/.claude/skills/scope
ln -s ~/Projects/ai-skills/plan ~/.claude/skills/plan
ln -s ~/Projects/ai-skills/prd ~/.claude/skills/prd
ln -s ~/Projects/ai-skills/markdown-style ~/.claude/skills/markdown-style
ln -s ~/Projects/ai-skills/kalpa ~/.claude/skills/kalpa

# 4. Symlink gstack
ln -s ~/Projects/gstack ~/.claude/skills/gstack

# 5. Run gstack setup
cd ~/Projects/gstack && ./setup
```

## 3. Updating

```bash
# Update ai-skills
cd ~/Projects/ai-skills && git pull

# Update gstack
cd ~/Projects/gstack && git pull
```

Or just re-run `./setup.sh` — it pulls gstack automatically.

## 4. Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed
- [Git](https://git-scm.com/)
- [Bun](https://bun.sh/) v1.0+ (required by gstack)
