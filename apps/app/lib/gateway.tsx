'use client';import {publicConfigPath} from '@/lib/public-config';import {uuid} from '@/lib/id';import {demoQuery,type QueryResult} from './queries';import {withDeadline} from './deadline';import {migrateDemo,isDemoSnapshot} from './demo-migrations';
import {createContext,useContext,useEffect,useState,useCallback,type ReactNode} from 'react';import {createClient,type SupabaseClient,type User} from '@supabase/supabase-js';import {toast} from 'sonner';import {demoData,demoMember,demoOwner} from './demo';import {surface} from './surface';import type {Row,Config} from './brand';
const initial:Config={url:'',key:'',appUrl:'',vapid:'',ready:false,operator:{name:'',address:'',contact:''}};
export class Gateway{
 client:SupabaseClient|null=null;data:Record<string,Row[]>|null=null;uid='';owner=surface==='owner';key='muumei-demo-v2';
 constructor(config:Config,demo:boolean){if(demo){this.data=demoData();this.uid=this.owner?demoOwner:demoMember;}else if(config.url&&config.key)this.client=createClient(config.url,config.key,{auth:{storageKey:'muumei-'+surface,detectSessionInUrl:true,persistSession:true,autoRefreshToken:true}})}
 loadDemo(){try{const stored=localStorage.getItem(this.key);if(stored){const parsed:unknown=JSON.parse(stored);if(isDemoSnapshot(parsed))this.data=migrateDemo({...demoData(),...parsed}) as Record<string,Row[]>;}this.persist()}catch{/* Storage unavailable or invalid: retain the safe demo seed. */}}
 persist(){if(this.data)localStorage.setItem(this.key,JSON.stringify(this.data))}
 async page(table:string,filter:Record<string,any>={},search='',column='name',page=0,size=25):Promise<QueryResult>{
  size=Math.max(1,Math.min(size,100));page=Math.max(0,page);
  if(this.data){const filtered=(this.data[table]||[]).filter(r=>Object.entries(filter).every(([k,v])=>r[k]===v)).filter(r=>!search||String(r[column]||'').toLocaleLowerCase().includes(search.toLocaleLowerCase())).sort((a,b)=>String(b.created_at||'').localeCompare(String(a.created_at||''))||a.id.localeCompare(b.id));return {rows:filtered.slice(page*size,(page+1)*size),total:filtered.length}}
  if(!this.client)throw Error('本番接続を準備中です。見本モードをお試しください。');
  let q=this.client.from(table).select('*',{count:'exact'});for(const[k,v]of Object.entries(filter))q=q.eq(k,v);if(search)q=q.ilike(column,'%'+search.replace(/[%_]/g,'')+'%');
  const{data,error,count}=await q.order('created_at',{ascending:false}).order('id',{ascending:true}).range(page*size,(page+1)*size-1);if(error)throw error;return {rows:data||[],total:count||0};
 }
 async list(table:string,filter:Record<string,any>={},search='',column='name',page=0):Promise<Row[]>{return (await this.page(table,filter,search,column,page,100)).rows}
 async all(table:string,filter:Record<string,any>={}){const rows:Row[]=[];let page=0;while(true){const batch=await this.page(table,filter,'','name',page++,100);rows.push(...batch.rows);if(!batch.rows.length||rows.length>=batch.total)return rows}}
 async markNotificationsRead(){if(this.data){for(const n of this.data.notifications||[])if(n.user_id===this.uid)n.read_at=new Date().toISOString();this.persist();return}const{error}=await this.client!.rpc('read_all_notifications');if(error)throw error}
 async query(kind:string,args:Record<string,any>={}):Promise<QueryResult>{if(this.data)return demoQuery(this.data,this.uid,this.owner,kind,args);if(!this.client)throw Error('未接続です');const{data,error}=await this.client.rpc('app_query',{kind,args});if(error)throw error;return data}
 async history(table:string,key:string,id:string,before?:Row):Promise<Row[]>{
  if(this.data)return (this.data[table]||[]).filter(m=>m[key]===id&&(!before||m.created_at<before.created_at||m.created_at===before.created_at&&m.id<before.id)).sort((a,b)=>String(b.created_at).localeCompare(String(a.created_at))||b.id.localeCompare(a.id)).slice(0,50);
  if(!this.client)throw Error('未接続です');let q=this.client.from(table).select('*').eq(key,id).order('created_at',{ascending:false}).order('id',{ascending:false}).limit(50);
  if(before){const at=new Date(before.created_at).toISOString();if(!/^[0-9a-f-]{36}$/i.test(before.id))throw Error('履歴の位置が不正です');q=q.or(`created_at.lt.${at},and(created_at.eq.${at},id.lt.${before.id})`)}
  const{data,error}=await q;if(error)throw error;return data||[];
 }
 async save(table:string,value:Partial<Row>):Promise<Row>{if(this.data){const id=value.id||uuid();const existing=(this.data[table]||[]).find(x=>x.id===id);const row={created_at:new Date().toISOString(),...existing,...value,id} as Row;if(['posts','reviews'].includes(table)&&/死ね|殺す|0\d{9,10}|[\w.+-]+@/.test(String(value.body||'').normalize('NFKC').replace(/[\s\-ー]/g,'')))throw Error('投稿内容に個人情報や禁止表現が含まれています');this.data[table]=[...(this.data[table]||[]).filter(x=>x.id!==id),row];this.persist();return row}if(!this.client)throw Error('未接続です');const{id,...patch}=value;const q=id?this.client.from(table).update(patch).eq('id',id):this.client.from(table).insert(patch);const{data,error}=await q.select().single();if(error)throw error;return data}
 async remove(table:string,id:string){if(this.data){this.data[table]=(this.data[table]||[]).filter(r=>r.id!==id);this.persist();return}const{error}=await this.client!.from(table).delete().eq('id',id);if(error)throw error}
 async command(action:string,args:Record<string,any>={}):Promise<any>{if(!this.data){if(!this.client)throw Error('本番接続を準備中です');const{data,error}=await this.client.rpc('app_command',{action,args});if(error)throw error;return data}
 const d=this.data;
 if(action==='save_job'){const r=await this.save('jobs',args.form);this.data.job_targets=this.data.job_targets.filter(t=>t.job_id!==r.id);for(const [purpose,items]of [['view',args.targets],['notify',args.notify]] as const)for(const item of items||[])await this.save('job_targets',{job_id:r.id,purpose,[item.startsWith('g:')?'group_id':'user_id']:item.slice(2)});return r}
 if(action==='onboard')return this.save('profiles',{id:this.uid,...args,status:'pending'});
 if(action==='approve'){if(!this.owner)throw Error('OWNER権限が必要です');await this.save('moderation_logs',{actor:this.uid,target:args.user_id,action:args.status,reason:args.reason});return this.save('profiles',{id:args.user_id,status:args.status})}
 if(action==='apply'){const j=d.jobs.find(x=>x.id===args.job_id);if(!j||j.status!=='published')throw Error('受付を終了しています');if(d.job_applications.some(a=>a.job_id===j.id&&a.user_id===this.uid&&['pending','accepted','completed'].includes(a.status)))throw Error('申込済みです');if(d.job_applications.filter(a=>a.job_id===j.id&&a.status==='accepted').length>=j.capacity)throw Error('定員に達しました');return this.save('job_applications',{job_id:j.id,user_id:this.uid,status:j.application_mode==='first_come'?'accepted':'pending',answers:args.answers})}
 if(action==='decide_application')return this.save('job_applications',{id:args.id,status:args.status});if(action==='withdraw')return this.save('job_applications',{id:args.id,status:'withdrawn'});
 if(action==='open_dm'){const mid=this.owner?args.member_id:demoMember;return d.owner_dm_threads.find(t=>t.member_id===mid)||this.save('owner_dm_threads',{owner_id:demoOwner,member_id:mid})}
 if(action==='send_message'){const r=await this.save('owner_dm_messages',{thread_id:args.thread_id,sender_id:this.uid,body:args.body||'添付ファイル'});for(const id of args.attachments||[])await this.save('dm_attachments',{id,message_id:r.id});return r}
 if(action==='availability')return {remaining:Math.max(0,Number(d.jobs.find(j=>j.id===args.job_id)?.capacity)-d.job_applications.filter(a=>a.job_id===args.job_id&&a.status==='accepted').length)};
 if(action==='issue_meet'||action==='issue_email_invite'||action==='issue_job_link'){const token=uuid().replaceAll('-','')+uuid().replaceAll('-','');const expires_at=new Date(Date.now()+600000).toISOString();await this.save(action==='issue_meet'?'meet_passes':'invites',{token,expires_at,status:'issued',inviter:this.uid,...args});return {token,expires_at}}
 if(action==='receive_meet'){const p=d.meet_passes.find(x=>x.token===args.token);if(!p||p.status!=='issued'||Date.parse(p.expires_at)<Date.now())throw Error('期限切れ、または使用済みのQRです');const claim=uuid();await this.save('meet_passes',{id:p.id,status:'received',claim});return {claim}}
 if(action==='claim_meet'){const p=d.meet_passes.find(x=>x.claim===args.claim&&x.status==='received');if(!p)throw Error('PASSが無効です');await this.save('meet_passes',{id:p.id,status:'claimed'});return this.save('profiles',{id:this.uid,meet_verified:true})}
 if(action==='read_dm'||action==='heartbeat')return {ok:true};if(action==='moderate')return this.save(args.table,{id:args.id,status:args.status});if(action==='resolve_report')return this.save('reports',{id:args.id,status:'resolved'});
 if(action==='line_send'){const r=await this.save('line_messages',{contact_id:args.contact_id,direction:'outbound',body:args.body,status:'sent',sender_name:args.sender_name});for(const id of args.attachments||[])await this.save('line_attachments',{id,message_id:r.id});return r}
 throw Error('この操作は実接続後に利用できます')}
 async edge(name:string,body:Record<string,any>){if(this.data){if(name==='invite-email')return this.command('issue_email_invite',body);if(name==='line-send')return this.command('line_send',body);return {demo:true}}if(!this.client)throw Error('未接続です');const{data,error}=await this.client.functions.invoke(name,{body});if(error)throw error;return data}
}
type ContextType={api:Gateway;config:Config;demo:boolean;user:User|null;profile:Row|null;profileLoading:boolean;loading:boolean;error:string;revision:number;refresh:()=>void;run:<T>(fn:()=>Promise<T>,success?:string)=>Promise<T|undefined>};const Context=createContext<ContextType|null>(null);
export function Provider({demo,children}:{demo:boolean;children:ReactNode}){const[config,setConfig]=useState(initial),[api,setApi]=useState(()=>new Gateway(initial,demo)),[user,setUser]=useState<User|null>(null),[profile,setProfile]=useState<Row|null>(null),[profileLoading,setProfileLoading]=useState(true),[loading,setLoading]=useState(true),[error,setError]=useState(''),[revision,setRevision]=useState(0);const refresh=useCallback(()=>setRevision(x=>x+1),[]);
 useEffect(()=>{
  let live=true;let unsubscribe=()=>{};const controller=new AbortController();
  setLoading(true);setError('');
  (async()=>{
   try{
    // The local demonstration never depends on live backend configuration.
    if(demo){const g=new Gateway(initial,true);g.loadDemo();if(live){setApi(g);setConfig(initial);setUser(null)}return}
    const c=await withDeadline((async()=>{const r=await fetch(publicConfigPath,{signal:controller.signal,cache:'no-store'});if(!r.ok)throw Error('設定を読み込めません。もう一度お試しください。');return await r.json() as Config})());
    if(!live)return;
    const g=new Gateway(c,false);setConfig(c);setApi(g);
    if(g.client){
     const{data,error:authError}=await withDeadline(g.client.auth.getUser(),12000,'ログイン状態を確認できません。通信状態を確認して、再読み込みしてください。');
     if(!live)return;
     if(authError&&authError.name!=='AuthSessionMissingError')throw authError;
     g.uid=data.user?.id||'';setUser(data.user);
     const{data:{subscription}}=g.client.auth.onAuthStateChange((_event,session)=>{if(!live)return;g.uid=session?.user.id||'';setUser(session?.user||null);refresh()});
     unsubscribe=()=>subscription.unsubscribe();
    }
   }catch(e){controller.abort();if(live)setError(e instanceof Error?e.message:'接続できません。再読み込みしてください。')}
   finally{if(live)setLoading(false)}
  })();
  return()=>{live=false;controller.abort();unsubscribe()};
 },[demo,refresh]);
 useEffect(()=>{
  let live=true;setProfileLoading(true);
  if(!api.uid){setProfile(null);setProfileLoading(false);return}
  withDeadline(api.list('profiles',{id:api.uid})).then(rows=>{if(live)setProfile(rows[0]||null)}).catch(e=>{if(live)setError(e.message)}).finally(()=>{if(live)setProfileLoading(false)});
  return()=>{live=false};
 },[api,user,revision]);
 useEffect(()=>{if(profile?.status!=='approved'||!api.client)return;const touch=()=>{if(document.visibilityState==='visible')void api.command('heartbeat').catch(()=>{})};touch();const timer=setInterval(touch,300000);return()=>clearInterval(timer)},[api,profile?.status]);
 const run=async<T,>(fn:()=>Promise<T>,success?:string)=>{try{const r=await fn();refresh();if(success)toast.success(success);return r}catch(e){toast.error(e instanceof Error?e.message:'操作できませんでした');return undefined}};
 return <Context.Provider value={{api,config,demo,user,profile,profileLoading,loading,error,revision,refresh,run}}>{children}</Context.Provider>}
