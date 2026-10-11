
import {SQL} from "bun";
if(!Bun.env.DATABASE_URL)throw Error("DATABASE_URL required");
const db=new SQL(Bun.env.DATABASE_URL);
const base="https://data.cityofnewyork.us/resource/";
const delay=(ms:number)=>new Promise(resolve=>setTimeout(resolve,ms));
async function read(dataset:string,params:Record<string,string>){
 const u=new URL(base+dataset+".json");for(const [k,v] of Object.entries(params))u.searchParams.set(k,v);
 let err="";
 for(let attempt=0;attempt<4;attempt++){
  try{
   const r=await fetch(u,{headers:{Accept:"application/json",...(Bun.env.SOCRATA_APP_TOKEN?{"X-App-Token":Bun.env.SOCRATA_APP_TOKEN}:{})},signal:AbortSignal.timeout(25000)});
   if(r.ok){const rows=await r.json();if(!Array.isArray(rows))throw Error("Unexpected source response");return rows}
   err="HTTP "+r.status;if(r.status!==429&&r.status<500)break;
  }catch(e:any){err=String(e.message)}
  await delay(500*(attempt+1)**2);
 }throw Error(dataset+" "+err);
}
await db`CREATE TABLE IF NOT EXISTS radar_b_large_instrument_repair_runs(
 id BIGSERIAL PRIMARY KEY,bbl TEXT NOT NULL,status TEXT NOT NULL,
 pages_fetched INT NOT NULL DEFAULT 0,new_legal_document_rows INT NOT NULL DEFAULT 0,
 loaded_master_rows INT NOT NULL DEFAULT 0,
 missing_master_rows INT NOT NULL DEFAULT 0,
 error_message TEXT,finished_at TIMESTAMPTZ DEFAULT NOW())`;
const cases=await db`SELECT a.bbl,a.status,a.source_pages,a.legal_count,a.master_count,p.borough,p.block,p.lot
 FROM radar_acris_universe_attempts a JOIN radar_properties p ON p.bbl=a.bbl
 WHERE a.status='partial' AND p.borough IN('MN','BK')
 ORDER BY a.checked_at,bbl LIMIT 2`;
