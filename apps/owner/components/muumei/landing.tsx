'use client';
import {useEffect} from 'react';
import {ArrowRight,ArrowUpRight,ChevronDown,ShieldCheck,MessageCircle,ScanLine,Check,Menu} from 'lucide-react';
import {brand} from '@/lib/brand';
import {useApp} from '@/lib/gateway';
import {Logo} from './ui';

const questions=[
 ['どんなサービスですか？','一緒に働いた人や知人とのつながりを残し、仕事の依頼やコミュニティに参加できるサービスです。運営者個人の仕事のお手伝い募集と、参加者との交流が中心です。'],
 ['招待がなくても登録できますか？','登録の申請ができます。プロフィールを入力し、運営者の確認・承認を受けてから、仕事やコミュニティを利用できます。'],
 ['アプリのインストールは必要ですか？','ブラウザからそのまま使えます。対応端末ではホーム画面に追加して、仕事やメッセージの通知を受け取ることもできます。'],
 ['タイミーの公式サービスですか？',brand.name+'は株式会社タイミーが提供する公式サービスではありません。スポットワークなどで生まれた縁をつなぐ、独立したサービスです。'],
 ['メンバー同士で個別に連絡できますか？','メンバー同士のDMはありません。みんなとの会話は掲示板で、仕事の相談や個別の連絡は運営者とのメッセージで行えます。'],
];
export function Landing(){
 const{config}=useApp();const ready=config.ready;const startHref=ready?'/join':'/demo/home';const startLabel=ready?brand.name+'をはじめる':'アプリを体験する';
 useEffect(()=>{
  if(!('IntersectionObserver'in window)||matchMedia('(prefers-reduced-motion: reduce)').matches)return;
  const observer=new IntersectionObserver(entries=>entries.forEach(e=>{if(e.isIntersecting){e.target.classList.add('is-visible');observer.unobserve(e.target)}}),{threshold:.08});
  document.querySelectorAll('.m-reveal').forEach(el=>{el.classList.add('will-reveal');observer.observe(el)});
  return()=>observer.disconnect();
 },[]);
 return <div className="marketing">
  <header className="m-header">
   <a href="/" aria-label={brand.name+' トップ'}><Logo/></a>
   <nav aria-label="サービス案内"><a href="#about">{brand.name}とは</a><a href="#how">使い方</a><a href="#questions">よくある質問</a></nav>
   <div className="m-header-actions"><a href="/login" className="m-login">ログイン</a><a href={startHref} className="m-button m-small">{ready?'はじめる':'体験する'} <ArrowRight size={16}/></a></div>
   <details className="m-mobile-menu"><summary aria-label="メニューを開く"><Menu size={23}/></summary><nav><a href="#about">{brand.name}とは</a><a href="#how">使い方</a><a href="/login">ログイン</a><a href="/invite">招待を受け取った方</a></nav></details>
  </header>
  <main id="main">
   <section className="m-hero m-photo-hero">
    <div className="m-hero-copy"><p className="m-kicker">人と仕事の、いいつづき。</p>{!ready&&<p className="m-launch-status">公開準備中 · 操作できる見本をご覧いただけます</p>}<h1>仕事で生まれた<br/>縁を、<span>次へ。</span></h1><p className="m-lead">ちょっと手を貸してほしい仕事も、<br/>また会いたい仲間とのつながりも。<br/>いつもの人と、次の「一緒に」へ。</p><div className="m-hero-actions"><a className="m-button" href={startHref}>{startLabel} <ArrowRight size={19}/></a><a className="m-invite" href="/invite">招待を受け取った方 <ArrowUpRight size={17}/></a></div><p className="m-quiet">{ready?'登録・プロフィール入力のあと、承認を経て利用できます。':'登録受付は準備中です。見本には架空のデータを使用しています。'}</p></div>
    <figure className="m-hero-photo"><img src="/images/work-together.webp" width="1536" height="1024" alt="机を囲み、暮らしの品を一緒に梱包する仲間たちのイメージ" fetchPriority="high"/><figcaption>ひとりで抱えず、いっしょに。</figcaption></figure>
   </section>
   <div className="m-intro-strip"><p>仕事が終わっても、<br className="m-mobile-break"/>つながりは、終わらない。</p><a href="#about" aria-label="サービス紹介へ"><ChevronDown size={20}/></a></div>
   <section className="m-about m-section m-reveal" id="about">
    <div className="m-section-label"><span>01</span><p>{brand.name}について</p></div>
    <div className="m-about-content"><h2>あの人と、<br/>もう一度、働けたら。</h2><div className="m-about-text"><p className="m-copy-large">今日だけ一緒に働いた人。<br/>名前だけ知っていた人。<br/>またお願いしたいと思った人。</p><p>「またね」で終わっていた出逢いに、つづきを。<br/>{brand.name}は、仕事で出逢った仲間や知人との縁を残し、<br className="m-desktop-break"/>次の仕事へつなぐサービスです。</p><p>いつもの職場の話をしたり、経験をプロフィールに残したり。<br className="m-desktop-break"/>あなたを知る人から、次の「お願い」が届きます。</p><a className="m-underlink" href="/demo/home">アプリを体験する <ArrowUpRight size={18}/></a></div></div>
   </section>
   <section className="m-entries m-section m-reveal" id="how">
    <div className="m-section-label"><span>02</span><p>あなたに合った、はじめ方</p></div><div className="m-section-heading"><h2>出逢い方は、それぞれ。<br/>つながる場所は、ここ。</h2><p>仕事で知り合った方も。<br/>知人や紹介からはじめる方も。</p></div>
    <div className="m-entry-grid">
     <article className="m-entry"><div className="m-entry-top"><span>仕事で出逢った方</span><small>SPOT</small></div><h3>あの職場の仲間と、<br/>またつながる。</h3><p>スポットワークをきっかけに出逢った方へ。職場の情報や経験を共有しながら、次の仕事へ。</p><ol><li>プロフィールを登録</li><li>CREWで仲間・職場とつながる</li><li>仕事の依頼を受け取る</li></ol><a href="/join?source=spotwork" className="m-entry-link">仕事のつながりから、はじめる <ArrowRight size={19}/></a></article>
     <article className="m-entry"><div className="m-entry-top"><span>知人・紹介・招待の方</span><small>DIRECT</small></div><h3>知っている人から、<br/>次の「お願い」。</h3><p>知人や紹介、直接の招待からはじめる方へ。あなたの経験や得意なことを、仕事につなげます。</p><ol><li>招待を受け取る・登録する</li><li>プロフィールを整える</li><li>仕事の依頼を受け取る</li></ol><a href="/join?source=direct" className="m-entry-link">紹介・招待から、はじめる <ArrowRight size={19}/></a></article>
    </div>
   </section>
   <section className="m-work m-section m-reveal" id="work"><div className="m-work-copy"><div className="m-section-label"><span>03</span><p>仕事を見つける</p></div><h2>自分に合う仕事を、<br/>知っている人と。</h2><p>日時も、場所も、報酬も。<br/>必要なことを確かめてから、参加を決められる。<br/>気になることは、運営者へ直接相談できます。</p><ul><li><Check size={18}/>依頼された仕事を、ひとつの画面で</li><li><Check size={18}/>持ち物や集合場所も、事前に確認</li><li><Check size={18}/>参加の確定や連絡は、お知らせに</li></ul><a className="m-button m-light" href="/demo/work">仕事の画面を見てみる <ArrowRight size={19}/></a></div><div className="m-work-sample"><div className="m-sample-head"><strong>あなたに届いている仕事</strong><span>画面の見本</span></div><article><div className="m-sample-category">物流・軽作業 <span>承認制</span></div><h3>いつものチームで。<br/>暮らしの雑貨を仕分ける仕事</h3><dl><div><dt>時間</dt><dd>9:00 – 12:00</dd></div><div><dt>エリア</dt><dd>サンプルエリアA</dd></div><div><dt>報酬</dt><dd>求人ごとにご案内</dd></div></dl><a href="/demo/work" className="m-sample-action">仕事の詳細を確認する <ArrowRight size={18}/></a></article><p>架空の求人を使った画面の見本です。報酬・交通費は、実際の求人ごとにご案内します。</p></div></section>
   <section className="m-trust m-section m-reveal"><div className="m-section-label"><span>04</span><p>安心して使うために</p></div><h2>人とのつながりだから、<br/>大切にしたいこと。</h2><div className="m-trust-grid">{[[ShieldCheck,'承認を経て、つながる','登録後に運営者が内容を確認。プロフィールの公開範囲も、自分で選べます。'],[MessageCircle,'仕事の相談は、運営者へ','個別の連絡は運営者との間で。メンバー同士のDMは設けていません。'],[ScanLine,'出逢いを、その場で残す','対面でQRを受け取るだけ。プロフィールの登録は、帰ってからでも大丈夫。']].map(([Icon,title,body],i)=>{const C=Icon as typeof ShieldCheck;return <article key={i}><C size={27} strokeWidth={1.5}/><h3>{String(title)}</h3><p>{String(body)}</p></article>})}</div><a className="m-underlink" href="/security">セキュリティへの取り組み <ArrowUpRight size={18}/></a></section>
   <section className="m-faq m-section m-reveal" id="questions"><div><div className="m-section-label"><span>05</span><p>よくある質問</p></div><h2>はじめる前に、<br/>気になること。</h2></div><div>{questions.map(([q,a])=><details key={q}><summary><span>{q}</span><ChevronDown size={19}/></summary><p>{!ready&&q==='招待がなくても登録できますか？'?'現在、登録受付は準備中です。受付開始後は招待がなくても申請でき、運営者の承認を経て利用できます。':a}</p></details>)}</div></section>
   <section className="m-final"><p>その出逢いに、つづきを。</p><h2>次の「一緒に」を、<br className="m-mobile-break"/>ここから。</h2><div><a className="m-button" href={startHref}>{startLabel} <ArrowRight size={19}/></a><a className="m-invite" href="/invite">招待を受け取った方 <ArrowUpRight size={17}/></a></div></section>
  </main>
  <footer className="m-footer"><div className="m-footer-top"><div><Logo/><p>{brand.tagline}</p></div><a href="/login" className="m-underlink">ログイン <ArrowUpRight size={17}/></a></div><nav>{[['about',brand.name+'とは'],['operator','運営情報'],['security','セキュリティ'],['rules','禁止事項'],['privacy','プライバシー'],['terms','利用規約'],['contact','通報・お問い合わせ'],['faq','よくある質問'],['app/install','アプリの使い方']].map(([path,label])=><a key={path} href={'/'+path}>{label}</a>)}</nav><div className="m-footer-bottom"><p>{brand.name}は株式会社タイミーが提供する公式サービスではありません。<br/>掲載写真はサービスの利用場面を表現したイメージです。</p><small>© {new Date().getFullYear()} {brand.name}</small></div></footer>
 </div>;
}