export function useApp(){const c=useContext(Context);if(!c)throw Error('Provider required');return c}
export function useRows(table:string,filter:Record<string,any>={},search='',column='name',page=0){const{api,revision}=useApp();const[rows,setRows]=useState<Row[]>([]),[loading,setLoading]=useState(true),[error,setError]=useState('');const key=JSON.stringify(filter);useEffect(()=>{let live=true;setLoading(true);setError('');const t=setTimeout(()=>{if(live){setError('読み込みが遅れています。再読み込みしてください');setLoading(false)}},12000);api.list(table,JSON.parse(key),search,column,page).then(r=>{if(live)setRows(r)}).catch(e=>{if(live)setError(e.message)}).finally(()=>{clearTimeout(t);if(live)setLoading(false)});return()=>{live=false;clearTimeout(t)}},[api,revision,table,key,search,column,page]);return {rows,loading,error}}
export function useDebounce(v:string){const[x,setX]=useState(v);useEffect(()=>{const t=setTimeout(()=>setX(v),250);return()=>clearTimeout(t)},[v]);return x}

export function useQuery(kind:string,args:Record<string,any>={}){
 const{api,revision}=useApp();const key=kind+JSON.stringify(args);const[state,setState]=useState<{key:string;data:QueryResult|null;error:string}>({key:'',data:null,error:''});
 useEffect(()=>{let live=true;setState({key,data:null,error:''});withDeadline(api.query(kind,JSON.parse(key.slice(kind.length)))).then(data=>{if(live)setState({key,data,error:''})}).catch(e=>{if(live)setState({key,data:null,error:e.message})});return()=>{live=false}},[api,revision,key,kind]);
 const current=state.key===key?state:{data:null,error:''};return {data:current.data,rows:current.data?.rows||[],total:current.data?.total||0,error:current.error,loading:!current.data&&!current.error};
}
export function usePage(table:string,filter:Record<string,any>={},search='',column='name',size=25){
 const{api,revision}=useApp();const[page,setPage]=useState(0),[state,setState]=useState<{key:string;data:QueryResult|null;error:string}>({key:'',data:null,error:''});const filterKey=JSON.stringify(filter),base=table+filterKey+search+column;
 useEffect(()=>setPage(0),[base]);const key=base+page;
 useEffect(()=>{let live=true;setState({key,data:null,error:''});withDeadline(api.page(table,JSON.parse(filterKey),search,column,page,size)).then(data=>{if(live)setState({key,data,error:''})}).catch(e=>{if(live)setState({key,data:null,error:e.message})});return()=>{live=false}},[api,revision,table,filterKey,search,column,page,size,key]);
 const current=state.key===key?state:{data:null,error:''};return {rows:current.data?.rows||[],total:current.data?.total||0,error:current.error,loading:!current.data&&!current.error,page,setPage,size};
}
