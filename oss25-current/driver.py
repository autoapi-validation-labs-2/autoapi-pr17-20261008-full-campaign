import datetime,json,os,pathlib,pwd,re,subprocess,sys,time,urllib.request,urllib.error
ROOT=pathlib.Path(__file__).resolve().parent
inventory=json.loads((ROOT/'inventory.json').read_text())
product=pathlib.Path('/opt/oss25/product')
out=(pathlib.Path(os.environ['GITHUB_WORKSPACE'])/'evidence') if '--preflight' in sys.argv else pathlib.Path('/home/autoapitest/evidence');out.mkdir(exist_ok=True)
operator=os.environ.get('OSS25_OPERATOR_TOKEN','')
modelkey=os.environ.get('OSS25_MODEL_API_KEY','')
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def redact(s):
 for v in [operator,modelkey]:
  if v:s=s.replace(v,'<redacted>')
 return re.sub(r'(?:sk-or-v1-|gho_)[A-Za-z0-9._~-]+','<redacted>',s)
def api(url,key,body=None):
 req=urllib.request.Request(url,headers={'Authorization':'Bearer '+key,'Accept':'application/vnd.github+json','Content-Type':'application/json'},data=None if body is None else json.dumps(body).encode())
 with urllib.request.urlopen(req,timeout=90) as r:return json.load(r)
if '--preflight' in sys.argv:
 record={'started_at':now(),'status':'running','checks':[]}
 try:
  if api('https://api.github.com/user',operator)['login']!='APPNINJAS123':raise RuntimeError('Incorrect GitHub identity')
  for item in inventory:
   data=api('https://api.github.com/repos/'+item['test_repository'],operator)
   if not data['private'] or data.get('fork') or not data.get('permissions',{}).get('push'):raise RuntimeError('Private parentless publication access not proven for '+item['source'])
  record['checks'].append({'github':'25 private parentless copies writable','status':'passed'})
  for model in ['deepseek/deepseek-v4.1-flash','deepseek/deepseek-v4-flash','deepseek/deepseek-v4-flash-0731']:
   response=api('https://openrouter.ai/api/v1/chat/completions',modelkey,{'model':model,'messages':[{'role':'user','content':'Return exactly a JSON object with ok set to true.'}],'max_tokens':128,'reasoning':{'enabled':False},'response_format':{'type':'json_object'},'provider':{'require_parameters':True}})
   answer=json.loads(response['choices'][0]['message']['content'])
   if answer.get('ok') is not True:raise RuntimeError('Live model response did not satisfy JSON preflight')
   record['checks'].append({'model':model,'status':'passed'})
  jev=api('https://openrouter.ai/api/alpha/decisions',modelkey,{'model':'typesafe/jev-1.13','state':'Dependency version changed from 1.0.0 to 1.0.1.','questions':{'consistent':{'type':'noul','instructions':'Is this a patch version update?','criteria':{'true':'patch update','false':'other update'}}}})
  if not isinstance(jev.get('answers',{}).get('consistent',{}).get('noul'),(int,float)):raise RuntimeError('Jev endpoint did not return the required probability')
  record['checks'].append({'model':'typesafe/jev-1.13','endpoint':'decisions','status':'passed'})
  record['status']='passed'
 except Exception as e:record.update(status='blocked',error=redact(str(e)));sys.exitcode=2
 record['finished_at']=now();(out/'infrastructure-preflight.json').write_text(redact(json.dumps(record,indent=2))+'\n')
 print(json.dumps(record));sys.exit(0 if record['status']=='passed' else 2)
