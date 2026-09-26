"""Build a Jupyter preview with inline data and self-contained playback audio.

Preview-only MP3 copies avoid authenticated audio subrequests from Jupyter's
opaque HTML origin. Original WAV files in audio/ are never modified.
"""
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
registry = json.loads((root / 'data/index.json').read_text())
files = {'data/index.json': registry}
audio_paths = set()
for models in registry['cases'].values():
    for entries in models.values():
        for entry in entries:
            conversation = json.loads((root / entry['path']).read_text())
            files[entry['path']] = conversation
            files[conversation['raw_json']] = json.loads((root / conversation['raw_json']).read_text())
            audio_paths.update(m['audio'] for m in conversation['messages'] if m.get('audio'))

for models in registry.get('metric_sources', {}).values():
    for path in models.values():
        content = (root / path).read_text()
        files[path] = content if path.endswith('.md') else json.loads(content)

cache = Path(tempfile.gettempdir()) / 'dyvoicebench-preview-audio'
cache.mkdir(exist_ok=True)
by_hash = {}
path_hash = {}
for path in sorted(audio_paths):
    digest = hashlib.sha256((root / path).read_bytes()).hexdigest()
    path_hash[path] = digest
    by_hash[digest] = path

def encode(item):
    digest, path = item
    target = cache / (digest + '.mp3')
    if not target.exists():
        subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-y', '-i', str(root / path),
                        '-map_metadata', '-1', '-ac', '1', '-ar', '24000', '-c:a', 'libmp3lame',
                        '-b:a', '64k', str(target)], check=True, capture_output=True)
    return digest, 'data:audio/mpeg;base64,' + base64.b64encode(target.read_bytes()).decode()

with ThreadPoolExecutor(max_workers=4) as pool:
    encoded = dict(pool.map(encode, by_hash.items()))

def safe_json(value):
    return json.dumps(value, ensure_ascii=False).replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')

app = (root / 'app.js').read_text().replace("'_blank'", "'_self'").replace('target="_blank"', 'target="_self"')
script = ('const previewFiles = ' + safe_json(files) + ';\n'
          'const audioData = ' + safe_json(encoded) + ';\n'
          'window.previewAudio = Object.fromEntries(Object.entries(' + safe_json(path_hash) + ').map(([path, hash]) => [path, audioData[hash]]));\n'
          'const fetch = async path => ({ok: Object.hasOwn(previewFiles, path), json: async () => previewFiles[path], text: async () => previewFiles[path]});\n' + app)
html = (root / 'index.html').read_text().replace('target="_blank"', 'target="_self"')
html = html.replace('<script src="app.js" defer></script>', '<script>\n' + script + '\n</script>')
(root / 'preview.html').write_text(html)
print(f'Built preview: {sum(len(entries) for group in registry['cases'].values() for entries in group.values())} conversations, {len(audio_paths)} audio references, {len(encoded)} unique recordings; {len(html.encode())/1e6:.1f} MB')
