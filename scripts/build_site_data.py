#!/usr/bin/env python3
"""Build the Dy-VoiceBench demo page data from the local benchmark outputs.

For every model we keep the original per-case JSON (history) plus the original
turn audio (WAV).  Nothing is synthesised here: audio files are copied verbatim
from the run directories and the conversation text is parsed from the recorded
histories so that the web page can replay them.

Missing (model, track) combinations are simply skipped and the page removes the
corresponding controls.
"""
import json, os, re, shutil, sys, hashlib
from pathlib import Path
from glob import glob

OUT = str(Path(__file__).resolve().parents[1])
BENCH = os.environ.get("BENCHMARK_ROOT", str(Path(OUT).parent / "benchmark"))
DATA  = os.path.join(OUT, "data")
AUDIO = os.path.join(OUT, "audio")
RAW   = os.path.join(OUT, "raw_json")

N_CASES = 1          # example conversations kept per (model, track)


# ── model registry ──────────────────────────────────────────────────────────
#  id             display name                     org
MODELS = [
    ("qwen3omni",      "Qwen3-Omni-30B-A3B-Instruct", "Alibaba Cloud"),
    ("stepaudio2",     "Step-Audio 2",                "StepFun"),
    ("gemini",         "Gemini-TTS",                  "Google DeepMind"),
    ("kimiaudio",      "Kimi-Audio",                  "Moonshot AI"),
    ("mimo_audio",     "MiMo-Audio-7B",               "Xiaomi"),
    ("fun_audio_chat", "Fun-Audio-Chat-8B",           "FunAudioLLM"),
    ("gpt4o_audio",    "GPT-4o-Audio",                "OpenAI"),
]

TRACKS = [
    ("hard", "Dynamic World I",   "HARD", "Multi-turn troubleshooting with backend tools"),
    ("coop", "Dynamic World II",  "COOP", "Cooperative two-agent device repair"),
    ("d2",   "Dynamic User State","D2",   "Emotion & state tracking across turns"),
    ("d3",   "Dynamic Knowledge", "D3",   "End-to-end speech dialogue, rule reasoning"),
]

# track -> model -> run directory (relative to BENCH) / d3 result file
SRC = {
    "hard": {
        "gpt4o_audio": "dynamic_bench_agent/outputs_gpt4o_audio",
        "qwen3omni":   "dynamic_bench_agent/outputs_qwen3_omni_unknown",
        "stepaudio2":  "dynamic_bench_agent/output_stepaudio2_unknown",
        "gemini":      "dynamic_bench_agent/outputs_gemini_tts",
        "kimiaudio":   "dynamic_bench_agent/outputs_kimi-audio_unknown",
        "mimo_audio":  "dynamic_bench_agent/outputs_mimo_audio_unknown",
    },
    "coop": {
        "gpt4o_audio": "dynamic_bench_agent_coo/outputs_gpt4o_audio_parallel",
        "qwen3omni":      "dynamic_bench_agent_coo/outputs_qwen3_omni_unknown",
        "stepaudio2":     "dynamic_bench_agent_coo/outputs_stepaudio2_unknown",
        "gemini":         "dynamic_bench_agent_coo/outputs_gemini_tts",
        "kimiaudio":      "dynamic_bench_agent_coo/outputs_kimiaudio_unknown",
        "mimo_audio":     "dynamic_bench_agent_coo/outputs_mimo_audio_unknown",
        "fun_audio_chat": "dynamic_bench_agent_coo/outputs_fun_audio_chat",
    },
    "d2": {
        "qwen3omni":  "D2-Bench/outputs_qwen3omni_full_newd2",
        "stepaudio2": "D2-Bench/outputs_stepaudio2_full_newd2",
        "gemini":     "D2-Bench/outputs_gemini_tts",
    },
    "d3": {
        "qwen3omni":      "D3-Bench/result/qwen3omni_combined.json",
        "stepaudio2":     "D3-Bench/result/stepaudio2_combined.json",
        "gemini":         "D3-Bench/result/gemini_audio_combined.json",
        "kimiaudio":      "D3-Bench/result/kimi_audio_combined.json",
        "mimo_audio":     "D3-Bench/result/mimo_audio_combined.json",
        "gpt4o_audio":    "D3-Bench/result/gpt4o_audio.json",
        "fun_audio_chat": "D3-Bench/result/fun_audio_chat_combined.json",
    },
}

