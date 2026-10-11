
import {SQL} from "bun";
if(!Bun.env.DATABASE_URL)throw Error("DATABASE_URL required");
const db=new SQL(Bun.env.DATABASE_URL);
const datasets=[
 {name:"HPD_LL7_QUALIFIED_TRANSACTION",id:"8wi4-bsy4",lastKnown:1720},
 {name:"HPD_SPECULATION_WATCH_HISTORIC",id:"adax-9mit",lastKnown:797}
];
await db`CREATE TABLE IF NOT EXISTS radar_a_hpd_transaction_signals(
 source_name TEXT NOT NULL,record_key TEXT NOT NULL,bbl TEXT NOT NULL,
 crfn TEXT,grantee TEXT,deed_date DATE,recorded_price NUMERIC,
 raw JSONB NOT NULL,source_url TEXT NOT NULL,ingested_at TIMESTAMPTZ DEFAULT NOW(),
 PRIMARY KEY(source_name,record_key))`;
await db`CREATE INDEX IF NOT EXISTS radar_a_hpd_tx_bbl_idx ON radar_a_hpd_transaction_signals(bbl,source_name)`;
await db`CREATE TABLE IF NOT EXISTS radar_a_hpd_signal_import_runs(
 id BIGSERIAL PRIMARY KEY,source_name TEXT,source_rows INT,processed_rows INT,
 matched_candidates INT,completeness TEXT,
 error TEXT,completed_at TIMESTAMPTZ NOT NULL DEFAULT NOW())`;