item=next(i for i in inventory if i['source']==os.environ['TARGET_SOURCE'])
baseline_mode='--baseline' in sys.argv
limit=os.environ.get('TARGET_CANDIDATE_LIMIT','all') or 'all'
if limit not in ['all','3']:raise RuntimeError('Unapproved candidate limit')
limit_arg='2147483647' if limit=='all' else '3'
user=pwd.getpwnam('autoapitest')
source=pathlib.Path('/home/autoapitest/source')
safeenv={k:v for k,v in os.environ.items() if not any(s in k.upper() for s in ['TOKEN','SECRET','PASSWORD','PRIVATE_KEY','API_KEY','OSS25_','GITHUB_TOKEN'])}
safeenv.update(HOME='/home/autoapitest',RUNNER_TOOL_CACHE='/home/autoapitest/toolcache',TMPDIR='/home/autoapitest/tmp',COREPACK_HOME='/home/autoapitest/corepack',REVIEWER_RUNTIME='openrouter',CI='true',GOMAXPROCS='4',CARGO_BUILD_JOBS='4',MAVEN_OPTS='-Xmx2048m',NODE_OPTIONS='--max-old-space-size=10240',RUSTUP_HOME='/opt/oss25/rustup',CARGO_HOME='/home/autoapitest/.cargo',XDEBUG_MODE='coverage',DOVEL_PRODUCT_SHA='db16e1a8f6372cdd47c018a5ac537b88ad9cda69')
safeenv['PATH']='/opt/oss25/maven/bin:/opt/oss25/beam/elixir/bin:/opt/oss25/beam/otp/bin:/home/autoapitest/.gem/bin:/home/autoapitest/.cargo/bin:/opt/oss25/cargo-bin:'+':'.join(p for p in safeenv['PATH'].split(':') if not p.startswith('/home/runner/'))
safeenv['GEM_HOME']='/home/autoapitest/.gem'
safeenv.update(GITHUB_WORKSPACE=str(source),RUNNER_TEMP='/home/autoapitest/tmp',GITHUB_ENV='/home/autoapitest/github-env',GITHUB_OUTPUT='/home/autoapitest/github-output',GITHUB_PATH='/home/autoapitest/github-path',GITHUB_STEP_SUMMARY='/home/autoapitest/github-summary')
safeenv.update(PLAYWRIGHT_BROWSERS_PATH='/home/autoapitest/.cache/ms-playwright',DISPLAY=':99',XDG_RUNTIME_DIR='/home/autoapitest/.runtime')
safeenv.update(GOPATH='/home/autoapitest/go')
safeenv.update(GH_CONFIG_DIR='/home/autoapitest/.config/gh',XDG_CONFIG_HOME='/home/autoapitest/.config',XDG_CACHE_HOME='/home/autoapitest/.cache',XDG_DATA_HOME='/home/autoapitest/.local/share',XDG_STATE_HOME='/home/autoapitest/.local/state',PNPM_HOME='/home/autoapitest/.local/share/pnpm',npm_config_cache='/home/autoapitest/.npm',GIT_CONFIG_GLOBAL='/home/autoapitest/.gitconfig',GIT_CONFIG_NOSYSTEM='1',UV_CACHE_DIR='/home/autoapitest/.cache/uv',BUN_INSTALL_CACHE_DIR='/home/autoapitest/.bun-cache',GOCACHE='/home/autoapitest/.cache/go-build',GOMODCACHE='/home/autoapitest/go/pkg/mod')
report={'product_sha':'db16e1a8f6372cdd47c018a5ac537b88ad9cda69','source':item['source'],'source_sha':item['source_sha'],'source_tree':item['source_tree'],'test_repository':item['test_repository'],'started_at':now(),'status':'starting','candidate_limit':'all supported manifest declarations within the product 60-minute policy','command_path':'unchanged run-dovel-flow.mjs','upstream_workflows_disabled':True}
report['candidate_limit_mode']=limit
def save():(out/'summary.json').write_text(redact(json.dumps(report,indent=2))+'\n')
def execute(args,env=None,cwd=None):
 if args[0]=='git':args=['git','-c','safe.directory='+str(source),'-c','safe.directory='+str(product),*args[1:]]
 r=subprocess.run(args,env=env,cwd=cwd,capture_output=True,text=True,timeout=1200)
 if r.returncode:raise RuntimeError(redact((r.stderr or r.stdout)[-3000:]))
 return r.stdout.strip()
