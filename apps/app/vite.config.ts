import {defineConfig,loadEnv} from 'vite';
import react from '@vitejs/plugin-react';
import {readFileSync} from 'node:fs';
import {fileURLToPath,URL} from 'node:url';
import {createPublicConfig,publicNames,staticHeaders,staticRedirects} from '../../scripts/public-config.mjs';

export default defineConfig(({mode})=>{
  const root=fileURLToPath(new URL('.',import.meta.url));
  const portable=mode==='static';
  const defaults=portable?JSON.parse(readFileSync(new URL('./wrangler.jsonc',import.meta.url),'utf8')).vars:{};
  const config=portable?createPublicConfig({...defaults,...loadEnv(mode,root,publicNames)}):null;
  return {
    plugins:[react(),...(portable?[{
      name:'muumei-static-config',
      generateBundle(this:{emitFile:(asset:{type:'asset';fileName:string;source:string})=>unknown}){
        this.emitFile({type:'asset',fileName:'muumei-config.json',source:JSON.stringify(config,null,2)+'\n'});
        this.emitFile({type:'asset',fileName:'_headers',source:staticHeaders});
        this.emitFile({type:'asset',fileName:'_redirects',source:staticRedirects});
      },
    }]:[])],
    define:{__MUUMEI_CONFIG_PATH__:JSON.stringify(portable?'/muumei-config.json':'/api/config')},
    resolve:{alias:{'@':root}},
    build:{outDir:portable?'dist-static':'dist',emptyOutDir:true},
    server:{host:'127.0.0.1'},
  };
});