await db`ALTER TABLE radar_a_regulation_review ADD COLUMN IF NOT EXISTS hpd_ll7_historic_transactions INT NOT NULL DEFAULT 0`;
await db`ALTER TABLE radar_a_regulation_review ADD COLUMN IF NOT EXISTS hpd_speculation_watch_historic INT NOT NULL DEFAULT 0`;
let errors=0;
for(const dataset of datasets){
 let sourceRows=0,processed=0,matchCount=0;
 try{
  const url=new URL("https://data.cityofnewyork.us/resource/"+dataset.id+".json");
  url.searchParams.set("$limit","5000");
  url.searchParams.set("$order","bbl ASC, deed_date ASC,crfn ASC");
  const r=await fetch(url,{signal:AbortSignal.timeout(50000),headers:{
    Accept:"application/json",...(Bun.env.SOCRATA_APP_TOKEN?{"X-App-Token":Bun.env.SOCRATA_APP_TOKEN}:{})}});
  if(!r.ok)throw Error("Source API HTTP "+r.status+" "+(await r.text()).slice(0,180));
  const rows:any[]=await r.json();
  if(!Array.isArray(rows))throw Error("Source not JSON array");
  sourceRows=rows.length;
  if(sourceRows>=5000)throw Error("Pagination cap reached");
  if(sourceRows<dataset.lastKnown)throw Error("Unexpected regression below published source total "+dataset.lastKnown);
  for(const x of rows){
   const borough=Number(x.boro),block=Number(x.block),lot=Number(x.lot);
   if(![1,2,3,4,5].includes(borough)||!Number.isSafeInteger(block)||
       !Number.isSafeInteger(lot)||block<1||lot<1||block>99999||lot>9999)
      throw Error("Malformed source BBL for "+dataset.id+": "+JSON.stringify({boro:x.boro,block:x.block,lot:x.lot}));
   const bbl=String(borough)+String(block).padStart(5,"0")+String(lot).padStart(4,"0");
   if(x.bbl!=null&&String(Math.floor(Number(x.bbl)))!==bbl)
     throw Error("Source BBL block/lot mismatch "+JSON.stringify({bbl,actual:x.bbl}));
   const raw=JSON.stringify(x);
   const hash=new Bun.CryptoHasher("sha256");hash.update(dataset.id+"|"+raw);
   const rowHash=hash.digest("hex");
   const price=x.price==null?null:Number(x.price);
   const dt=String(x.deed_date??"").slice(0,10);
   await db`INSERT INTO radar_a_hpd_transaction_signals(
    source_name,record_key,bbl,crfn,grantee,deed_date,recorded_price,raw,source_url,ingested_at)
    VALUES(${dataset.name},${rowHash},${bbl},${x.crfn==null?null:String(x.crfn)},${x.grantee??null},
    ${/^\d{4}-\d{2}-\d{2}$/.test(dt)?dt:null},${Number.isFinite(price)?price:null},
    ((${raw}::jsonb #>> '{}')::jsonb),${url.toString()},NOW())
    ON CONFLICT(source_name,record_key) DO UPDATE SET ingested_at=NOW()`;
   processed++;
  }
  const matched=await db`SELECT COUNT(DISTINCT t.bbl)::int AS candidate_lots
    FROM radar_a_hpd_transaction_signals t JOIN radar_asset_screen s ON s.bbl=t.bbl
    WHERE t.source_name=${dataset.name}`;
  matchCount=matched[0].candidate_lots;
  await db`INSERT INTO radar_a_hpd_signal_import_runs(
    source_name,source_rows,processed_rows,matched_candidates,completeness)
    VALUES(${dataset.name},${sourceRows},${processed},${matchCount},'ALL_SOURCE_ROWS_LOADED')`;
  console.log(JSON.stringify({event:"milestone_a_hpd_signal_source_imported",dataset:dataset.name,
    sourceRows,processed,matchedCandidates:matchCount,
    note:"Historic rent-regulated sales context only, not current rent status."}));
 }catch(err:any){
  errors++;
  await db`INSERT INTO radar_a_hpd_signal_import_runs(
    source_name,source_rows,processed_rows,matched_candidates,completeness,error)
    VALUES(${dataset.name},${sourceRows},${processed},${matchCount},'FAILED',${String(err.message).slice(0,500)})`;
  console.error(JSON.stringify({event:"milestone_a_hpd_signal_source_failed",dataset:dataset.name,error:String(err.message)}));
 }
}
if(errors===0){
 await db`UPDATE radar_a_regulation_review r SET
    hpd_ll7_historic_transactions=(SELECT COUNT(*)::int FROM radar_a_hpd_transaction_signals t
       WHERE t.bbl=r.bbl AND t.source_name='HPD_LL7_QUALIFIED_TRANSACTION'),
    hpd_speculation_watch_historic=(SELECT COUNT(*)::int FROM radar_a_hpd_transaction_signals t
       WHERE t.bbl=r.bbl AND t.source_name='HPD_SPECULATION_WATCH_HISTORIC')`;
 await db`INSERT INTO radar_a_evidence(bbl,evidence_type,source_record_id,source_url,
    evidence_interpretation,provenance,last_seen)
   SELECT t.bbl,t.source_name,'HPD_LL7:'||t.record_key,t.source_url,
     CASE WHEN t.source_name='HPD_SPECULATION_WATCH_HISTORIC'
       THEN 'Historical HPD Speculation Watch sale; not current distress or free-market status'
       ELSE 'Historical LL7 qualified sale of select rent-regulated multiple dwelling; not current unit status' END,
     jsonb_build_object('crfn',t.crfn,'deed_date',t.deed_date,'historic_sale_price',t.recorded_price),NOW()
   FROM radar_a_hpd_transaction_signals t JOIN radar_asset_screen s ON s.bbl=t.bbl
   ON CONFLICT(bbl,evidence_type,source_record_id) DO UPDATE SET
     provenance=EXCLUDED.provenance,last_seen=NOW()`;
 const tot=await db`SELECT
   (SELECT COUNT(*)::int FROM radar_a_hpd_transaction_signals WHERE source_name='HPD_LL7_QUALIFIED_TRANSACTION') AS ll7,
   (SELECT COUNT(*)::int FROM radar_a_hpd_transaction_signals WHERE source_name='HPD_SPECULATION_WATCH_HISTORIC') AS speculation,
   (SELECT COUNT(*)::int FROM radar_a_regulation_review WHERE hpd_ll7_historic_transactions>0) AS matched_ll7_lots,
   (SELECT COUNT(*)::int FROM radar_a_regulation_review WHERE hpd_speculation_watch_historic>0) AS matched_watch_lots`;
 console.log(JSON.stringify({event:"milestone_a_hpd_signals_crosswalk_passed",total:tot[0],
   legal_regulation_verification:false}));
}
await db.close();
if(errors)process.exitCode=1;