try:
 expected=execute(['git','-C',str(product),'rev-parse','HEAD'])
 if expected!=report['product_sha']:raise RuntimeError('Product revision mismatch')
 authenv=safeenv.copy()
 import base64
 authenv.update(GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='http.https://github.com/.extraheader',GIT_CONFIG_VALUE_0='AUTHORIZATION: basic '+base64.b64encode(('x-access-token:'+operator).encode()).decode(),GIT_LFS_SKIP_SMUDGE='1',GIT_CONFIG_GLOBAL='/dev/null')
 execute(['git','-c','filter.lfs.required=false','-c','filter.lfs.smudge=','-c','filter.lfs.process=','clone','https://github.com/'+item['test_repository']+'.git',str(source)],env=authenv)
 execute(['git','-C',str(source),'checkout','--detach',item['source_sha']],env=safeenv)
 if execute(['git','-C',str(source),'rev-parse','HEAD^{tree}'])!=item['source_tree']:raise RuntimeError('Target source tree mismatch')
 execute(['chown','-R','autoapitest:autoapitest',str(source),str(out)])
 execute(['chown','-R','root:root',str(product)])
 execute(['chmod','-R','go-w',str(product)])
 for p in ['/home/autoapitest/tmp','/home/autoapitest/toolcache','/home/autoapitest/.runtime']:pathlib.Path(p).mkdir(exist_ok=True);execute(['chown','autoapitest:autoapitest',p])
 for name,value in [('user.name','AutoAPI product testing'),('user.email','148944741+APPNINJAS123@users.noreply.github.com')]:execute(['git','-C',str(source),'config',name,value],env=safeenv)
 subprocess.run(['git','config','--global','--add','safe.directory',str(product)],env=safeenv,cwd='/home/autoapitest',user=user.pw_uid,group=user.pw_gid,extra_groups=[],check=True)
 subprocess.run(['git','submodule','update','--init','--recursive'],cwd=source,env=safeenv,user=user.pw_uid,group=user.pw_gid,extra_groups=[],check=True)
 if item['source']=='elixir-plug/plug':
  probe=subprocess.run(['elixir','--version'],env=safeenv,cwd='/home/autoapitest',user=user.pw_uid,group=user.pw_gid,extra_groups=[],capture_output=True,text=True,check=True)
  if 'Elixir 1.18.4' not in probe.stdout:raise RuntimeError('Pinned Elixir is not active under repository identity: '+probe.stdout[-500:])
  for cmd in [['mix','local.hex','--force'],['mix','local.rebar','--force']]:subprocess.run(cmd,env=safeenv,cwd='/home/autoapitest',user=user.pw_uid,group=user.pw_gid,extra_groups=[],check=True)
 node=execute(['which','node'])
 if execute([node,'--version']) not in ['v22.22.0','v24.20.0','v24.21.0']:raise RuntimeError('Pinned Node runtime is not active: '+execute([node,'--version'])+' at '+node)
 credential_env={**safeenv,'GH_TOKEN':operator}
 credential_probe=subprocess.run(['gh','auth','git-credential','get'],input='protocol=https\nhost=github.com\n\n',capture_output=True,text=True,env=credential_env,cwd='/home/autoapitest',user=user.pw_uid,group=user.pw_gid,extra_groups=[],timeout=30)
 if credential_probe.returncode or ('password='+operator) not in credential_probe.stdout:raise RuntimeError('Unprivileged publication credential helper is not ready: '+redact(credential_probe.stderr[-1000:]))
 report['publication_credential_helper']='passed under repository UID'
 report['runtime_php']=execute(['php','--version']).splitlines()[0]
 command=[node,'--import',str(product/'packages/part-a/node_modules/tsx/dist/loader.mjs'),str(product/'scripts/run-dovel-flow.mjs'),'--secrets-stdin','--repository',str(source),'--owner',item['test_repository'].split('/')[0],'--name',item['test_repository'].split('/')[1],'--max-candidates',limit_arg,'--max-runtime-minutes','60','--open-pr','true','--output-dir',str(out)]
 if baseline_mode:
  command=[node,'--import',str(product/'packages/part-a/node_modules/tsx/dist/loader.mjs'),str(ROOT/'baseline_controller.mjs'),str(product),str(source),str(out)]
  report['command_path']='independent unchanged-source baseline control; no model requests or publication'
 report['node_heap_limit_mib']=10240
 report['host_memtotal_kib']=next(line.split(':',1)[1].strip() for line in pathlib.Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemTotal:'))
 mem_kib=int(report['host_memtotal_kib'].split()[0])
 if mem_kib < 14*1024*1024:raise RuntimeError('Host memory insufficient for10GiB heap; no product flow started')
 report.update(status='running',runtime_node=execute([node,'--version']),kernel_ptrace_scope=pathlib.Path('/proc/sys/kernel/yama/ptrace_scope').read_text().strip(),repository_uid=user.pw_uid,coordinator_uid=os.getuid())
 save()
 p=subprocess.Popen(command,cwd=product,env=safeenv,user=user.pw_uid,group=user.pw_gid,extra_groups=[],stdin=subprocess.DEVNULL if baseline_mode else subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,start_new_session=True)
 if not baseline_mode:p.stdin.write(json.dumps({'OPENROUTER_API_KEY':modelkey,'GH_TOKEN':operator}));p.stdin.close()
 with (out/'flow.log').open('w') as log:
  for line in p.stdout:
   line=redact(line);log.write(line);log.flush();
   if line.startswith(('[1/4]','[2/4]','[3/4]','[4/4]')):print('Product stage '+line.split(']')[0]+']',flush=True)
 code=p.wait()
 report.update(status=('baseline_passed' if code==0 else 'baseline_failed') if baseline_mode else ('completed' if code==0 else 'flow_failed'),exit_code=code)
 report['source_unchanged']=not execute(['git','-C',str(source),'status','--porcelain','--untracked-files=no'],env=safeenv)
except Exception as e:report.update(status='infrastructure_blocked',error=redact(str(e)))
report['finished_at']=now();save();print(json.dumps({k:report.get(k) for k in ['source','product_sha','status','exit_code','source_unchanged']}))
sys.exit(0 if report['status'] in ['completed','baseline_passed'] else 2)
