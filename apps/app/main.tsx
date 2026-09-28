import React,{Suspense} from 'react';import{createRoot}from'react-dom/client';import App from './components/muumei/app';import './app/globals.css';import './app/photo-theme.css';
createRoot(document.getElementById('root')!).render(<Suspense fallback={<p role="status">読み込み中…</p>}><App path={location.pathname}/></Suspense>);
