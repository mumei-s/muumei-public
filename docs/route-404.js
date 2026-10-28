// One Pages fallback, with explicit boundaries for real pages and member samples.
(() => {
 const root='/muumei-public/',sample=root+'review/member/',owner=root+'review/owner/';
 const path=location.pathname;
 if(!path.startsWith(root)){const message=document.querySelector('p');if(message)message.textContent='このページは見つかりません';return}
 if(path.startsWith(owner)||path===root+'review/owner'){location.replace(root);return}
 if(path.startsWith(sample)){
  const route=path.slice(sample.length)+location.search;
  if(route.length>8192||route.includes('\\'))return;
  if(path.startsWith(sample+'demo/')){location.replace(sample+'demo/home/?__muumei_route='+encodeURIComponent(route)+location.hash);return}
  const ordinary=path.slice(sample.length);
  location.replace(root+ordinary);return;
 }
 const route=path.slice(root.length)+location.search;
 if(route.length>8192||route.includes('\\'))return;
 if(path===root+'demo'||path===root+'demo/'){location.replace(sample+'demo/home/');return}
 if(path.startsWith(root+'demo/')){location.replace(sample+path.slice(root.length)+location.search+location.hash);return}
 // The ordinary top is a brochure. Boot the preserved real member application
 // from its own HTML before its restoreRoute() restores a dynamic member URL.
 if(path.startsWith(root+'app/')){location.replace(root+'app/home/?__muumei_route='+encodeURIComponent(route)+location.hash);return}
 location.replace(root+'?__muumei_route='+encodeURIComponent(route)+location.hash);
})();
