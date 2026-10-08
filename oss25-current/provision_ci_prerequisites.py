import json,pathlib,re,subprocess,sys
# Exact commands from the pinned repositories' Linux CI. No wildcard or shell permission.
commands={
 'expressjs/express':['-y install lcov'],
 'nodejs/undici':['install ninja-build','install -y wasi-libc binaryen'],
 'BurntSushi/ripgrep':['update','install g++ --yes'],
 'sinatra/sinatra':['update','install --yes pandoc nodejs pkg-config libxml2-dev libxslt-dev libyaml-dev'],
 'sharkdp/bat':['-y update','-y install gcc-arm-linux-gnueabihf','-y install gcc-aarch64-linux-gnu'],
}.get(sys.argv[1],[])
if not commands:sys.exit(0)
for args in commands:
 if not re.fullmatch(r'[A-Za-z0-9 +.-]+',args):raise RuntimeError('Invalid exact prerequisite command')
 subprocess.run(['/usr/bin/apt-get',*args.split()],check=True)
p=pathlib.Path('/etc/sudoers.d/autoapi-ci-prerequisites');p.write_text(''.join('autoapitest ALL=(root) NOPASSWD: /usr/bin/apt-get '+args+'\n' for args in commands));p.chmod(0o440)
subprocess.run(['visudo','-cf',str(p)],check=True)
print(json.dumps({'source':sys.argv[1],'exact_prerequisites_prepared':commands,'arbitrary_sudo_access':False}))
