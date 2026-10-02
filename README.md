# SafePlate — an offline allergy-aware meal planner

Built for the [DEV Hacktoberfest Weekend Challenge 2026: Build for a Friend](https://dev.to/challenges/hacktoberfest-weekend-2026-10-01).

My roommate is allergic to peanuts and shrimp. Dorm wifi is flaky, and neither
of us wants health data sitting on somebody else's server. So SafePlate runs
**100% on the laptop**: [Gemma 3 4B](https://deepmind.google/technologies/gemma/)
(open weights, `ggml-org` Q4_K_M quant) executed locally by
[llama.cpp](https://github.com/ggml-org/llama.cpp) `llama-server`,
a tiny web UI,
zero accounts, zero tracking, zero cost.

## Run it (Windows / Mac / Linux)

1. Download + extract the `win-cpu` build of
   [llama.cpp releases](https://github.com/ggml-org/llama.cpp/releases)
2. Download `gemma-3-4b-it-Q4_K_M.gguf` from
   [ggml-org/gemma-3-4b-it-GGUF](https://huggingface.co/ggml-org/gemma-3-4b-it-GGUF)
3. `llama-server -m gemma-3-4b-it-Q4_K_M.gguf --port 8080`
   (or any port — set `SAFEPLATE_LLAMA`)
4. `python server.py` → open http://localhost:8765/
5. CLI: `python safeplate.py peanuts,shrimp 2`

## How it works

- The UI collects allergies + servings and builds a strict prompt: the model
  MUST NEVER suggest dishes containing the listed allergens.
- Gemma returns a 7-day dinner plan + shopping list as JSON, rendered locally.
- Nothing leaves the machine — verify with your firewall or airplane mode.

## Why open innovation matters here

- **Privacy**: allergy/health data never touches a server we don't control.
- **Offline**: works in a dorm with dead wifi; a closed API would simply fail.
- **Cost**: $0 to run, forever — no per-token bill for a student.
- **Control**: swap `gemma3:1b` for any open-weight model without rewriting the app.

## Challenge checklist

- New repo, built Oct 2–5 2026 during the challenge window.
- Prize lanes entered: Best Use of Gemma.
- Handover: gave it to my roommate on Oct 2. His words:
  "Khá hữu ích, bình thường tao toàn phải tự nghĩ đau cả đầu."
  ("Pretty useful — normally I have to come up with meals myself, headache.")
  His ask: richer menus for different people with balanced nutrition → v2
  audience selector (student / gym / senior) + per-day nutrition note.
