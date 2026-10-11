
import {SQL} from "bun";
if(!Bun.env.DATABASE_URL)throw Error("DATABASE_URL required");
const db=new SQL(Bun.env.DATABASE_URL);
const sleep=(ms:number)=>new Promise(resolve=>setTimeout(resolve,ms));
async function source(table:string,id:string){
 const u=new URL("https://data.cityofnewyork.us/resource/"+table+".json");
 u.searchParams.set("document_id",id);u.searchParams.set("$limit","1001");
 let last="";
 for(let retry=0;retry<3;retry++){
  try{
   const r=await fetch(u,{headers:{"Accept":"application/json",...(Bun.env.SOCRATA_APP_TOKEN?{"X-App-Token":Bun.env.SOCRATA_APP_TOKEN}:{})},signal:AbortSignal.timeout(18000)});
   if(r.ok){const rows=await r.json();if(!Array.isArray(rows))throw Error("invalid source response");return rows}
   last="HTTP "+r.status;if(r.status!==429&&r.status<500)break;
  }catch(e:any){last=String(e.message)}
  await sleep(350*(retry+1));
 }
 throw Error(table+" "+last);
}
await db`CREATE TABLE IF NOT EXISTS radar_b_document_source_checks(
 document_id TEXT PRIMARY KEY REFERENCES radar_acris_documents(document_id),
 all_legals_recorded BOOLEAN NOT NULL DEFAULT FALSE,
 all_parties_recorded BOOLEAN NOT NULL DEFAULT FALSE,
 raw_legal_rows INT,raw_party_rows INT,
 source_status TEXT NOT NULL DEFAULT 'PENDING',
 checked_at TIMESTAMPTZ,source_error TEXT)`;
const docs=await db`SELECT DISTINCT e.document_id
 FROM radar_r22_document_events e
 LEFT JOIN radar_b_document_source_checks x ON x.document_id=e.document_id
 WHERE x.document_id IS NULL OR
 (x.source_status IN ('ERROR','PARTIAL') AND x.checked_at<NOW()-INTERVAL '6 hours')
 ORDER BY e.document_id LIMIT 35`;
