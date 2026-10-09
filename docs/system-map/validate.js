// Checks every id referenced in data.js exists. Run: node docs/system-map/validate.js
const fs=require('fs'); const vm=require('vm');
const code=fs.readFileSync(__dirname+'/data.js','utf8')+'\n;MAP';
const MAP=vm.runInNewContext(code);
const ids=new Set([...MAP.groups.map(g=>g.id),...MAP.nodes.map(n=>n.id)]);
let bad=0; const chk=(id,where)=>{ if(!ids.has(id)){ console.log('MISSING',id,'in',where); bad++; } };
MAP.nodes.forEach(n=>{ if(!MAP.groups.find(g=>g.id===n.group)){ console.log('node without group',n.id); bad++; } (n.touches||[]).forEach(t=>chk(t,'touches of '+n.id)); (n.flags||[]).forEach(f=>{ if(!MAP.flags.find(x=>x.id===f)){ console.log('unknown flag',f,'on',n.id); bad++; } }); });
MAP.edges.forEach(e=>{ chk(e.from,'edge'); chk(e.to,'edge'); });
MAP.steps.forEach((s,i)=>{ (s.focus||[]).forEach(f=>chk(f,'step '+i)); (s.edges||[]).forEach(k=>{ const [a,b]=[k.split('-')[0],k.split('-').slice(1).join('-')]; if(!MAP.edges.find(e=>e.from===a&&e.to===b)){ console.log('step',i,'edge not found',k); bad++; } }); });
MAP.flags.forEach(f=>(f.nodes||[]).forEach(n=>chk(n,'flag '+f.id)));
const used=new Set(MAP.nodes.flatMap(n=>n.flags||[])); MAP.flags.forEach(f=>{ if(!used.has(f.id)) console.log('note: flag',f.id,'not attached to any node.flags (still linked via flag.nodes)'); });
console.log(`${MAP.groups.length} groups, ${MAP.nodes.length} nodes, ${MAP.edges.length} edges, ${MAP.steps.length} steps, ${MAP.flags.length} flags; ${bad} problems`);
process.exit(bad?1:0);
