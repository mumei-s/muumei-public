"""Accept only a checksum-pinned public distribution, never private source or a live OWNER."""
import base64, hashlib, io, json, os, pathlib, re, stat, urllib.request, zipfile
revision=os.environ['SOURCE_REVISION'];expected=os.environ['DISTRIBUTION_SHA256'];root=pathlib.Path('docs')
assert re.fullmatch('[0-9a-f]{40}',revision) and re.fullmatch('[0-9a-f]{64}',expected)
# Existing verified files make deployment replayable after the temporary transfer URL expires.
manifest=pathlib.Path('.github/releases/compact-manifest.json')
if manifest.exists():
 saved=json.loads(manifest.read_text())
 if saved.get('sourceRevision')==revision and saved.get('archiveSha256')==expected and all((root/f['path']).is_file() and hashlib.sha256((root/f['path']).read_bytes()).hexdigest()==f['sha256'] for f in saved['files']):
  print('The exact verified distribution is already stored on public main.');raise SystemExit(0)
url=os.environ['PUBLIC_DISTRIBUTION_URL']
assert url.startswith('https://') and '.oaiusercontent.com/' in url
with urllib.request.urlopen(url,timeout=90) as response:packed=response.read(80*1024*1024+1)
assert len(packed)<=80*1024*1024 and hashlib.sha256(packed).hexdigest()==expected,'Public distribution checksum mismatch'
allowed={'.html','.js','.css','.json','.webmanifest','.svg','.png','.webp','.jpg','.jpeg','.ico','.txt','.woff','.woff2'}
files={}
with zipfile.ZipFile(io.BytesIO(packed)) as archive:
 for item in archive.infolist():
  if item.is_dir():continue
  name=item.filename;p=pathlib.PurePosixPath(name)
  assert name and not p.is_absolute() and '..' not in p.parts and '\\' not in name
  assert not any(part in {'.git','node_modules'} or part.startswith('.env') for part in p.parts)
  assert 'owner' not in p.parts or p.parts[:2]==('review','owner'),'A live OWNER must not be published here'
  assert p.suffix in allowed or name=='.nojekyll',name
  assert not stat.S_ISLNK(item.external_attr>>16)
  assert item.file_size<=20*1024*1024 and name not in files
  data=archive.read(item)
  if p.suffix in {'.html','.js','.json'}:
   text=data.decode('utf-8');assert not re.search(r'sb_secret_[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}',text),name
  files[name]=data
assert 150<=len(files)<=500 and sum(map(len,files.values()))<100*1024*1024
info=json.loads(files['build-info.json'])
assert info['surface']=='app' and info['base']=='/muumei-public/' and info['sourceRevision']==revision and info['ready'] is False
config=json.loads(files['muumei-config.json'])
assert config['ready'] is False and config['key'].startswith('sb_publishable_')
for part in ['member','owner']:
 c=json.loads(files['review/'+part+'/muumei-config.json']);assert not c['url'] and not c['key'] and c['ready'] is False
 b=json.loads(files['review/'+part+'/build-info.json']);assert b['sourceRevision']==revision
 for name,data in files.items():
  if name.startswith('review/'+part+'/') and name.endswith('.html'):
   assert b"connect-src 'self'" in data and b'noindex' in data,name
assert {'review/index.html','review/review.js','jobs/index.html','direct/index.html','demo/home/index.html'}<=files.keys()
assert b'load-status' in files['review/index.html']
# All paths/bytes/configuration are verified before touching the deployed tree.
# Keep old hashed assets for already-open tabs; replace current documents atomically per file.
for name,data in files.items():
 target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
manifest.parent.mkdir(parents=True,exist_ok=True)
manifest.write_text(json.dumps({'sourceRevision':revision,'archiveSha256':expected,'files':[{'path':name,'sha256':hashlib.sha256(data).hexdigest()} for name,data in sorted(files.items())]},indent=2)+'\n')
print('Verified and installed',len(files),'public distribution files for',revision)
