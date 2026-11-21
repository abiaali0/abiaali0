let runtime;
async function setup(){if(!runtime)runtime=(async()=>{importScripts('https://cdn.jsdelivr.net/pyodide/v0.28.1/full/pyodide.js');const py=await loadPyodide();const response=await fetch('demo-sources.json');if(!response.ok)throw Error('Project sources unavailable');const src=await response.json();py.FS.mkdirTree('/home/pyodide/app');py.FS.mkdirTree('/home/pyodide/static_analyzer');for(const [path,value]of Object.entries({'app/__init__.py':'','app/text_utils.py':src.text_utils,'app/matcher.py':src.matcher,'agent.py':src.agent,'static_analyzer/__init__.py':'','static_analyzer/models.py':src.models,'static_analyzer/rules.py':src.rules}))py.FS.writeFile('/home/pyodide/'+path,value);await py.runPythonAsync('import sys\nsys.path.insert(0,"/home/pyodide")');return py;})();return runtime;}
self.onmessage=async({data})=>{try{self.postMessage({status:'Loading Python runtime and repository logic…'});const py=await setup();py.globals.set('payload_json',JSON.stringify(data));const result=await py.runPythonAsync(`
import json, ast, pathlib, tempfile
from app.matcher import calculate_match
from static_analyzer.rules import RuleVisitor
from agent import extract_keywords, discover_context_files, create_implementation_plan, create_pull_request_summary
p=json.loads(payload_json)
if p['kind']=='match':
 result=calculate_match(p['resume'],p['job'])
elif p['kind']=='analyzer':
 tree=ast.parse(p['code'])
 visitor=RuleVisitor('sample.py')
 visitor.visit(tree)
 result={'findings':[f.to_dict() for f in visitor.finalize()], 'method':'Original repository AST rules; submitted code is parsed, never executed.'}
elif p['kind']=='agent':
 keywords=extract_keywords(p['title'],p['body'])
 with tempfile.TemporaryDirectory() as directory:
  for name in p['files'].splitlines():
   name=name.strip()
   if not name: continue
   relative=pathlib.PurePosixPath(name)
   if relative.is_absolute() or '..' in relative.parts: raise ValueError('Use relative paths without ..')
   target=pathlib.Path(directory)/relative
   target.parent.mkdir(parents=True,exist_ok=True)
   target.touch()
  context=discover_context_files(directory,keywords)
 plan=create_implementation_plan(p['title'],keywords,context)
 result={'keywords':keywords,'context_files':context,'plan':plan,'pull_request_summary':create_pull_request_summary(p['title'],plan,context)}
json.dumps(result)
`);self.postMessage({result:JSON.parse(result)});}catch(e){self.postMessage({error:String(e.message||e)});}};
