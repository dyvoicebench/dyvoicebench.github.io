# Dy-VoiceBench demo

This site was rebuilt from `dyvoicebench/dyvoicebench.github.io`, upstream commit
`691837a` (Initial demo website). It retains the original visual design and replaces
the synthetic conversations and random metrics with recorded benchmark data.

## Preview

```bash
cd "/root/nas/yuyunzhen/bench/demo page"
python3 -m http.server 8765 --bind 127.0.0.1
```

Open `http://localhost:8765` on the server, or forward port 8765 over SSH.
The page requires HTTP because it loads JSON with `fetch`.

## Rebuild and verify

```bash
python3 scripts/build_site_data.py
python3 scripts/verify_site.py
python3 scripts/verify_content.py
```

The default source is the sibling `benchmark` directory; set `BENCHMARK_ROOT`
to use another copy. The build replaces the generated `data`, `raw_json`, and
`audio` directories. Source run paths are listed in `scripts/build_site_data.py`.

## Content

- Seven models, four tracks, 22 selected conversations and 232 original audio files.
- One example per available model/track, selected in source order without
  filtering by success.
- GPT-4o's Dynamic World I run has one available conversation and no summary;
  its metric cards are omitted.
- Full-run metrics come from the corresponding `summary.json` or D3
  `*.eval.summary.md`, with source copies rendered in the page’s evaluation details dialog.
- D3 task context is available above its conversation. Responses remain text-only
  where no model recording exists.
- Missing model/track combinations and missing audio buttons are omitted.
- WAV files are copied byte for byte; original JSON field values are preserved
  with normalized formatting. Tool calls include participant, arguments and results.

The demo is a sample browser, not a full export of every experiment or alternate
configuration. Source summaries may cover different sample counts; scores are
shown as recorded and are not combined into a synthetic ranking.

Authors, affiliations, paper links, license claims and synthetic interactive metrics
were removed. At the user’s explicit request, Abstract, Introduction, Method,
Conclusion, References and BibTeX are restored exactly from upstream commit
`691837a`, including their original text and links. The original local folder
is preserved alongside this one as `demo page.backup-20260926-151435`.

## Jupyter file preview

Run `python3 scripts/build_preview.py` to rebuild `preview.html` after updating
the site data or JavaScript. This preview inlines all conversation data and
64 kbps MP3 playback copies, so Jupyter/platform audio authentication and opaque
origins do not block playback. The original WAV assets remain unchanged. The
preview is about 59 MB and may take longer to load the first time.

Task context is rendered as headings, paragraphs and lists. With one example per
model/track, the redundant example dropdown is hidden.

## Readable records

Conversation details and Source results open in accessible in-page dialogs.
JSON fields are rendered as labeled records with expandable sections; evaluation
summaries use metric cards and case tables. Markdown formatting is rendered in
context, conversations, tool results and source records. Original JSON values
remain unchanged. Both dialogs also work in the self-contained Jupyter preview.

## Coverage audit

GPT-4o Dynamic World II includes one example from the four-shard cooperative
run (156 histories), together with its combined run summary. The importer reads
both direct `histories/` and `shard_*/run_output/histories/` layouts.

Available task categories: Qwen3-Omni / Step-Audio 2 / Gemini-TTS: four;
GPT-4o / Kimi-Audio / MiMo-Audio: three; Fun-Audio-Chat: one.
GPT-4o, Kimi, MiMo and Fun-Audio-Chat have no identified Dynamic User State
run in the current data. Fun-Audio-Chat's cooperative history has empty
round logs and empty participant message arrays, so it is not shown.

## Original prose preservation

The six static sections (Abstract, Introduction, Method, Conclusion, References,
BibTeX) must remain identical to upstream commit `691837a`.
`verify_content.py` checks this separately from the real-data case explorer.
