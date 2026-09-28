'use client';
import {useState} from 'react';
import {Checkbox} from '@/components/ui/checkbox';
import {useApp} from '@/lib/gateway';
import type {Row} from '@/lib/brand';
import {Modal,Button,Field,Choice} from './ui';
export function ContentEditor({kind,row}:{kind:'workplaces'|'boards'|'rules';row:Row}){
 const{api,run}=useApp();const[form,setForm]=useState<Row>({...row});const[busy,setBusy]=useState(false);const set=(key:string,value:unknown)=>setForm({...form,[key]:value});
 const save=()=>{setBusy(true);void run(async()=>{
  if(kind==='rules'){
   if(!String(form.pattern||'').trim())throw Error('判定する文字列を入力してください');
   if(form.kind==='regex')try{new RegExp(form.pattern)}catch{throw Error('正規表現を確認してください')}
   await api.save('moderation_rules',{id:row.id,pattern:form.pattern,kind:form.kind,category:form.category,enabled:form.enabled});
  }else{
   if(!String(form.name||'').trim())throw Error('名前を入力してください');
   await api.save(kind,{id:row.id,name:form.name.trim(),description:form.description||'',...(kind==='workplaces'?{area:form.area,industry:form.industry,address:form.address||''}:{category:form.category})});
  }
 },'変更を保存しました').finally(()=>setBusy(false))};
 return <Modal trigger={<button className="btn secondary">内容を編集</button>} title={kind==='rules'?'禁止ワードを編集':kind==='boards'?'掲示板を編集':'職場を編集'}>
  {kind==='rules'?<><Field label="禁止ワード・正規表現" value={form.pattern} onChange={v=>set('pattern',v)} required/><Choice label="判定方式" value={form.kind} onChange={v=>set('kind',v)} options={[["literal","文字列"],["regex","正規表現"]]}/><Field label="カテゴリー" value={form.category} onChange={v=>set('category',v)}/><label className="check"><Checkbox checked={form.enabled} onCheckedChange={v=>set('enabled',v===true)}/>このルールを有効にする</label></>:<><Field label="名前" value={form.name} onChange={v=>set('name',v)} required/><Field label="説明" value={form.description} onChange={v=>set('description',v)} multiline/>{kind==='workplaces'?<><Field label="エリア" value={form.area} onChange={v=>set('area',v)} required/><Field label="業種" value={form.industry} onChange={v=>set('industry',v)}/><Field label="職場の所在地（公開してよい情報のみ）" value={form.address} onChange={v=>set('address',v)}/></>:<Field label="カテゴリー" value={form.category} onChange={v=>set('category',v)}/>}</>}
  <Button onClick={save} disabled={busy}>{busy?'保存中…':'変更を保存'}</Button>
 </Modal>;
}