SCENARIO_FILES = {
    "hard": "dynamic_bench_agent/data/Hard/json.json",
    "coop": "dynamic_bench_agent_coo/data/scenarios.json",
    "d2": "Data/D2/descriptions/all_descriptions.json",
}

WAV_RE = re.compile(r"([\w.\-]+\.wav)")


def load_scenarios(rel):
    p = os.path.join(BENCH, rel)
    if not os.path.exists(p):
        return {}
    data = json.load(open(p))
    items = data if isinstance(data, list) else data.values()
    out = {}
    for s in items:
        sid = s.get("test_case_id") or s.get("scenario_id") or s.get("id")
        if sid:
            out[sid] = s
    return out


def opening_text(scenario):
    if not scenario:
        return None
    ts = scenario.get("task_setup") or {}
    return ts.get("ticket") or scenario.get("opening_user_message") or scenario.get("description")


def wav_basename(path):
    return os.path.basename(path) if path else None


def build_agent_messages(hist, scenario):
    """Replay recorded responses and tool steps in their original order."""
    msgs = []
    for r in hist.get("round_logs") or []:
        turn = r.get("turn", 0)
        if turn == 0:
            ticket = opening_text(scenario)
            if not ticket:
                ticket = next((m.get("content") for m in hist.get("human_history", [])
                               if m.get("role") == "assistant"), None)
            audio = wav_basename((r.get("agent") or {}).get("input"))
            if ticket or audio:
                msgs.append(dict(role="user", label="User", text=ticket or "", audio=audio, round=turn))
        for side, role in [("human", "user"), ("agent", "model")]:
            part = r.get(side) or {}
            last_response = None
            def response(value):
                nonlocal last_response
                if not value or value.get("is_tool_call"):
                    return
                text = value.get("text") or ""
                audio = wav_basename(value.get("audio_path"))
                signature = (text, audio)
                if (text or audio) and signature != last_response:
                    msgs.append(dict(role=role, label="User" if role == "user" else "Agent",
                                     text=text, audio=audio, round=turn))
                    last_response = signature
            response(part.get("initial_response"))
            for step in part.get("tool_steps") or []:
                call = step.get("tool_call") or {}
                body = json.dumps({"arguments": call.get("arguments", {}),
                                   "result": step.get("tool_result")}, ensure_ascii=False, indent=2)
                msgs.append(dict(role="tool", who=role, label=call.get("name", "Tool"),
                                 text=body, audio=None, round=turn))
                response(step.get("followup_response"))
            response(part.get("final_response"))
    return msgs


def build_d2_messages(hist):
    msgs = []
    rnd = -1
    for m in hist.get("conversation_log") or []:
        role = "user" if m.get("role") == "human" else "model"
        if role == "user":
            rnd += 1
        msgs.append({"role": role, "label": "User" if role == "user" else "Agent",
                     "text": m.get("text") or "",
                     "audio": wav_basename(m.get("audio_path")),
                     "round": max(rnd, 0)})
    return msgs


def build_d3_messages(task):
    msgs = []
    msgs.append({"role": "user", "label": "User",
                 "text": task.get("user_prompt") or "", "audio": task.get("audio_path1"),
                 "round": 0})
    if task.get("output_turn1") or task.get("output"):
        msgs.append({"role": "model", "label": "Model",
                     "text": task.get("output_turn1") or task["output"], "audio": None, "round": 0})
    if task.get("user_prompt_turn2"):
        msgs.append({"role": "user", "label": "User", "text": task["user_prompt_turn2"],
                     "audio": task.get("audio_path2"), "round": 1})
    if task.get("output_turn2"):
        msgs.append({"role": "model", "label": "Model", "text": task["output_turn2"],
                     "audio": None, "round": 1})
    return msgs