let complete=0,partial=0,failed=0,legals=0,parties=0;
for(const d of docs){
 const id=String(d.document_id);
 if(!/^[A-Za-z0-9_-]{1,80}$/.test(id)){failed++;continue;}
 try{
  const [legal,party]=await Promise.all([source("8h5j-fqxa",id),source("636b-3b5g",id)]);
  const legalComplete=legal.length<1001,partyComplete=party.length<1001;
  let badLot=0;
  const bbls=new Set<string>();
  for(const row of legal){
   const b=Number(row.borough),block=Number(row.block),lot=Number(row.lot);
   if(![1,2,3,4,5].includes(b)||!Number.isInteger(block)||!Number.isInteger(lot)||
    block<1||lot<1||block>99999||lot>9999){badLot++;continue}
   const bbl=String(b)+String(block).padStart(5,"0")+String(lot).padStart(4,"0");
   bbls.add(bbl);
   const raw=JSON.stringify(row);
   await db`INSERT INTO radar_acris_collateral_lots(document_id,bbl,partial_lot,property_type,
       source_raw,source_url)
    VALUES(${id},${bbl},${row.partial_lot??null},${row.property_type??null},
       ((${raw}::jsonb #>> '{}')::jsonb),'https://data.cityofnewyork.us/resource/8h5j-fqxa.json')
    ON CONFLICT(document_id,bbl) DO UPDATE SET source_raw=EXCLUDED.source_raw,seen_at=NOW()`;
  }
  for(const row of party){
   const raw=JSON.stringify(row),hash=new Bun.CryptoHasher("sha256");
   hash.update(raw);const key=hash.digest("hex");
   await db`INSERT INTO radar_acris_party_evidence(document_id,row_hash,party_type,party_name,
       source_raw,source_url)
    VALUES(${id},${key},${row.party_type??null},${row.name??null},
       ((${raw}::jsonb #>> '{}')::jsonb),'https://data.cityofnewyork.us/resource/636b-3b5g.json')
    ON CONFLICT(document_id,row_hash) DO UPDATE SET seen_at=NOW(),source_raw=EXCLUDED.source_raw`;
  }
  const trueComplete=legalComplete&&partyComplete&&badLot===0;
  const status=trueComplete?"COMPLETE":"PARTIAL";
  await db`INSERT INTO radar_b_document_source_checks(document_id,all_legals_recorded,
      all_parties_recorded,raw_legal_rows,raw_party_rows,source_status,checked_at,source_error)
   VALUES(${id},${legalComplete&&badLot===0},${partyComplete},${legal.length},${party.length},
      ${status},NOW(),${badLot?"Malformed legal BBL rows "+badLot:null})
   ON CONFLICT(document_id) DO UPDATE SET all_legals_recorded=EXCLUDED.all_legals_recorded,
    all_parties_recorded=EXCLUDED.all_parties_recorded,
    raw_legal_rows=EXCLUDED.raw_legal_rows,raw_party_rows=EXCLUDED.raw_party_rows,
    source_status=EXCLUDED.source_status,checked_at=NOW(),source_error=EXCLUDED.source_error`;
  await db`INSERT INTO radar_acris_collateral_scope(document_id,distinct_lots,scope_checked_at,scope_complete)
   VALUES(${id},${bbls.size},NOW(),${legalComplete&&badLot===0})
   ON CONFLICT(document_id) DO UPDATE SET distinct_lots=EXCLUDED.distinct_lots,
    scope_checked_at=NOW(),scope_complete=EXCLUDED.scope_complete`;
  legals+=legal.length;parties+=party.length;if(trueComplete)complete++;else partial++;
 }catch(err:any){
  failed++;
  await db`INSERT INTO radar_b_document_source_checks(document_id,source_status,checked_at,source_error)
   VALUES(${id},'ERROR',NOW(),${String(err.message).slice(0,600)})
   ON CONFLICT(document_id) DO UPDATE SET source_status='ERROR',checked_at=NOW(),source_error=EXCLUDED.source_error`;
  console.error(JSON.stringify({event:"milestone_b_document_evidence_error",document_id:id,error:String(err.message)}));
 }
}
const totals=await db`SELECT
 (SELECT COUNT(*)::int FROM radar_r22_document_events) AS dossier_events,
 (SELECT COUNT(*)::int FROM radar_b_document_source_checks WHERE source_status='COMPLETE') AS completed_documents,
 (SELECT COUNT(*)::int FROM radar_b_document_source_checks WHERE source_status='PARTIAL') AS partial_documents,
 (SELECT COUNT(*)::int FROM radar_b_document_source_checks WHERE source_status='ERROR') AS error_documents,
 (SELECT COUNT(DISTINCT e.document_id)::int FROM radar_r22_document_events e WHERE NOT EXISTS(
  SELECT 1 FROM radar_b_document_source_checks s WHERE s.document_id=e.document_id AND s.source_status='COMPLETE')) AS remaining,
 (SELECT COUNT(*)::int FROM radar_acris_party_evidence WHERE document_id IN
  (SELECT document_id FROM radar_r22_document_events)) AS recorded_party_rows,
 (SELECT COUNT(*)::int FROM radar_acris_collateral_scope WHERE document_id IN
  (SELECT document_id FROM radar_r22_document_events) AND distinct_lots>1) AS multi_lot_documents`;
console.log(JSON.stringify({event:"milestone_b_indexed_document_verification_batch",
 attempted:docs.length,complete,partial,failed,legal_source_rows:legals,party_source_rows:parties,
 totals:totals[0],semantics:"Party labels are recording-era metadata, not present-day creditor identification."}));
await db.close();
if(failed)process.exitCode=1;
