
import {SQL} from "bun";
if(!Bun.env.DATABASE_URL)throw Error("DATABASE_URL required");
const db=new SQL(Bun.env.DATABASE_URL);
await db`CREATE TABLE IF NOT EXISTS radar_r22_crossrefs(
 source_document_id TEXT NOT NULL,edge_hash TEXT NOT NULL,
 referenced_document_id TEXT,reference_crfn TEXT,
 reference_reel_year TEXT,reference_reel_number TEXT,
 source_raw JSONB NOT NULL,source_url TEXT NOT NULL,
 checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 PRIMARY KEY(source_document_id,edge_hash))`;
await db`CREATE INDEX IF NOT EXISTS radar_r22_ref_target_idx ON radar_r22_crossrefs(referenced_document_id)`;
await db`CREATE TABLE IF NOT EXISTS radar_r22_remarks(
 document_id TEXT NOT NULL,sequence_number INT NOT NULL,
 remark_text TEXT NOT NULL,source_url TEXT NOT NULL,
 checked_at TIMESTAMPTZ DEFAULT NOW(),PRIMARY KEY(document_id,sequence_number))`;
await db`CREATE TABLE IF NOT EXISTS radar_r22_refchecks(
 document_id TEXT PRIMARY KEY,crossref_count INT NOT NULL DEFAULT 0,
 remark_count INT NOT NULL DEFAULT 0,
 source_complete BOOLEAN NOT NULL DEFAULT FALSE,
 error_text TEXT,checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW())`;
await db`CREATE TABLE IF NOT EXISTS radar_r22_facility_research(
 bbl TEXT PRIMARY KEY REFERENCES radar_r22_dossiers(bbl),
 explicit_ref_edges INT NOT NULL DEFAULT 0,
 referenced_doc_ids_matched INT NOT NULL DEFAULT 0,
 documents_without_refcheck INT NOT NULL DEFAULT 0,
 potential_family_status TEXT NOT NULL DEFAULT 'LINKAGE_NOT_ESTABLISHED',
 current_facility_notional NUMERIC,current_payoff NUMERIC,
 actual_maturity DATE,verified_debt_terms BOOLEAN NOT NULL DEFAULT FALSE,
 updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())`;
const pick=await db`SELECT e.bbl,e.document_id,e.doc_type,e.recorded_datetime
 FROM radar_r22_document_events e
 LEFT JOIN radar_r22_refchecks c ON c.document_id=e.document_id
 WHERE c.document_id IS NULL
  OR (c.source_complete=false AND c.checked_at<NOW()-INTERVAL '12 hours')
 ORDER BY CASE WHEN e.is_2020_22_vintage THEN 0
  WHEN upper(e.doc_type) IN ('SAT','SATM','ASST','AGMT','CEMA','MMOD','MCON') THEN 1
  ELSE 2 END,e.recorded_datetime DESC NULLS LAST,e.document_id
 LIMIT 40`;
