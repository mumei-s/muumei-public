import { cpSync, mkdirSync, readFileSync, writeFileSync, readdirSync, rmSync, symlinkSync } from 'node:fs';
import { resolve, join, basename } from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';

// Packaging only. Business logic, database privileges and live hosting settings are unchanged.
const source=resolve(process.argv[2]||'.'),surface=process.argv[3]||'app',base=process.argv[4]||'/muumei-public/',appUrl=process.argv[5]||'https://mumei-s.github.io/muumei-public/';
if(!['app','owner'].includes(surface))throw Error('Unknown surface');
if(!/^\/(?:[A-Za-z0-9_-]+\/)*$/.test(base))throw Error('Invalid base path');
const canonical=new URL(appUrl);
if(canonical.protocol!=='https:'||canonical.username||canonical.password||canonical.search||canonical.hash||!/^\/(?:[A-Za-z0-9_-]+\/)*$/.test(canonical.pathname))throw Error('Invalid canonical app URL');
const original=join(source,'apps',surface),work=join(source,'.pages-staging',surface),app=join(work,'apps',surface);
mkdirSync(work,{recursive:true});rmSync(app,{recursive:true,force:true});
cpSync(original,app,{recursive:true,filter:p=>!['node_modules','.git','dist','dist-static','dist-pages'].includes(basename(p))&&!basename(p).startsWith('.env')});
mkdirSync(join(work,'scripts'),{recursive:true});cpSync(join(source,'scripts/public-config.mjs'),join(work,'scripts/public-config.mjs'));
symlinkSync(join(original,'node_modules'),join(app,'node_modules'),'dir');
const require=createRequire(join(original,'package.json')),ts=require('typescript'),f=ts.factory,ident='_muumeiPageUrl';
const wrap=e=>f.createCallExpression(f.createIdentifier(ident),undefined,[e]);
const printed=ts.createPrinter({newLine:ts.NewLineKind.LineFeed});
const routes=surface==='app'?['about','operator','security','rules','privacy','terms','contact','faq','login','join','invite','receive','demo-receive','job-link','match-preview',...['app','demo'].flatMap(p=>['home','crew','work','boards','workplaces','my','messages','meet','notifications','install'].map(x=>p+'/'+x))]:['login',...['','demo/'].flatMap(p=>['dashboard','approvals','members','favorites','groups','invites','jobs','jobs/new','calendar','templates','applications','campaigns','messages','line','notifications','install','workplaces','boards','reviews','reports','rules','analytics','settings'].map(x=>p+x))];
let modified=0;
function walk(dir){return readdirSync(dir,{withFileTypes:true}).flatMap(e=>e.isDirectory()&&!['node_modules','public'].includes(e.name)?walk(join(dir,e.name)):e.isFile()&&e.name.endsWith('.tsx')?[join(dir,e.name)]:[])}
for(const file of walk(join(app,'components'))){
 const sf=ts.createSourceFile(file,readFileSync(file,'utf8'),ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);let changed=false;
 const result=ts.transform(sf,[context=>root=>{
  const match=(n,re)=>re.test(n.getText(sf));
  const visit=node=>{
   if(ts.isJsxAttribute(node)&&['href','src','action'].includes(node.name.getText(sf))&&node.initializer){const init=node.initializer,expr=ts.isStringLiteral(init)?f.createStringLiteral(init.text):ts.isJsxExpression(init)?init.expression:undefined;if(expr){changed=true;return f.updateJsxAttribute(node,node.name,f.createJsxExpression(undefined,wrap(ts.visitNode(expr,visit))))}}
   if(ts.isBinaryExpression(node)){
    if(node.operatorToken.kind===ts.SyntaxKind.PlusToken&&match(node.left,/^(?:window\.)?location\.origin$/)){changed=true;return f.updateBinaryExpression(node,node.left,node.operatorToken,wrap(ts.visitNode(node.right,visit)))}
    if(node.operatorToken.kind===ts.SyntaxKind.EqualsToken&&match(node.left,/^(?:window\.)?location\.(?:href|pathname)$/)){changed=true;return f.updateBinaryExpression(node,node.left,node.operatorToken,wrap(ts.visitNode(node.right,visit)))}
   }
   if(ts.isCallExpression(node)){const callee=node.expression.getText(sf);if(/^(?:window\.)?location\.(?:assign|replace)$/.test(callee)&&node.arguments.length){changed=true;return f.updateCallExpression(node,node.expression,node.typeArguments,[wrap(ts.visitNode(node.arguments[0],visit)),...node.arguments.slice(1)])}if(callee==='navigator.serviceWorker.register'){changed=true;return f.updateCallExpression(node,node.expression,node.typeArguments,[wrap(node.arguments[0]),f.createObjectLiteralExpression([f.createPropertyAssignment('scope',wrap(f.createStringLiteral('/')))])])}}
   return ts.visitEachChild(node,visit,context);
  };return ts.visitNode(root,visit);
 }]);
 if(changed){writeFileSync(file,`import { pageUrl as ${ident} } from '@/lib/pages-base';\n`+printed.printFile(result.transformed[0]));modified++}result.dispose();
}
const helper=`declare const __MUUMEI_BASE_PATH__: string;
const base=__MUUMEI_BASE_PATH__;
export function pageUrl<T>(value:T):T {
 if(typeof value!=='string'||!value.startsWith('/')||value.startsWith('//'))return value;
 if(value.includes('\\\\'))throw Error('Invalid local URL');
 if(base==='/'||value===base.slice(0,-1)||value.startsWith(base))return value;
 return (base+value.slice(1)) as T;
}
export function appPath(path:string):string {
 const local=base==='/'?path:path===base.slice(0,-1)?'/':path.startsWith(base)?'/'+path.slice(base.length):'/__outside_base__';
 return local.length>1?local.replace(/\\/$/,''):local;
}
export function restoreRoute(){
 const u=new URL(location.href),route=u.searchParams.get('__muumei_route');
 if(route===null||route.length>8192||route.startsWith('/')||route.includes('\\\\'))return;
 const target=new URL(base+route,location.origin);
 if(target.origin!==location.origin||!target.pathname.startsWith(base))return;
 history.replaceState(null,'',target.pathname+target.search+location.hash);
}
`;
writeFileSync(join(app,'lib/pages-base.ts'),helper);
const mainFile=join(app,'main.tsx');let main=readFileSync(mainFile,'utf8');
if(!main.includes('path={location.pathname}'))throw Error('Entry route changed; inspect before packaging');
main="import {appPath,restoreRoute} from './lib/pages-base';\n"+main.replace('createRoot(','restoreRoute();\ncreateRoot(').replace('path={location.pathname}','path={appPath(location.pathname)}');writeFileSync(mainFile,main);
const publicConfig=await import(pathToFileURL(join(source,'scripts/public-config.mjs')).href),defaults=JSON.parse(readFileSync(join(original,'wrangler.jsonc'),'utf8')).vars;
const config=publicConfig.createPublicConfig({...defaults,MUUMEI_APP_URL:canonical.origin,MUUMEI_PRODUCTION_READY:'false'});config.appUrl=canonical.href.replace(/\/$/,'');
writeFileSync(join(app,'public/muumei-config.json'),JSON.stringify(config,null,2)+'\n');
writeFileSync(join(app,'vite.config.ts'),`import{defineConfig}from'vite';import react from'@vitejs/plugin-react';import{fileURLToPath,URL}from'node:url';export default defineConfig({base:${JSON.stringify(base)},plugins:[react()],define:{__MUUMEI_BASE_PATH__:${JSON.stringify(JSON.stringify(base))},__MUUMEI_CONFIG_PATH__:${JSON.stringify(JSON.stringify(base+'muumei-config.json'))}},resolve:{alias:{'@':fileURLToPath(new URL('.',import.meta.url))}},build:{outDir:'dist-pages',emptyOutDir:true,sourcemap:false}});\n`);
// The previous footer white-text rule must not make a white secondary button unreadable.
writeFileSync(join(app,'app/photo-theme.css'),readFileSync(join(app,'app/photo-theme.css'),'utf8')+'\n.m-footer a.m-underlink,.m-footer a.m-underlink:hover{color:#162337!important}\n');
const manifestPath=join(app,'public/manifest.webmanifest'),manifest=JSON.parse(readFileSync(manifestPath,'utf8')),url=p=>typeof p==='string'&&p.startsWith('/')&&!p.startsWith('//')?base+p.slice(1):p;
manifest.id=base;manifest.scope=base;manifest.start_url=url(manifest.start_url||'/');for(const icon of manifest.icons||[])icon.src=url(icon.src);for(const shortcut of manifest.shortcuts||[]){shortcut.url=url(shortcut.url);for(const icon of shortcut.icons||[])icon.src=url(icon.src)}writeFileSync(manifestPath,JSON.stringify(manifest,null,2)+'\n');
writeFileSync(join(app,'public/offline.html'),readFileSync(join(app,'public/offline.html'),'utf8').replace(/(href|src)="\/(?!\/)/g,`$1="${base}`));
const prefix='muumei-pages-'+surface+'-'+createHash('sha256').update(base).digest('hex').slice(0,10)+'-',revision=createHash('sha256').update(process.env.SOURCE_REVISION||'local').update(readFileSync(fileURLToPath(import.meta.url))).digest('hex').slice(0,16);
const sw=`const BASE=${JSON.stringify(base)},PREFIX=${JSON.stringify(prefix)},VERSION=PREFIX+${JSON.stringify(revision)};
const local=p=>BASE+p.replace(/^\\//,'');const FALLBACK=local('offline.html');
self.addEventListener('install',e=>e.waitUntil(caches.open(VERSION).then(c=>c.addAll([FALLBACK,local('icons/icon-192.png')]))));
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith(PREFIX)&&k!==VERSION).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('message',e=>{if(e.data?.type==='SKIP_WAITING')self.skipWaiting()});
self.addEventListener('fetch',e=>{const u=new URL(e.request.url);if(e.request.mode==='navigate'&&u.origin===self.location.origin&&u.pathname.startsWith(BASE))e.respondWith(fetch(e.request).catch(()=>caches.match(FALLBACK)))});
function destination(value){if(typeof value!=='string'||!/^\\/(?!\\/)/.test(value)||value.includes('\\\\'))return local('app/notifications');const u=new URL(value.startsWith(BASE)?value:local(value),self.location.origin);return u.origin===self.location.origin&&u.pathname.startsWith(BASE)?u.pathname+u.search+u.hash:local('app/notifications')}
self.addEventListener('push',e=>{let data={title:'MUUMEI',body:'新しいお知らせがあります',url:'/app/notifications'};try{Object.assign(data,e.data.json())}catch{}e.waitUntil(self.registration.showNotification(data.title,{body:data.body,icon:local('icons/icon-192.png'),badge:local('icons/badge-96.png'),tag:data.id||'muumei',data:{url:destination(data.url)}}))});
self.addEventListener('notificationclick',e=>{e.notification.close();const target=new URL(destination(e.notification.data?.url),self.location.origin);e.waitUntil(self.clients.matchAll({type:'window',includeUncontrolled:true}).then(async list=>{for(const c of list){const u=new URL(c.url);if(u.origin===target.origin&&u.pathname.startsWith(BASE)){await c.navigate(target.href);return c.focus()}}return self.clients.openWindow(target.href)}))});
`;
writeFileSync(join(app,'public/sw.js'),sw);
for(const cmd of [['exec','tsc','--noEmit'],['exec','vite','build']]){const r=spawnSync('pnpm',cmd,{cwd:app,stdio:'inherit'});if(r.status!==0)process.exit(r.status||1)}
const dist=join(app,'dist-pages');let html=readFileSync(join(dist,'index.html'),'utf8');
const policy="default-src 'self'; object-src 'none'; base-uri 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https:; connect-src 'self' "+config.url+' '+config.url.replace(/^https:/,'wss:')+"; form-action 'self'";
html=html.replace('<head>',`<head><meta http-equiv="Content-Security-Policy" content="${policy}"><meta name="referrer" content="strict-origin-when-cross-origin">`);writeFileSync(join(dist,'index.html'),html);
for(const route of routes){mkdirSync(join(dist,route),{recursive:true});writeFileSync(join(dist,route,'index.html'),html)}
writeFileSync(join(dist,'404.html'),`<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="${policy}"><title>MUUMEI</title></head><body><p>ページを開いています…</p><script src="${base}route-404.js"></script></body></html>`);
writeFileSync(join(dist,'route-404.js'),`const b=${JSON.stringify(base)};if(location.pathname.startsWith(b)){const r=location.pathname.slice(b.length)+location.search;location.replace(b+'?__muumei_route='+encodeURIComponent(r)+location.hash)}else{document.querySelector('p').textContent='このページは見つかりません'};\n`);
writeFileSync(join(dist,'.nojekyll'),'');for(const file of ['_headers','_redirects'])rmSync(join(dist,file),{force:true});
writeFileSync(join(dist,'build-info.json'),JSON.stringify({surface,base,sourceRevision:process.env.SOURCE_REVISION||'local',packagerRevision:process.env.GITHUB_SHA||'local',ready:false,generatedAt:new Date().toISOString()},null,2)+'\n');
const out=join(source,'release',surface);rmSync(out,{recursive:true,force:true});mkdirSync(out,{recursive:true});cpSync(dist,out,{recursive:true});console.log(JSON.stringify({surface,base,modifiedComponents:modified,output:out,ready:false}));
