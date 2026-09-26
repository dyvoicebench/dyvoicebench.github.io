# Demo page verification

* models: 7
* conversations: 22
* audio files referenced: 232
* problems: 0

| model | track | case | messages | with audio | raw_json vs source |
|---|---|---|---:|---:|---|
| qwen3omni | hard | HARD_001 | 16 | 11 | OK |
| stepaudio2 | hard | HARD_001 | 24 | 22 | OK |
| gemini | hard | HARD_001 | 17 | 13 | OK |
| kimiaudio | hard | HARD_001 | 25 | 17 | OK |
| mimo_audio | hard | HARD_001 | 23 | 22 | OK |
| gpt4o_audio | hard | HARD_001 | 5 | 4 | OK |
| qwen3omni | coop | COOP_001 | 22 | 13 | OK |
| stepaudio2 | coop | COOP_001 | 18 | 11 | OK |
| gemini | coop | COOP_001 | 16 | 9 | OK |
| kimiaudio | coop | COOP_003 | 26 | 16 | OK |
| mimo_audio | coop | COOP_001 | 29 | 26 | OK |
| gpt4o_audio | coop | COOP_001 | 29 | 26 | OK |
| qwen3omni | d2 | D2_001 | 13 | 13 | OK |
| stepaudio2 | d2 | D2_001 | 11 | 11 | OK |
| gemini | d2 | D2_001 | 11 | 11 | OK |
| qwen3omni | d3 | d3-001 | 2 | 1 | OK |
| stepaudio2 | d3 | d3-001 | 2 | 1 | OK |
| gemini | d3 | d3-001 | 2 | 1 | OK |
| kimiaudio | d3 | d3-001 | 2 | 1 | OK |
| mimo_audio | d3 | d3-001 | 2 | 1 | OK |
| fun_audio_chat | d3 | d3-001 | 2 | 1 | OK |
| gpt4o_audio | d3 | d3-001 | 2 | 1 | OK |

## Coverage correction and browser verification

- Added GPT-4o Dynamic World II from the existing 156-case parallel run.
- 22 examples; 232 audio files verified against source recordings.
- Chromium: 22 conversation dialogs, 21 available evaluation dialogs passed.
- No exposed Markdown artifacts in expanded records; no page JavaScript errors.
- Audio playback passed for every model/track combination with external audio requests blocked.
- Mobile page and dialog overflow checks passed.

## Final case text audit

- Checked all 22 cases: 131 user messages, 123 model messages, 45 tool messages.
- Source scan found no replacement characters, invalid control characters, mojibake or identical adjacent duplicate messages.
- Browser-visible wording matches the source after Markdown formatting, including all seven task contexts.
- No exposed asterisk formatting or code fences in conversation text.
- Mobile width 390px: no clipped conversation text.
- One Kimi-Audio message has audio but no source transcript; its empty bubble was removed and the recording retained.
- No source transcript was invented or rewritten. Browser JavaScript errors: 0.

## Original static prose restored

- Abstract, Introduction, Method, Conclusion, References and BibTeX restored from initial upstream commit `691837a`.
- Section HTML matches the original after line-ending normalization.
- Browser-rendered text and link destinations match the original for all six sections.
- Case explorer, evaluation details dialog and audio playback smoke checks passed.
- Browser JavaScript errors: 0.
