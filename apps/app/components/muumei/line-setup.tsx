'use client';
import {useEffect,useRef} from 'react';
import {useApp} from '@/lib/gateway';
import {Button} from './ui';

const webhook='https://slamzhgsawfnmwlejgqp.supabase.co/functions/v1/line-webhook';
export function LineSetupGuide(){
 const{run,demo}=useApp();const section=useRef<HTMLElement>(null);
 useEffect(()=>{if(location.hash==='#line-setup')section.current?.scrollIntoView({block:'start'})},[]);
 return <section ref={section} className="card line-setup" id="line-setup" aria-labelledby="line-setup-title">
  <p className="eyebrow">LINE CONNECTION</p>
  <h2 id="line-setup-title">LINEとつなぐには</h2>
  <p className="line-setup-lead">相手はいつものLINE。あなたはMUUMEIの「LINE受信箱」から返信できます。</p>
  <div className="notice">{demo?'この画面は見本です。LINEには送信しません。':'設定を保存するだけでは接続完了になりません。最後に実際の送受信を確認してください。'}</div>
  <ol className="line-setup-steps">
   <li><h3>メールで公式アカウントを用意する</h3><p>LINE Business IDにメールアドレスで登録し、MUUMEI用のLINE公式アカウントを作ります。登録・メール確認・規約への同意は、ご本人のアカウントで行ってください。</p><a className="text-link" href="https://developers.line.biz/ja/docs/messaging-api/getting-started/" target="_blank" rel="noopener noreferrer">公式の登録手順を開く ↗</a></li>
   <li><h3>「Messaging API」を有効にする</h3><p>LINE Official Account Managerの「設定 → Messaging API → Messaging APIを利用する」へ進みます。管理するプロバイダーは後で変更できないため、MUUMEI用を選びます。</p></li>
   <li><h3>接続用の鍵をサーバーに登録する</h3><p>LINE Developersで取得するチャネルシークレットとチャネルアクセストークンを、MUUMEI専用Supabaseの「Edge Functions → Secrets」に設定します。鍵はこの画面やチャットには貼らないでください。</p><details><summary>設定する項目を見る</summary><dl className="line-setup-keys"><dt>LINE_CHANNEL_SECRET</dt><dd>対象チャネルの「チャネル基本設定」にあるシークレット。</dd><dt>LINE_CHANNEL_ACCESS_TOKEN</dt><dd>同じチャネルの「Messaging API設定」で発行するアクセストークン。</dd><dt>LINE_DESTINATION_ID</dt><dd>そのトークンでボット情報を取得した際のuserId（Uから始まる値）。「あなたのユーザーID」や「@から始まるID」とは別です。</dd></dl><p>本体とOWNERの許可URL・OWNERのメール認証も、接続作業の中で設定します。</p></details></li>
   <li><h3>LINEの送信先をMUUMEIにする</h3><p>LINE Developersの「Messaging API設定 → Webhook URL」に次のURLを入れ、秘密値の設定後に「検証」で成功を確認します。「Webhookの利用」と「Webhookの再送」を有効にします。</p><code className="line-webhook-url">{webhook}</code><Button secondary onClick={()=>void run(()=>navigator.clipboard.writeText(webhook),'Webhook URLをコピーしました')}>Webhook URLをコピー</Button><p className="muted">自動応答メッセージを併用する場合は、手動返信と重複しない内容に調整します。</p></li>
   <li><h3>1人と送受信を試す</h3><p>テストに協力する相手に公式アカウントを友だち追加してもらい、LINEからメッセージと写真を送ってもらいます。あなたはLINE受信箱で受け取り、返信と写真・PDFを送り返します。</p><p>名前とアイコンは「LINE受信箱 → 名前・アイコン設定」で変更できます。PDFなどは7日間有効のリンクで届きます。トーク一覧には公式アカウントの名前とアイコンが表示されます。</p></li>
  </ol>
  <p className="muted">個人LINEの過去のトークや友だち一覧が自動で移る仕組みではありません。相手との1対1の連絡に利用します。</p>
 </section>;
}
