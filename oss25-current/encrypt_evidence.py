import hashlib,hmac,json,os,pathlib,subprocess,tarfile,tempfile
workspace=pathlib.Path(os.environ['GITHUB_WORKSPACE']);key=os.environ.get('OSS25_MODEL_API_KEY','')
if not key:raise SystemExit('No report-encryption credential; plaintext will not be uploaded.')
evidence=workspace/'evidence';evidence.mkdir(exist_ok=True)
for path in [workspace/'product/product-build.log',pathlib.Path('/opt/oss25/product/product-build.log')]:
 if path.is_file():
  import shutil;shutil.copyfile(path,evidence/'product-build.log');break
out=workspace/'encrypted-evidence';out.mkdir(exist_ok=True)
passphrase=hashlib.sha256(b'oss25-v1-encryption\0'+key.encode()).hexdigest()
with tempfile.TemporaryDirectory(prefix='oss25-encrypt-') as temp:
 plain=pathlib.Path(temp)/'evidence.tar.gz'
 with tarfile.open(plain,'w:gz') as archive:
  for path in sorted(evidence.iterdir()):
   # Candidate checkouts and their build caches are disposable; durable receipts,
   # complete captured outputs, physical patches and progress remain included.
   if path.is_dir() and path.name.startswith('candidate-') and path.name != 'candidate-receipts':continue
   archive.add(path,arcname=path.name,recursive=True)
 cipher=out/'evidence.enc'
 proc=subprocess.run(['openssl','enc','-aes-256-cbc','-salt','-pbkdf2','-iter','200000','-md','sha256','-in',str(plain),'-out',str(cipher),'-pass','stdin'],input=passphrase+'\n',text=True,capture_output=True)
 if proc.returncode:raise SystemExit('Report encryption failed; plaintext will not be uploaded.')
 payload=cipher.read_bytes();metadata={'version':1,'algorithm':'AES-256-CBC/PBKDF2-SHA256-200000/HMAC-SHA256','product_sha':'03a297f00411464e35ff6f3ead572fc38360a9bf','run':os.environ['GITHUB_RUN_ID'],'source':os.environ.get('TARGET_SOURCE','preflight'),'ciphertext_sha256':hashlib.sha256(payload).hexdigest()}
 canonical=json.dumps(metadata,sort_keys=True,separators=(',',':')).encode();authkey=hmac.new(key.encode(),b'oss25-evidence-v1-auth',hashlib.sha256).digest();metadata['hmac_sha256']=hmac.new(authkey,canonical+b'\0'+payload,hashlib.sha256).hexdigest();(out/'manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
print('Authenticated encrypted report prepared; plaintext reports will not be published.')
