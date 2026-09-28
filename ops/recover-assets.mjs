import{readFileSync,writeFileSync,mkdirSync,existsSync}from'node:fs';import{resolve,join}from'node:path';import{createHash}from'node:crypto';
const root=resolve(process.argv[2]||'.');
const files=[['images/work-together.webp','c28891a0540b68e5a937ea6d5a290a9e5a942520'],['images/everyday-connections.webp','3d4d6bb4f6f27246f6611255df401888bc5aeef9'],['icons/maskable-512.png',null]];
for(const[path,expected]of files){
 const local=join(root,'apps/app/public',path);let data;
 if(existsSync(local))data=readFileSync(local);else{
  const response=await fetch('https://muumei.sabosan0404.chatgpt.site/'+path,{signal:AbortSignal.timeout(30000)});
  if(!response.ok)throw Error('Cannot restore public media: '+path+' HTTP '+response.status);
  data=Buffer.from(await response.arrayBuffer());
 }
 const valid=path.endsWith('.webp')?data.toString('ascii',0,4)==='RIFF'&&data.toString('ascii',8,12)==='WEBP':data.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10]));
 if(!valid||data.length<100||data.length>2000000)throw Error('Invalid image response: '+path);
 const hash=createHash('sha1').update('blob '+data.length+'\0').update(data).digest('hex');
 if(expected&&hash!==expected)throw Error('Original image integrity mismatch: '+path);
 for(const surface of['app','owner']){const target=join(root,'apps',surface,'public',path);mkdirSync(join(target,'..'),{recursive:true});writeFileSync(target,data)}
 console.log(path+' verified '+hash+' '+data.length+' bytes');
}