let processed=0,completed=0,partial=0,failed=0;
for(const caseRow of cases){
 const bbl=String(caseRow.bbl),boro=caseRow.borough==="MN"?"1":"3";
 let added=0,master=0,pages=0,missing=0;
 try{
  const found=new Set<string>();
  let pageComplete=false,after=0;
  const initial=caseRow.source_pages>=5?Math.min(1500,Math.max(0,Number(caseRow.source_pages)-1)*300):0;
  for(let offset=initial;offset<=14700;offset+=300){
   const rows=await read("8h5j-fqxa",{borough:boro,block:String(caseRow.block),
     lot:String(caseRow.lot),"$limit":"300","$offset":String(offset),"$order":"document_id"});
   pages++;after=offset;
   for(const x of rows){
    const id=String(x.document_id||"");
    if(!/^[A-Za-z0-9_-]{1,80}$/.test(id))continue;
    found.add(id);
    const raw=JSON.stringify(x);
    await db`INSERT INTO radar_acris_universe_legals(
     bbl,document_id,borough,good_through_date,property_type,record_type,raw,source_url,seen_at)
     VALUES(${bbl},${id},${caseRow.borough},${x.good_through_date??null},
       ${x.property_type??null},${x.record_type??null},
       ((${raw}::jsonb #>> '{}')::jsonb),'https://data.cityofnewyork.us/resource/8h5j-fqxa.json',NOW())
     ON CONFLICT(bbl,document_id) DO UPDATE SET raw=EXCLUDED.raw,seen_at=NOW()`;
    added++;
   }
   if(rows.length<300){pageComplete=true;break}
  }
  const needs=await db`SELECT l.document_id FROM radar_acris_universe_legals l
   LEFT JOIN radar_acris_documents d ON d.document_id=l.document_id
   WHERE l.bbl=${bbl} AND d.document_id IS NULL ORDER BY l.document_id`;
  for(let i=0;i<needs.length;i+=50){
   const batch=needs.slice(i,i+50).map((x:any)=>String(x.document_id));
   const where="document_id in ("+batch.map(x=>"'"+x+"'").join(",")+")";
   const rows=await read("bnx9-e6tj",{"$where":where,"$limit":"1000"});
   for(const x of rows){
    const id=String(x.document_id);
    if(!batch.includes(id))continue;
    const amt=x.document_amt==null?null:Number(x.document_amt);
    const raw=JSON.stringify(x);
    await db`INSERT INTO radar_acris_documents(
      document_id,doc_type,document_amt,recorded_datetime,raw,source_url,last_seen)
      VALUES(${id},${x.doc_type??null},${Number.isFinite(amt)?amt:null},
       ${x.recorded_datetime??null},((${raw}::jsonb #>> '{}')::jsonb),
       'https://data.cityofnewyork.us/resource/bnx9-e6tj.json',NOW())
      ON CONFLICT(document_id) DO UPDATE SET doc_type=EXCLUDED.doc_type,
       document_amt=EXCLUDED.document_amt,recorded_datetime=EXCLUDED.recorded_datetime,
       raw=EXCLUDED.raw,last_seen=NOW()`;
    await db`INSERT INTO radar_collateral_links(document_id,bbl) VALUES(${id},${bbl})
      ON CONFLICT DO NOTHING`;
    master++;
   }
  }
  const total=await db`SELECT COUNT(*)::int AS legal_documents,
    COUNT(d.document_id)::int AS linked_masters,
    COUNT(*) FILTER(WHERE d.document_id IS NULL)::int AS missing_masters
   FROM radar_acris_universe_legals l
   LEFT JOIN radar_acris_documents d ON d.document_id=l.document_id
   WHERE l.bbl=${bbl}`;
  missing=total[0].missing_masters;
  const good=pageComplete&&missing===0;
  await db`UPDATE radar_acris_universe_attempts SET status=${good?'success':'partial'},
    legal_count=${total[0].legal_documents},master_count=${total[0].linked_masters},
    source_pages=${Math.max(Number(caseRow.source_pages)||0,Math.floor(after/300)+1)},
    truncated=${!pageComplete},checked_at=NOW(),
    error_text=${good?null:!pageComplete?"More than 15000 source rows":missing+" Master documents missing"}
   WHERE bbl=${bbl}`;
  await db`INSERT INTO radar_b_large_instrument_repair_runs(
   bbl,status,pages_fetched,new_legal_document_rows,loaded_master_rows,missing_master_rows)
   VALUES(${bbl},${good?'COMPLETE':'PARTIAL'},${pages},${added},${master},${missing})`;
  processed++;if(good)completed++;else partial++;
  console.log(JSON.stringify({event:"milestone_b_deep_pagination_record",bbl,source_pages:pages,
    legal_upserts:added,master_loaded:master,remaining_missing:missing,
    complete:good,total_documents:total[0].legal_documents,
    caveat:"Completeness refers only to indexed ACRIS source rows, not signed instrument text."}));
 }catch(e:any){
  processed++;failed++;
  await db`INSERT INTO radar_b_large_instrument_repair_runs(
   bbl,status,pages_fetched,new_legal_document_rows,loaded_master_rows,missing_master_rows,error_message)
   VALUES(${bbl},'ERROR',${pages},${added},${master},${missing},${String(e.message).slice(0,500)})`;
  console.error(JSON.stringify({event:"milestone_b_deep_pagination_error",bbl,error:String(e.message)}));
 }
}
console.log(JSON.stringify({event:"milestone_b_partial_collection_repair",processed,completed,partial,failed}));
await db.close();
if(failed)process.exitCode=1;
