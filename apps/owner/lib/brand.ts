export const brand={name:'MUUMEI',reading:'ムーメイ',tagline:'仕事で生まれた縁を、次へ。',version:'0.10.1',navy:'#101319',aqua:'#92baff',cloud:'#edf0f5'};
export const categories=['ポスティング','物流・軽作業','配送補助','イベント','接客','その他'];
export const sourceNames:Record<string,string>={spotwork:'SPOT',direct:'DIRECT',referral:'紹介',owner_email:'メール招待',qr:'対面QR',other:'その他'};
export const labels:Record<string,string>={approved:'承認済み',pending:'承認待ち',invited:'招待中',email_verified:'メール確認済み',rejected:'否認',suspended:'停止',banned:'利用禁止',draft:'下書き',published:'募集中',scheduled:'公開予約',closed:'募集終了',accepted:'参加確定',declined:'見送り',withdrawn:'取り下げ',completed:'完了',queued:'送信待ち',sending:'送信中',sent:'送信受付済み',failed:'送信失敗',received:'受信',all:'承認済みの全員',individual:'個人指定',favorites:'お気に入り',groups:'グループ',spotwork:'SPOT経由',direct:'DIRECT経由',url:'URL限定',owner:'OWNER指定'};
export const notificationCategories={jobs:'新しい仕事',applications:'参加・承認',dm:'メッセージ',replies:'掲示板の返信',changes:'求人の変更',reminders:'仕事前の確認',important:'重要なお知らせ'};
export const legalFields={employer:'募集者の名称',employer_address:'募集者の住所',contact:'連絡先',contract_period:'契約期間',renewal:'更新基準・上限',work_change:'業務の変更範囲',location_change:'就業場所の変更範囲',overtime:'時間外労働',insurance:'加入保険',smoking:'受動喫煙防止措置',cancellation:'キャンセル・解除条件',deliverable:'業務内容・納品物・期日',payment_due:'支払期日'};
export type Row={id:string;[k:string]:any};
export type Config={url:string;key:string;appUrl:string;vapid:string;ready:boolean;operator:{name:string;address:string;contact:string}};
