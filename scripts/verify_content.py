import json, pathlib, re, sys
root=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'scripts'));import build_site_data as B
bench=pathlib.Path(B.BENCH)
index=json.loads((root/'data/index.json').read_text());checked=0
for track,groups in index['cases'].items():
 for model,entries in groups.items():
  for entry in entries:
   c=json.loads((root/entry['path']).read_text());raw=json.loads((root/c['raw_json']).read_text())
   def strings(obj):
    if isinstance(obj,str): yield obj
    elif isinstance(obj,dict):
     for v in obj.values(): yield from strings(v)
    elif isinstance(obj,list):
     for v in obj: yield from strings(v)
   texts=set(strings(raw))
   scenarios=B.load_scenarios(B.SCENARIO_FILES[track]) if track in B.SCENARIO_FILES else {}
   sc=scenarios.get(entry['case']);opening=B.opening_text(sc)
   for m in c['messages']:
    if m['role']!='tool' and m['text']:
     assert m['text'] in texts or m['text']==opening,(model,track,entry['case'],'text drift')
    if m.get('audio_src'):
     source=(bench/'D3-Bench/eval-data/d3-wav' if track=='d3' else bench/B.SRC[track][model]/'temp_audio')/m['audio_src']
     if track != 'd3' and not source.is_file():
      matches=list((bench/B.SRC[track][model]).glob('shard_*/run_output/temp_audio/'+m['audio_src']))
      assert len(matches)<=1, ('ambiguous source audio',m['audio_src'])
      if matches: source=matches[0]
     assert bool(m['audio'])==source.is_file(),('audio omitted',m['audio_src'])
   assert entry['n_audio']==sum(bool(m['audio']) for m in c['messages'])
   checked+=1
for track,models in index['metric_sources'].items():
 for model,path in models.items():
  rel=B.SRC[track][model]
  src=bench/'D3-Bench/result/eval-result'/(pathlib.Path(rel).stem+'.eval.summary.md') if track=='d3' else bench/rel/'summary.json'
  assert (root/path).read_bytes()==src.read_bytes(),('metric source drift',path)
  if track!='d3':
   raw=json.loads(src.read_text())['overall']
   assert all(raw[k]==v for k,v in index['stats'][track][model].items())
html=(root/'index.html').read_text(); js=(root/'app.js').read_text()
assert not any(x in js for x in ['Math.random','placeholderConversation'])
# The user requires the original static prose, including its original references.
import subprocess
original=subprocess.check_output(['git','-C',str(root),'show','691837a:index.html']).decode().replace('\r\n','\n')
for section in ['abstract','introduction','method','conclusion','references','bibtex']:
 pattern=r'<section\b[^>]*\bid="'+section+r'"[^>]*>.*?</section>'
 assert re.search(pattern,html,re.S).group()==re.search(pattern,original,re.S).group(),('original prose changed',section)
for anchor in re.findall(r'href="#([^"]+)"',html): assert f'id="{anchor}"' in html
print(f'PASS: {checked} conversations have source-grounded text and every available recording; metric sources match; original static sections unchanged; no synthetic application data or broken anchors.')
