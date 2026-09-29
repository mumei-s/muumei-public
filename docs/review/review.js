const frame=document.querySelector('#view'),notes=document.querySelector('#notes'),text=document.querySelector('#description');let role='member',version='0.11.0';const last={member:'member/demo/home/',owner:'owner/demo/dashboard/'};try{text.value=localStorage.getItem('muumei-review-note-v1')||''}catch{}text.addEventListener('input',()=>{try{localStorage.setItem('muumei-review-note-v1',text.value)}catch{}});for(const name of ['member','owner'])document.querySelector('#'+name).onclick=()=>{try{last[role]=frame.contentWindow.location.href}catch{}role=name;frame.src=last[role];frame.title=role==='member'?'メンバーの操作確認':'管理側の操作確認';for(const n of ['member','owner'])document.querySelector('#'+n).setAttribute('aria-pressed',String(role===n))};document.querySelector('#feedback').onclick=()=>{notes.hidden=!notes.hidden;document.querySelector('#feedback').setAttribute('aria-expanded',String(!notes.hidden));if(!notes.hidden)text.focus()};document.querySelector('#copy').onclick=async()=>{let path='';try{const u=new URL(frame.contentWindow.location.href);path=u.pathname}catch{}const report=['MUUMEI 操作確認 v'+version,'画面: '+role,'場所: '+path,'画面幅: '+innerWidth+' × '+innerHeight,'内容: '+text.value].join('\n');try{await navigator.clipboard.writeText(report);document.querySelector('#copy-status').textContent='コピーしました。このチャットに貼り付けてください。'}catch{text.value=report;text.focus();text.select();document.querySelector('#copy-status').textContent='選択した文章をコピーしてください。'}};document.querySelector('#reset').onclick=()=>{if(!confirm('確認用の投稿・応募などを初期状態に戻します。本番データは変更しません。'))return;for(const key of Object.keys(localStorage))if(key==='muumei-review-v1'||key.startsWith('muumei-review-v1-'))localStorage.removeItem(key);last.member='member/demo/home/';last.owner='owner/demo/dashboard/';frame.src=last[role]};
// Bounded iframe loading feedback. Never auto-reload or discard entered data.
const loadStatus=document.querySelector('#load-status'),retryView=document.querySelector('#retry-view');
let loadTimer,loadStart=0,frameLoaded=false;
function inspectView(){
 const elapsed=Math.floor((performance.now()-loadStart)/1000);
 let ready=false;
 try{ready=frameLoaded&&frame.contentDocument?.readyState==='complete'&&Boolean(frame.contentDocument.querySelector('#main'))}catch{}
 if(ready){clearInterval(loadTimer);loadStatus.textContent='表示完了 · '+(role==='member'?'メンバー画面':'確認用管理画面');retryView.hidden=true;return}
 if(elapsed>=15){clearInterval(loadTimer);loadStatus.textContent='読み込みが遅れているか、停止しています。';retryView.hidden=false;return}
 loadStatus.textContent='読み込み中（'+elapsed+'秒）';
}
function beginViewLoad(loaded=false){clearInterval(loadTimer);loadStart=performance.now();frameLoaded=loaded;retryView.hidden=true;loadStatus.textContent='読み込み中…';loadTimer=setInterval(inspectView,500)}
new MutationObserver(()=>beginViewLoad()).observe(frame,{attributes:true,attributeFilter:['src']});
frame.addEventListener('load',()=>{frameLoaded=true;inspectView()});
frame.addEventListener('error',()=>{clearInterval(loadTimer);loadStatus.textContent='画面を読み込めませんでした。';retryView.hidden=false});
retryView.onclick=()=>{beginViewLoad();try{frame.contentWindow.location.reload()}catch{frame.src=last[role]}};
beginViewLoad(Boolean(frame.contentDocument?.querySelector('#main')));
