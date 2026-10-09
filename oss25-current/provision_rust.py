import json,os,pathlib,subprocess,sys
channels=json.loads(pathlib.Path(__file__).with_name('rust-toolchains.json').read_text()).get(sys.argv[1],[])
for c in channels:
 subprocess.run(['/opt/oss25/cargo-bin/rustup','toolchain','install',c,'--profile','minimal','--no-self-update'],env={**os.environ,'RUSTUP_HOME':'/opt/oss25/rustup'},check=True)
if sys.argv[1] in ['BurntSushi/ripgrep','sharkdp/bat']:
 subprocess.run(['/opt/oss25/cargo-bin/rustup','default','1.96.0'],env={**os.environ,'RUSTUP_HOME':'/opt/oss25/rustup'},check=True)
subprocess.run(['chmod','-R','a+rX','/opt/oss25/rustup'],check=True)
print(json.dumps({'source':sys.argv[1],'declared_rust_toolchains_prepared':channels}))