def main():
    for d in (DATA, AUDIO, RAW):
        if os.path.exists(d):
            shutil.rmtree(d)
        os.makedirs(d)

    scenarios_cache = {k: load_scenarios(v) for k, v in SCENARIO_FILES.items()}
    d3_wav_dir = os.path.join(BENCH, "D3-Bench/eval-data/d3-wav")
    copied = {}     # (model, track, case) -> stats

    index = {"models": [{"id": i, "name": n, "org": o} for i, n, o in MODELS],
             "tracks": [{"id": t, "name": nm, "short": sh, "desc": de} for t, nm, sh, de in TRACKS],
             "cases": {}, "stats": {}, "has_audio": {}}

    for track, tname, short, tdesc in TRACKS:
        index["cases"][track] = {}
        for mid, mname, org in MODELS:
            rel = SRC.get(track, {}).get(mid)
            if not rel:
                continue
            case_entries = []
            if track == "d3":
                res = os.path.join(BENCH, rel)
                if not os.path.exists(res):
                    continue
                tasks = json.load(open(res))
                picked = [t for t in tasks if t.get("audio_path1")
                          and (t.get("output_turn1") or t.get("output"))
                          and os.path.exists(os.path.join(d3_wav_dir, t["audio_path1"]))]
                # Include one single-turn and one multi-turn task where available.
                multi = next((t for t in picked if t.get("user_prompt_turn2") and t.get("output_turn2")), None)
                picked = picked[:N_CASES]
                if multi and N_CASES > 1 and multi not in picked:
                    picked[-1] = multi
                for t in picked:
                    msgs = build_d3_messages(t)
                    case_entries.append(copy_case(
                        mid, track, t["task_id"], msgs, t,
                        audio_lookup=lambda bn, _d=d3_wav_dir: os.path.join(_d, bn)))
            else:
                run_root = Path(BENCH) / rel
                history_files = list(run_root.glob("histories/*.json"))
                history_files += list(run_root.glob("shard_*/run_output/histories/*.json"))
                picked = 0
                for f in sorted(history_files, key=lambda path: (path.name, str(path))):
                    audio_dir = str(f.parent.parent / "temp_audio")
                    if picked >= N_CASES:
                        break
                    try:
                        hist = json.load(open(f))
                    except Exception:
                        continue
                    sid = hist.get("scenario_id") or os.path.basename(f)[8:-5]
                    sc = scenarios_cache.get(track, {}).get(sid)
                    msgs = build_d2_messages(hist) if track == "d2" else build_agent_messages(hist, sc)
                    if not msgs:
                        continue
                    have_audio = sum(1 for m in msgs if m.get("audio")
                                     and os.path.exists(os.path.join(audio_dir, m["audio"])))
                    if have_audio < 2:
                        continue
                    case_entries.append(copy_case(
                        mid, track, sid, msgs, hist,
                        audio_lookup=lambda bn, _d=audio_dir: os.path.join(_d, bn),
                        scenario=sc))
                    picked += 1
            if case_entries:
                index["cases"][track][mid] = case_entries
                copied[(mid, track)] = len(case_entries)

    index["models"] = [m for m in index["models"] if any(m["id"] in group for group in index["cases"].values())]
    index["tracks"] = [t for t in index["tracks"] if index["cases"][t["id"]]]
    attach_stats(index, SRC)
    json.dump(index, open(os.path.join(OUT, "data", "index.json"), "w"),
              ensure_ascii=False, indent=2)
    print("cases per (model, track):")
    for (m, t), n in sorted(copied.items()):
        print(f"  {m:15s} {t:5s} {n}")
    print("index written")


