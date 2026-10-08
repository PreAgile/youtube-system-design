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
   E('rdb',770,0,'RDB'), E('store',770,200,'S3'),
   A('client','api',150,135,300,0,'all bytes'),
   A('api','rdb',600,120,170,-75,'metadata'),
   A('api','store',600,150,170,85,'video file'),
 ]},
 {name:'step1-upload', els:[
   R('client',0,100,'Client'), R('api',340,0,'API'),
   E('rdb',680,-5,'RDB'), E('store',340,220,'S3'),
   A('client','api',150,115,190,-70,'control'),
   A('client','store',150,150,190,105,'chunks'),
   A('api','rdb',490,35,190,0,'session'),
   A('api','store',415,70,0,150,'check'),
 ]},
 {name:'step2-processing', els:[
   R('client',0,100,'Client'), R('api',340,0,'API'),
   E('rdb',700,-5,'RDB'), E('store',340,240,'S3'), R('worker',700,240,'Worker'),
   A('client','api',150,115,190,-70,'upload ctl / poll'),
   A('client','store',150,150,190,115,'chunks'),
   A('api','rdb',490,35,210,0,'jobs'),
   A('worker','rdb',775,240,0,-165,'lease'),
   A('worker','store',700,280,-210,0,'segments'),
 ]},
 {name:'step3-playback', els:[
   R('client',0,100,'Client'), R('api',340,0,'API'),
   E('rdb',700,-5,'RDB'), E('store',340,240,'S3'), R('worker',700,240,'Worker'),
   A('client','api',150,115,190,-70,'playback info'),
   A('client','store',150,150,190,115,'manifest / segments'),
   A('api','rdb',490,35,210,0),
   A('worker','rdb',775,240,0,-165),
   A('worker','store',700,280,-210,0,'segments'),
 ]},
 {name:'step4-global', els:[
   R('client',0,140,'Client'), C('cdn',300,120,'CDN'), R('regional',560,140,'Regional cache',190),
   R('api',840,0,'API'), E('store',840,240,'S3'),
   E('rdb',1140,-5,'RDB'), R('worker',1140,240,'Worker'),
   A('client','cdn',150,175,150,0,'GET'),
   A('cdn','regional',410,175,150,0,'miss'),
   A('regional','api',750,155,90,-100,'info'),
   A('regional','store',750,195,90,85,'files'),
   A('api','rdb',990,35,150,0),
   A('worker','rdb',1215,240,0,-165),
   A('worker','store',1140,280,-150,0),
 ]},
 {name:'step5-global-upload', els:[
   R('client',0,140,'Client'), R('edge',340,140,'Edge'),
   R('api',700,0,'API'), E('rdb',1010,-5,'RDB'), E('store',700,270,'S3'),
   A('client','edge',150,175,190,0,'chunks x N'),
   A('edge','store',490,195,210,110,'backbone'),
   A('client','api',150,150,550,-100,'control'),
   A('api','rdb',850,35,160,0,'session'),
   A('api','store',775,70,0,200,'check'),
 ]},
 {name:'final-overview', els:[
   R('client',0,300,'Client'), R('edge',330,40,'Edge'), E('store',900,35,'S3',170,80),
   R('worker',1220,40,'Worker'), R('api',900,300,'API'), E('rdb',1220,295,'RDB'),
   C('cdn',330,500,'CDN'), R('regional',600,520,'Regional cache',190),
   A('client','edge',150,315,180,-225,'chunks'),
   A('edge','store',480,75,420,0,'backbone'),
   A('client','api',150,335,750,0,'control / poll'),
   A('api','store',975,300,0,-185,'check'),
   A('api','rdb',1050,335,170,0,'state'),
   A('worker','rdb',1295,110,0,185,'lease'),
   A('worker','store',1220,75,-150,0,'segments'),
   A('client','cdn',150,360,200,160,'GET'),
   A('cdn','regional',440,555,160,0,'miss'),
   A('regional','api',790,540,150,-170,'info'),
   A('regional','store',700,520,220,-405,'files'),
 ]},
];
