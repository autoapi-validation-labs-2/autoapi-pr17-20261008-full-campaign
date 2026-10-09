#!/usr/bin/python3
# Only permit Playwright's already-provisioned apt dependencies. Never run its shell.
import os,re,shlex,subprocess,sys
if os.getuid()!=0 or len(sys.argv)!=2:raise SystemExit('Invalid dependency setup invocation')
parts=sys.argv[1].split('&&')
if len(parts)!=2 or shlex.split(parts[0])!=['apt-get','update']:raise SystemExit('Only the prepared Playwright dependency operation is allowed')
args=shlex.split(parts[1])
if args[:2]!=['apt-get','install']:raise SystemExit('Only apt-get install is allowed')
packages=[]
for arg in args[2:]:
 if arg in ['-y','--no-install-recommends']:continue
 if not re.fullmatch(r'[a-z0-9][a-z0-9+.-]*',arg):raise SystemExit('Unexpected package argument')
 probe=subprocess.run(['/usr/bin/dpkg-query','-W','-f=${db:Status-Status}',arg],capture_output=True,text=True)
 if probe.returncode or probe.stdout!='installed':raise SystemExit('Dependency not pre-provisioned: '+arg)
 packages.append(arg)
if not packages:raise SystemExit('No prepared dependencies declared')
subprocess.run(['/usr/bin/apt-get','update'],check=True,env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','DEBIAN_FRONTEND':'noninteractive'})
subprocess.run(['/usr/bin/apt-get','install','-y','--no-install-recommends',*packages],check=True,env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','DEBIAN_FRONTEND':'noninteractive'})