def copy_case(mid, track, case_id, msgs, raw_obj, audio_lookup, scenario=None):
    """Copy original WAV bytes and JSON values; write derived conversation JSON."""
    stem = re.sub(r"[^\w\-]", "_", case_id)
    adir_rel = f"audio/{mid}/{track}/{stem}"
    adir = os.path.join(OUT, adir_rel)
    os.makedirs(adir, exist_ok=True)

    out_msgs = []
    used = []
    n = 0
    for m in msgs:
        m = dict(m)
        bn = m.get("audio")
        m["audio_src"] = bn            # original file name, used by verify_site.py
        if bn:
            src = audio_lookup(bn)
            if src and os.path.exists(src):
                dst_name = f"{n:02d}_{m['role']}.wav"
                shutil.copyfile(src, os.path.join(adir, dst_name))
                m["audio"] = f"{adir_rel}/{dst_name}"
                used.append(bn)
            else:
                m["audio"] = None
        else:
            m["audio"] = None
        out_msgs.append(m)
        n += 1

    # Original JSON values preserved; formatting normalized.
    raw_dir = os.path.join(RAW, mid, track)
    os.makedirs(raw_dir, exist_ok=True)
    raw_path = os.path.join(raw_dir, stem + ".json")
    json.dump(raw_obj, open(raw_path, "w"), ensure_ascii=False, indent=2)

    conv = {
        "model": mid, "track": track, "case": case_id,
        "title": (scenario or {}).get("scenario_name") or raw_obj.get("category"),
        "category": ((scenario or {}).get("category") or (scenario or {}).get("domain_display")) if scenario else None,
        "description": (scenario or {}).get("description") or (scenario or {}).get("core_situation"),
        "context": raw_obj.get("long_description") if track == "d3" else None,
        "raw_json": f"raw_json/{mid}/{track}/{stem}.json",
        "messages": out_msgs,
    }
    cdir = os.path.join(DATA, mid, track)
    os.makedirs(cdir, exist_ok=True)
    json.dump(conv, open(os.path.join(cdir, stem + ".json"), "w"),
              ensure_ascii=False, indent=2)

    return {"case": case_id, "title": conv["title"], "category": conv["category"],
            "n_messages": len(out_msgs),
            "n_audio": len(used),
            "path": f"data/{mid}/{track}/{stem}.json"}


def attach_stats(index, src):
    """Attach the recorded overall metrics + per-case outcome to the index."""
    for track, per_model in index["cases"].items():
        for mid, entries in per_model.items():
            rel = src.get(track, {}).get(mid)
            if not rel:
                continue
            if track == "d3":
                summary = Path(BENCH) / "D3-Bench/result/eval-result" / (Path(rel).stem + ".eval.summary.md")
                if summary.exists():
                    content = summary.read_text()
                    keys = {"Total samples": "total_samples", "Overall average rule score": "rule_score",
                            "Overall average sample score": "sample_score", "Turn1 average sample score": "turn1_score",
                            "Turn2 average sample score": "turn2_score"}
                    stats = {}
                    for label, key in keys.items():
                        match = re.search(r"^- " + re.escape(label) + r": ([0-9.]+)$", content, re.M)
                        if match:
                            stats[key] = float(match.group(1))
                    index["stats"].setdefault(track, {})[mid] = stats
                    dest = Path(DATA) / "metrics" / mid / (track + ".md")
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(summary, dest)
                    index.setdefault("metric_sources", {}).setdefault(track, {})[mid] = str(dest.relative_to(OUT))
                continue
            sp = os.path.join(BENCH, rel, "summary.json")
            if not os.path.exists(sp):
                continue
            dest = Path(DATA) / "metrics" / mid / (track + ".json")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(sp, dest)
            index.setdefault("metric_sources", {}).setdefault(track, {})[mid] = str(dest.relative_to(OUT))
            summ = json.load(open(sp))
            ov = summ.get("overall") or {}
            index["stats"].setdefault(track, {})[mid] = {
                k: v for k, v in ov.items() if isinstance(v, (int, float))}
            cases = summ.get("cases") or {}
            for ce in entries:
                ci = cases.get(ce["case"])
                if not ci:
                    continue
                if "success" in ci:
                    ce["success"] = ci["success"]
                ri = ci.get("run_info") or {}
                if ri.get("terminal_status"):
                    ce["terminal_status"] = ri["terminal_status"]


if __name__ == "__main__":
    main()


