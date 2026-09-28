'use client';
import {useEffect,useState} from 'react';
import {useApp} from './gateway';
import {withDeadline} from './deadline';
import type {Row} from './brand';
/** Re-fetch loaded pages on incoming events, so older unsent messages disappear too. */
export function useHistory(id:string|undefined,line:boolean){
 const{api,revision}=useApp();const[pages,setPages]=useState(1),[rows,setRows]=useState<Row[]>([]),[loading,setLoading]=useState(true),[error,setError]=useState(''),[more,setMore]=useState(false);
 useEffect(()=>{setPages(1);setRows([])},[id,line]);
 useEffect(()=>{let live=true;if(!id){setRows([]);setLoading(false);return}setLoading(true);setError('');void(async()=>{const found:Row[]=[];let cursor:Row|undefined,last:Row[]=[];for(let p=0;p<pages;p++){last=await withDeadline(api.history(line?'line_messages':'owner_dm_messages',line?'contact_id':'thread_id',id,cursor),12000,'会話の取得に時間がかかっています');if(!live)return;found.push(...last);cursor=last.at(-1);if(last.length<50)break}if(live){setRows(found.reverse());setMore(last.length===50);if(!line)void api.command('read_dm',{thread_id:id}).catch(()=>{})}})().catch(e=>{if(live)setError(e.message)}).finally(()=>{if(live)setLoading(false)});return()=>{live=false}},[api,id,line,pages,revision]);
 return{rows,loading,error,more,older:()=>setPages(p=>p+1)};
}
