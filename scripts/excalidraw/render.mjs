import { chromium } from 'playwright';
import os from 'os'; import fs from 'fs'; import path from 'path';
import diagrams from './diagrams.mjs';
const out = process.argv[2]; fs.mkdirSync(out+'/src',{recursive:true}); fs.mkdirSync(out+'/exports',{recursive:true});
const b = await chromium.launch({...(process.env.CHROME_PATH ? {executablePath: process.env.CHROME_PATH} : {})});
const p = await b.newPage();
p.on('pageerror', e=>console.log('err:', e.message.slice(0,300)));
await p.goto('file://'+process.cwd()+'/page.html');
await p.waitForFunction('window.ready===true',null,{timeout:90000});
for (const d of diagrams) {
  const r = await p.evaluate(async(skel)=>{
    const Ex = window.Ex;
    const els = Ex.convertToExcalidrawElements(skel.map(e=>({strokeColor:'#1e1e1e',backgroundColor:'transparent',fillStyle:'solid',strokeWidth:2,roughness:1,...e})), {regenerateIds:false});
    const appState = {exportBackground:true, viewBackgroundColor:'#ffffff', exportWithDarkMode:false};
    const svg = await Ex.exportToSvg({elements:els, appState, files:null, exportPadding:24});
    const blob = await Ex.exportToBlob({elements:els, appState, files:null, mimeType:'image/png', exportPadding:24, getDimensions:(w,h)=>({width:w*2,height:h*2,scale:2})});
    const png = await new Promise(res=>{const fr=new FileReader();fr.onload=()=>res(fr.result.split(',')[1]);fr.readAsDataURL(blob);});
    const scene = {type:'excalidraw',version:2,source:'https://excalidraw.com',elements:els,appState:{viewBackgroundColor:'#ffffff',gridSize:null},files:{}};
    return {svg: svg.outerHTML, png, scene: JSON.stringify(scene,null,2)};
  }, d.els);
  fs.writeFileSync(`${out}/src/${d.name}.excalidraw`, r.scene);
  fs.writeFileSync(`${out}/exports/${d.name}.svg`, r.svg);
  fs.writeFileSync(`${out}/exports/${d.name}.png`, Buffer.from(r.png,'base64'));
  console.log('rendered', d.name);
}
await b.close();