const sleep=(ms:number)=>new Promise(r=>setTimeout(r,ms));
const pull=async(table:string,id:string)=>{
 const url=new URL("https://data.cityofnewyork.us/resource/"+table+".json");
 url.searchParams.set("document_id",id);
 url.searchParams.set("$limit","1001");
 let problem="";
 for(let i=0;i<3;i++){
  try{
   const res=await fetch(url,{headers:{Accept:"application/json"},signal:AbortSignal.timeout(20000)});
   if(res.ok){const rows=await res.json();if(!Array.isArray(rows))throw Error("non-array");return rows}
   problem="HTTP "+res.status;
   if(res.status!==429&&res.status<500)break;
  }catch(err:any){problem=String(err.message)}
  await sleep(600*(i+1));
 }
 throw Error(problem||"source unavailable");
};
let passed=0,fail=0,totalRefs=0,totalRemarks=0,matched=0;
for(const doc of pick){
 const id=String(doc.document_id);
 try{
  if(!/^[A-Za-z0-9_-]{1,80}$/.test(id))throw Error("Invalid document id");
  const refs=await pull("pwkr-dpni",id);
  const remarks=await pull("9p4w-7npp",id);
  const complete=refs.length<1001&&remarks.length<1001;
  for(const x of refs){
   const payload=JSON.stringify(x);
   const sha=new Bun.CryptoHasher("sha256");sha.update(payload);
   const hash=sha.digest("hex");
   const target=String(x.reference_by_doc_id??"").trim();
   const crfn=String(x.reference_by_crfn_??"").trim();
   await db`INSERT INTO radar_r22_crossrefs(source_document_id,edge_hash,referenced_document_id,
     reference_crfn,reference_reel_year,reference_reel_number,source_raw,source_url,checked_at)
     VALUES(${id},${hash},${target||null},${crfn||null},
     ${x.reference_by_reel_year??null},${x.reference_by_reel_nbr??null},
     ((${payload}::jsonb #>> '{}')::jsonb),
     'https://data.cityofnewyork.us/resource/pwkr-dpni.json',NOW())
     ON CONFLICT(source_document_id,edge_hash) DO UPDATE SET checked_at=NOW()`;
   totalRefs++;
   if(target&&await db`SELECT 1 FROM radar_acris_documents WHERE document_id=${target} LIMIT 1`.then(a=>a.length>0))matched++;
  }
  for(const x of remarks){
   const n=Number(x.sequence_number);
   if(!Number.isInteger(n)||n<0||n>10000)continue;
   await db`INSERT INTO radar_r22_remarks(document_id,sequence_number,remark_text,source_url)
     VALUES(${id},${n},${String(x.remark_text??"")},'https://data.cityofnewyork.us/resource/9p4w-7npp.json')
     ON CONFLICT(document_id,sequence_number) DO UPDATE SET remark_text=EXCLUDED.remark_text,checked_at=NOW()`;
   totalRemarks++;
  }
  await db`INSERT INTO radar_r22_refchecks(document_id,crossref_count,remark_count,source_complete,checked_at)
    VALUES(${id},${refs.length},${remarks.length},${complete},NOW())
    ON CONFLICT(document_id) DO UPDATE SET crossref_count=EXCLUDED.crossref_count,
      remark_count=EXCLUDED.remark_count,source_complete=EXCLUDED.source_complete,error_text=NULL,checked_at=NOW()`;
  passed++;
 }catch(err:any){
  fail++;
  await db`INSERT INTO radar_r22_refchecks(document_id,source_complete,error_text,checked_at)
    VALUES(${id},false,${String(err.message).slice(0,500)},NOW())
    ON CONFLICT(document_id) DO UPDATE SET source_complete=false,error_text=EXCLUDED.error_text,checked_at=NOW()`;
  console.error(JSON.stringify({event:"r22_ref_document_failed",id,error:String(err.message)}));
 }
}
await db`INSERT INTO radar_r22_facility_research(bbl,explicit_ref_edges,referenced_doc_ids_matched,
 documents_without_refcheck,potential_family_status,updated_at)
 SELECT d.bbl,
 (SELECT COUNT(*)::int FROM radar_r22_crossrefs r JOIN radar_r22_document_events ev
   ON ev.document_id=r.source_document_id WHERE ev.bbl=d.bbl),
 (SELECT COUNT(*)::int FROM radar_r22_crossrefs r JOIN radar_r22_document_events ev
    ON ev.document_id=r.source_document_id
    WHERE ev.bbl=d.bbl AND r.referenced_document_id IN (SELECT document_id FROM radar_acris_documents)),
 (SELECT COUNT(*)::int FROM radar_r22_document_events ev LEFT JOIN radar_r22_refchecks c
   ON c.document_id=ev.document_id WHERE ev.bbl=d.bbl AND c.document_id IS NULL),
 'REFERENCES_FOUND_FACILITY_REQUIRES_LEGAL_REVIEW',NOW()
 FROM radar_r22_dossiers d
 ON CONFLICT(bbl) DO UPDATE SET explicit_ref_edges=EXCLUDED.explicit_ref_edges,
 referenced_doc_ids_matched=EXCLUDED.referenced_doc_ids_matched,
 documents_without_refcheck=EXCLUDED.documents_without_refcheck,updated_at=NOW()`;
const audit=await db`SELECT
 (SELECT COUNT(*)::int FROM radar_r22_dossiers) AS dossiers,
 (SELECT COUNT(*)::int FROM radar_r22_refchecks WHERE source_complete) AS checked,
 (SELECT COUNT(*)::int FROM radar_r22_crossrefs) AS crossrefs,
 (SELECT COUNT(*)::int FROM radar_r22_remarks) AS remarks,
 (SELECT COUNT(*)::int FROM radar_r22_facility_research) AS facility_research_rows`;
console.log(JSON.stringify({event:"r22_crossreference_acceptance",attempted:pick.length,passed,failed:fail,
 added_crossref_rows:totalRefs,added_remark_rows:totalRemarks,
 references_to_loaded_documents:matched,coverage:audit[0],
 caveat:"Recorded cross-references are not confirmation of a single current loan facility or satisfied debt."}));
await db.close();
if(fail)process.exitCode=1;
