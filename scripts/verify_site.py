#!/usr/bin/env python3
"""Independent check of the demo page against the original benchmark runs.

For every recorded conversation it re-reads the ORIGINAL run directory and
compares, file by file, what the web page is about to serve:

  * raw_json/<...>.json      vs  the original history / result JSON (parsed equality)
  * audio/<...>/NN_role.wav  vs  the original WAV              (sha256)
  * data/<...>.json          vs  every referenced file existing + every
                                 message audio byte-identical to the source

Writes a human-reviewable report to VERIFY.md and exits non-zero on any drift.
"""
import hashlib, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_site_data as B   # reuse the same source mapping

ROOT = B.OUT
INDEX = json.load(open(os.path.join(ROOT, "data", "index.json")))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def source_history(track, mid, case):
    rel = B.SRC[track][mid]
    if track == "d3":
        return os.path.join(B.BENCH, rel)
    direct = os.path.join(B.BENCH, rel, "histories", f"history_{case}.json")
    if os.path.exists(direct):
        return direct
    from glob import glob
    matches = glob(os.path.join(B.BENCH, rel, "shard_*", "run_output", "histories", f"history_{case}.json"))
    if len(matches) != 1:
        raise ValueError(f"Expected one source history for {mid}/{track}/{case}, got {len(matches)}")
    return matches[0]


def source_audio(track, mid, case):
    rel = B.SRC[track][mid]
    if track == "d3":
        return os.path.join(B.BENCH, "D3-Bench/eval-data/d3-wav")
    return os.path.join(os.path.dirname(os.path.dirname(source_history(track, mid, case))), "temp_audio")


rows, problems, checked_wav = [], [], 0
for track, per_model in INDEX["cases"].items():
    for mid, entries in per_model.items():
        for e in entries:
            case = e["case"]
            conv = json.load(open(os.path.join(ROOT, e["path"])))
            rawp = os.path.join(ROOT, conv["raw_json"])
            raw = json.load(open(rawp))

            # 1. raw json comparable to the original run?
            src = source_history(track, mid, case)
            if track == "d3":
                tasks = json.load(open(src))
                match = any(t.get("task_id") == case and t == raw for t in tasks)
                src_desc = f"{os.path.basename(src)}[{case}]"
            else:
                match = json.load(open(src)) == raw
                src_desc = os.path.relpath(src, B.BENCH)
            if not match:
                problems.append(f"raw_json mismatch: {mid}/{track}/{case}")

            # 2. audio byte-identical to the original recordings?
            adir = source_audio(track, mid, case)
            wav_ok = wav_bad = 0
            for m in conv["messages"]:
                if not m["audio"]:
                    continue
                local = os.path.join(ROOT, m["audio"])
                if not os.path.exists(local):
                    problems.append(f"missing audio: {m['audio']}")
                    continue
                orig = os.path.join(adir, m.get("audio_src") or "")
                if not m.get("audio_src") or not os.path.exists(orig):
                    problems.append(f"original audio not found: {mid}/{track}/{case} {m.get('audio_src')}")
                    continue
                if sha(local) != sha(orig):
                    problems.append(f"audio mismatch: {m['audio']} != {m['audio_src']}")
                else:
                    wav_ok += 1
                checked_wav += 1
            rows.append((mid, track, case, len(conv["messages"]),
                         sum(1 for m in conv["messages"] if m["audio"]),
                         os.path.exists(rawp), match))

# ---- write report -------------------------------------------------------
lines = ["# Demo page verification", "",
         f"* models: {len(INDEX['models'])}",
         f"* conversations: {len(rows)}",
         f"* audio files referenced: {checked_wav}",
         f"* problems: {len(problems)}", "",
         "| model | track | case | messages | with audio | raw_json vs source |",
         "|---|---|---|---:|---:|---|"]
for mid, track, case, n, na, has_raw, match in rows:
    lines.append(f"| {mid} | {track} | {case} | {n} | {na} | {'OK' if match else 'MISMATCH'} |")
if problems:
    lines += ["", "## Problems"] + [f"* {p}" for p in problems]
open(os.path.join(ROOT, "VERIFY.md"), "w").write("\n".join(lines) + "\n")

print("\n".join(lines[:8]))
print(f"\nreport written to {os.path.join(ROOT, 'VERIFY.md')}")
sys.exit(1 if problems else 0)
