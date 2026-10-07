import { chromium } from 'playwright'; import os from 'os'; import fs from 'fs';
const dir = process.argv[2];
const b = await chromium.launch({...(process.env.CHROME_PATH ? {executablePath: process.env.CHROME_PATH} : {})});
const p = await b.newPage(); await p.goto('file://'+process.cwd()+'/page.html'); await p.waitForFunction('window.ready===true',null,{timeout:90000});
for (const f of fs.readdirSync(dir+'/src')) {
  const scene = fs.readFileSync(`${dir}/src/${f}`,'utf8');
  const r = await p.evaluate(async(txt)=>{
    const data = JSON.parse(txt); const els = window.Ex.restoreElements(data.elements, null);
    const svg = await window.Ex.exportToSvg({elements:els, appState:{exportBackground:true,viewBackgroundColor:'#ffffff'}, files:null, exportPadding:24});
    const texts = els.filter(e=>e.type==='text').map(e=>e.text);
    const arrows = els.filter(e=>e.type==='arrow'); const bound = arrows.filter(a=>a.startBinding&&a.endBinding).length;
    return {viewBox: svg.getAttribute('viewBox'), texts, arrows: arrows.length, bound};
  }, scene);
  const exported = fs.readFileSync(`${dir}/exports/${f.replace('.excalidraw','.svg')}`,'utf8').match(/viewBox="([^"]+)"/)[1];
  console.log(f, r.viewBox===exported?'viewBox OK':'viewBox DIFF', `arrows ${r.bound}/${r.arrows} bound`, r.texts.join(' | '));
}
await b.close();
