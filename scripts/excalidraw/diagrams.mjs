// Skeletons per design step. Shapes: rectangle = component, ellipse = data store, circle = CDN.
// 'Regional cache' = CDN mid-tier per region (e.g. AWS CloudFront Regional Edge Cache), not an origin shield.
const R=(id,x,y,t,w=150,h=70)=>({type:'rectangle',id,x,y,width:w,height:h,label:{text:t}});
const E=(id,x,y,t,w=150,h=80)=>({type:'ellipse',id,x,y,width:w,height:h,label:{text:t}});
const C=(id,x,y,t,d=110)=>({type:'ellipse',id,x,y,width:d,height:d,label:{text:t}});
// arrow between two element ids with explicit points
const A=(from,to,x,y,dx,dy,t,dashed=false)=>({type:'arrow',x,y,width:dx,height:dy,points:[[0,0],[dx,dy]],
  start:{id:from},end:{id:to},...(t?{label:{text:t}}:{}),...(dashed?{strokeStyle:'dashed'}:{})});

export default [
 {name:'step0-simplest', els:[
   R('client',0,100,'Client'), R('api',450,100,'API'),
   E('rdb',770,0,'RDB'), E('store',770,200,'Storage'),
   A('client','api',150,135,300,0,'all bytes'),
   A('api','rdb',600,120,170,-75,'metadata'),
   A('api','store',600,150,170,85,'video file'),
 ]},
 {name:'step1-upload', els:[
   R('client',0,100,'Client'), R('api',340,0,'API'),
   E('rdb',680,-5,'RDB'), E('store',340,220,'Storage'),
   A('client','api',150,115,190,-70,'control'),
   A('client','store',150,150,190,105,'chunks'),
   A('api','rdb',490,35,190,0,'session'),
   A('api','store',415,70,0,150,'check'),
 ]},
 {name:'step2-processing', els:[
   R('client',0,100,'Client'), R('api',340,0,'API'),
   E('rdb',700,-5,'RDB'), E('store',340,240,'Storage'), R('worker',700,240,'Worker'),
   A('client','api',150,115,190,-70,'upload ctl / poll'),
   A('client','store',150,150,190,115,'chunks'),
   A('api','rdb',490,35,210,0,'jobs'),
   A('worker','rdb',775,240,0,-165,'lease'),
   A('worker','store',700,280,-210,0,'segments'),
 ]},
 {name:'step3-playback', els:[
   R('client',0,100,'Client'), R('api',340,0,'API'),
   E('rdb',700,-5,'RDB'), E('store',340,240,'Storage'), R('worker',700,240,'Worker'),
   A('client','api',150,115,190,-70,'playback info'),
   A('client','store',150,150,190,115,'manifest / segments'),
   A('api','rdb',490,35,210,0),
   A('worker','rdb',775,240,0,-165),
   A('worker','store',700,280,-210,0,'segments'),
 ]},
 {name:'step4-global', els:[
   R('client',0,140,'Client'), C('cdn',300,120,'CDN'), R('regional',560,140,'Regional cache',190),
   R('api',840,0,'API'), E('store',840,240,'Storage'),
   E('rdb',1140,-5,'RDB'), R('worker',1140,240,'Worker'),
   A('client','cdn',150,175,150,0,'GET'),
   A('cdn','regional',410,175,150,0,'miss'),
   A('regional','api',750,155,90,-100,'info'),
   A('regional','store',750,195,90,85,'files'),
   A('api','rdb',990,35,150,0),
   A('worker','rdb',1215,240,0,-165),
   A('worker','store',1140,280,-150,0),
 ]},
];
