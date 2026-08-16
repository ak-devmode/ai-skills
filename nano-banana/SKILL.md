---
name: nano-banana
version: 1.0.0
description: |
  Generate or edit images from a prompt using Google's Gemini image models
  ("Nano Banana" — gemini-2.5-flash-image, gemini-3.x-flash-image,
  gemini-3-pro-image). Produces real image files on disk that can then be
  uploaded, embedded, or read back for inspection.

  Use when asked to "generate an image", "make a picture/photo/portrait/icon",
  "create demo assets", "I need a placeholder photo", "edit this image", or when
  a task is blocked because no image exists — seeding demo data with avatars,
  mocking up a visual, producing a diagram background, making synthetic faces
  for screenshots.

  Do NOT use for charts or data visualisation (use /dataviz), for architecture
  or flow diagrams (use /diagram — ASCII is the house style), or for anything
  depicting a real, identifiable person.
allowed-tools:
  - Bash
  - Read
  - Write
---

# nano-banana — image generation via Gemini

## 1. Setup (one-time)

1.1 API key lives at `~/.config/gemini/api_key`, mode `600`, **outside every git
repo**. `GEMINI_API_KEY` in the environment overrides it if set.

> This repo is public. Never write the key into SKILL.md, a script, a commit, or
> a command line — reference the path only.

1.2 Create a key at <https://aistudio.google.com/apikey>. **Attach it to an
existing GCP project with billing enabled.** On the free tier Google may use
prompts and outputs to improve their products; on paid terms they do not. That
distinction matters the moment a prompt contains client, patient, or
proprietary content — which happens sooner than expected.

## 2. Usage

```
python3 ~/.claude/skills/nano-banana/scripts/nb-image.py "PROMPT" -o out.jpg
```

| Flag | Meaning |
|---|---|
| `-o, --out` | output path; `.jpg` or `.png` (default `out.png`) |
| `-m, --model` | default `gemini-3.1-flash-image` |
| `--ref PATH` | reference image to edit or stay consistent with; repeatable |
| `--list-models` | print image-capable models available to this key |
| `-q, --quiet` | suppress the per-file summary line |

Multi-image responses are written as `out-1.jpg`, `out-2.jpg`, …

**Always `Read` the generated file before using it.** The model follows prompts
well but not perfectly, and a wrong face or a stray artefact is obvious to look
at and invisible in a byte count.

## 3. Prompting

Be explicit about subject, framing, lighting and background. Vague prompts give
inconsistent framing that is painful to crop.

```
"Photorealistic passport-style headshot of an Indonesian woman, age 34,
 warm neutral expression, looking directly at camera, plain light grey studio
 backdrop, soft even lighting, sharp focus, head and shoulders.
 No text, no watermark, no border."
```

- State demographics explicitly when they matter. Generic prompts drift toward
  Western subjects, which reads as careless in a localised product.
- `"No text, no watermark, no border"` is worth including by default.
- For a **consistent character** across several images, generate once, then pass
  that file with `--ref` on subsequent calls. This is the main advantage over a
  one-shot generator.

## 4. Gotchas

- **Latency is ~40s per image.** A foreground batch of four exceeds a two-minute
  Bash timeout. Generate sequentially, or background the batch.
- **Parallel calls fail silently.** Four concurrent invocations returned exit 0
  while two produced no file. Verify by checking file size or mtime changed —
  never trust the exit code alone.
- **Aspect ratio is not fixed.** Observed 1408×768 and 848×1264 from identical
  prompt shapes. Crop to square yourself if you need an avatar; anchor the crop
  near the top on portrait outputs so the head is not cut off.
- **HTTP 429 usually means billing, not rate limiting.** *"Your prepayment
  credits are depleted"* → top up at <https://ai.studio/projects>. The script
  surfaces this hint.
- **Size the output for its use.** Generations land at 500–700 KB. If the target
  renders them as small avatars, downscale before uploading — many apps serve
  the original at full size to every list row.

## 5. Not for

- Charts, plots, dashboards → `/dataviz`
- Architecture, flow, sequence diagrams → `/diagram` (ASCII is the house style)
- Anything portraying a real, identifiable person, or synthetic imagery
  presented as a real record.
