import type {Row} from './brand';
export type QueryResult={rows:Row[];total:number;[key:string]:any};
export const PAGE_SIZE=25;
/** Device-local equivalent of the authenticated SQL query. Never used for authorization. */
export function demoQuery(d:Record<string,Row[]>,uid:string,owner:boolean,kind:string,args:Record<string,any>):QueryResult {
 const tables=(name:string)=>d[name]||[];
 const matches=(v:unknown,q:unknown)=>!q||String(v||'').toLocaleLowerCase().includes(String(q).toLocaleLowerCase());
 let rows:Row[]=[];
 if(['members','groups','dashboard','applications'].includes(kind)&&!owner)throw Error('OWNER権限が必要です');
 if(kind==='members')rows=tables('profiles').map((p):Row=>({...p,favorite_id:tables('favorites').find(f=>f.user_id===p.id)?.id,group_member_id:tables('group_members').find(g=>g.group_id===args.group&&g.user_id===p.id)?.id,inviter_name:tables('profiles').find(i=>i.id===tables('invites').find(i=>i.redeemed_by===p.id)?.inviter)?.display_name})).filter(p=>matches(p.display_name,args.search)&&matches(p.area,args.area)&&(!args.status||args.status==='all'||p.status===args.status)&&(!args.source||args.source==='all'||p.signup_source===args.source)&&(!args.category||args.category==='all'||p.job_categories?.includes(args.category))&&(!args.meet||p.meet_verified)&&(!args.favorite||p.favorite_id)&&(!args.history||tables('job_applications').some(a=>a.user_id===p.id&&a.status==='completed'))&&(!args.group||args.group==='all'||args.candidates||p.group_member_id));
 else if(kind==='groups')rows=tables('groups').map((g):Row=>({...g,member_count:tables('group_members').filter(m=>m.group_id===g.id).length})).filter(g=>matches(g.name,args.search));
 else if(kind==='threads'){
  if(args.line&&!owner)throw Error('OWNER権限が必要です');
  rows=tables(args.line?'line_contacts':'owner_dm_threads').filter(t=>args.line||t.owner_id===uid||t.member_id===uid).map(t=>{const p=tables('profiles').find(p=>p.id===(owner?t.member_id:t.owner_id));return {...t,display_name:args.line?t.display_name:p?.display_name||'運営者',avatar_url:args.line?t.picture_url:p?.avatar_url}}).filter(t=>(!args.id||t.id===args.id)&&matches(t.display_name,args.search));
 }else if(kind==='calendar'){
  const counts:Record<string,number>={};for(const j of tables('jobs').filter(j=>String(j.work_date||'').startsWith(String(args.month).slice(0,7))&&matches(j.title,args.search)&&(!args.category||args.category==='all'||j.category===args.category)))counts[j.work_date]=(counts[j.work_date]||0)+1;return{rows:Object.entries(counts).map(([id,count])=>({id,count})),total:Object.values(counts).reduce((a,b)=>a+b,0)};
 }else if(kind==='home'){const apps=tables('job_applications').filter(a=>a.user_id===uid);return{rows:[],total:0,accepted:apps.filter(a=>a.status==='accepted'&&String(tables('jobs').find(j=>j.id===a.job_id)?.work_date)>=new Date().toLocaleDateString('sv-SE',{timeZone:'Asia/Tokyo'})).length,pending:apps.filter(a=>a.status==='pending').length};
 }else if(kind==='posts')rows=tables('posts').map((p):Row=>({...p,display_name:tables('profiles').find(x=>x.id===p.author_id)?.display_name})).filter(p=>(!args.board_id||p.board_id===args.board_id)&&matches(p.body,args.search));
 else if(kind==='my_applications')rows=tables('job_applications').filter(a=>a.user_id===uid).map((a):Row=>({...a,title:tables('jobs').find(j=>j.id===a.job_id)?.title,work_date:tables('jobs').find(j=>j.id===a.job_id)?.work_date}));
 else if(kind==='notifications')rows=tables('notifications').filter(n=>n.user_id===uid);
 else if(kind==='applications')rows=tables('job_applications').map((a):Row=>({...a,display_name:tables('profiles').find(p=>p.id===a.user_id)?.display_name,title:tables('jobs').find(j=>j.id===a.job_id)?.title})).filter(a=>(!args.status||args.status==='all'||a.status===args.status)&&(!args.job_id||args.job_id===a.job_id));
 else if(kind==='dashboard'){
  const jobs=tables('jobs'),apps=tables('job_applications'),profiles=tables('profiles'),count=(rows:Row[],key:string)=>rows.reduce((a,r)=>(a[r[key]]=(a[r[key]]||0)+1,a),{} as Record<string,number>);
  return {rows:[],total:0,members:profiles.length,pending:profiles.filter(p=>p.status==='pending').length,jobs:jobs.filter(j=>j.status==='published').length,applications:apps.filter(a=>a.status==='pending').length,active:profiles.filter(p=>Date.parse(p.last_active_at)>Date.now()-30*86400000).length,views:tables('job_views').length,applied:apps.length,accepted:apps.filter(a=>['accepted','completed'].includes(a.status)).length,repeats:Object.values(count(apps.filter(a=>a.status==='completed'),'user_id')).filter(n=>n>1).length,sources:count(profiles,'signup_source'),push:count(tables('push_deliveries'),'status'),reports:tables('reports').filter(r=>r.status==='open').length,unread:tables('owner_dm_messages').filter(m=>!m.read_at&&m.sender_id!==uid).length,unfilled:jobs.filter(j=>j.status==='published'&&apps.filter(a=>a.job_id===j.id&&['accepted','completed'].includes(a.status)).length<j.capacity).length,groups:tables('groups').map((g):Row=>({...g,member_count:tables('group_members').filter(m=>m.group_id===g.id).length})),recent:profiles.slice().sort((a,b)=>String(b.created_at).localeCompare(String(a.created_at))).slice(0,4),upcoming:jobs.filter(j=>j.status==='published'&&j.work_date>=new Date().toLocaleDateString('sv-SE',{timeZone:'Asia/Tokyo'})).sort((a,b)=>String(a.work_date).localeCompare(String(b.work_date))).slice(0,5)};
 }else throw Error('不明な一覧です');
 rows.sort((a,b)=>String(b.created_at||'').localeCompare(String(a.created_at||''))||a.id.localeCompare(b.id));
 const size=Math.min(100,Math.max(1,args.limit||PAGE_SIZE)),start=Math.max(0,args.page||0)*size;
 return {rows:rows.slice(start,start+size),total:rows.length,...(kind==='notifications'?{unread:rows.filter(r=>!r.read_at).length}:{})};
}
