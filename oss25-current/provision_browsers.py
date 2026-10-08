import json,os,pathlib,pwd,subprocess,sys
versions=json.loads(pathlib.Path(__file__).with_name('browser-versions.json').read_text()).get(sys.argv[1],[])
if not versions:sys.exit(0)
engines=['chromium'] if sys.argv[1]=='trpc/trpc' else ['chromium','firefox','webkit']
u=pwd.getpwnam('autoapitest');env={'PATH':os.environ['PATH'],'HOME':u.pw_dir,'CI':'true','LANG':'C.UTF-8','PLAYWRIGHT_BROWSERS_PATH':u.pw_dir+'/.cache/ms-playwright','DISPLAY':':99','TMPDIR':u.pw_dir+'/tmp','XDG_CONFIG_HOME':u.pw_dir+'/.config','XDG_CACHE_HOME':u.pw_dir+'/.cache','XDG_DATA_HOME':u.pw_dir+'/.local/share','XDG_RUNTIME_DIR':u.pw_dir+'/.runtime'}
tmp=pathlib.Path(env['TMPDIR']);tmp.mkdir(exist_ok=True);tmp.chmod(0o700);os.chown(tmp,u.pw_uid,u.pw_gid)
run=pathlib.Path(env['XDG_RUNTIME_DIR']);run.mkdir(exist_ok=True);run.chmod(0o700);os.chown(run,u.pw_uid,u.pw_gid)
subprocess.run(['npx','--yes','playwright@'+versions[-1],'install-deps','chromium','firefox','webkit'],check=True)
subprocess.Popen(['Xvfb',':99','-screen','0','1920x1080x24','-ac'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
for v in versions:
 subprocess.run(['npx','--yes','playwright@'+v,'install','chromium','firefox','webkit'],env=env,cwd=u.pw_dir,user=u.pw_uid,group=u.pw_gid,extra_groups=[],check=True)
# The libraries and binaries are ready; prove all browser engines can launch
# from the same unprivileged identity that runs repository tests.
for v in versions:
 for browser in engines:
  subprocess.run(['npx','--yes','playwright@'+v,'screenshot','--browser',browser,'about:blank',u.pw_dir+'/browser-'+browser+'.png'],env=env,cwd=u.pw_dir,user=u.pw_uid,group=u.pw_gid,extra_groups=[],check=True)
print(json.dumps({'source':sys.argv[1],'browser_versions_installed':versions,'required_engines_smoke_tested':engines}))
