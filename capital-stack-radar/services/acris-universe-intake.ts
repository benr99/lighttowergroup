
import {SQL} from "bun";
if(!Bun.env.DATABASE_URL)throw Error("DATABASE_URL required");
const db=new SQL(Bun.env.DATABASE_URL);
const API="https://data.cityofnewyork.us/resource/";
const pause=(ms:number)=>new Promise(resolve=>setTimeout(resolve,ms));
const fetchData=async(dataset:string,query:Record<string,string>)=>{
  const url=new URL(API+dataset+".json");
  for(const [key,value] of Object.entries(query))url.searchParams.set(key,value);
  let failure="Unknown error";
  for(let attempt=0;attempt<3;attempt++){
    try{
      const res=await fetch(url,{headers:{"Accept":"application/json",
        ...(Bun.env.SOCRATA_APP_TOKEN?{"X-App-Token":Bun.env.SOCRATA_APP_TOKEN}:{})},
        signal:AbortSignal.timeout(25000)});
      if(res.ok){const data=await res.json();if(!Array.isArray(data))throw Error("Unexpected source body");return data}
      failure="HTTP "+res.status+" "+(await res.text()).slice(0,150);
      if(res.status!==429&&res.status<500)throw Error(failure);
    }catch(err:any){failure=String(err.message);if(failure.startsWith("HTTP 4")&&!failure.startsWith("HTTP 429"))break}
    await pause(700*(attempt+1)**2);
  }
  throw Error(dataset+" "+failure);
};
await db`CREATE TABLE IF NOT EXISTS radar_acris_universe_legals(
 bbl TEXT NOT NULL,document_id TEXT NOT NULL,borough TEXT NOT NULL,good_through_date TEXT,
 property_type TEXT,record_type TEXT,raw JSONB NOT NULL,source_url TEXT NOT NULL,
 seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),PRIMARY KEY(bbl,document_id))`;
await db`CREATE INDEX IF NOT EXISTS radar_acris_universe_legals_doc_idx ON radar_acris_universe_legals(document_id)`;
await db`CREATE TABLE IF NOT EXISTS radar_acris_universe_attempts(
 bbl TEXT PRIMARY KEY,status TEXT NOT NULL DEFAULT 'pending',legal_count INT NOT NULL DEFAULT 0,
 master_count INT NOT NULL DEFAULT 0,source_pages INT NOT NULL DEFAULT 0,truncated BOOLEAN NOT NULL DEFAULT FALSE,
 error_text TEXT,checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW())`;
await db`CREATE TABLE IF NOT EXISTS radar_acris_universe_job_runs(
 id BIGSERIAL PRIMARY KEY,attempted INT NOT NULL DEFAULT 0,successful INT NOT NULL DEFAULT 0,
 failed INT NOT NULL DEFAULT 0,legal_records INT NOT NULL DEFAULT 0,
 master_records INT NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT 'running',
 completed_at TIMESTAMPTZ,error_text TEXT)`;
await db`CREATE TABLE IF NOT EXISTS radar_acris_documents (
 document_id TEXT PRIMARY KEY,doc_type TEXT,document_amt NUMERIC,recorded_datetime TIMESTAMPTZ,
 raw JSONB NOT NULL,source_url TEXT NOT NULL,last_seen TIMESTAMPTZ DEFAULT NOW())`;
await db`CREATE TABLE IF NOT EXISTS radar_collateral_links (
 document_id TEXT NOT NULL REFERENCES radar_acris_documents(document_id),
 bbl TEXT NOT NULL REFERENCES radar_properties(bbl),PRIMARY KEY(document_id,bbl))`;
await db`CREATE TABLE IF NOT EXISTS radar_acris_intake_leases(
 name TEXT PRIMARY KEY,locked_until TIMESTAMPTZ NOT NULL DEFAULT to_timestamp(0),
 lease_owner TEXT,last_heartbeat TIMESTAMPTZ)`;
await db`INSERT INTO radar_acris_intake_leases(name) VALUES('main_acris_collector') ON CONFLICT DO NOTHING`;
const acquired=await db`UPDATE radar_acris_intake_leases
 SET locked_until=NOW()+INTERVAL '280 seconds',
 lease_owner=${Bun.env.RAILWAY_DEPLOYMENT_ID||"railway-cron"},last_heartbeat=NOW()
 WHERE name='main_acris_collector' AND locked_until<NOW() RETURNING name`;
if(acquired.length!==1){
 console.log(JSON.stringify({event:"acris_intake_overlap_suppressed",policy:"skip_if_prior_batch_lease_valid"}));
 await db.close();process.exit(0);
}
const integrity=await db`SELECT
 (SELECT COUNT(*)::int FROM radar_pluto_raw) AS raw_lots,
 (SELECT COUNT(*)::int FROM radar_asset_screen) AS screened_lots,
 (SELECT COUNT(*)::int FROM radar_asset_identity_hypotheses) AS identity_rows`;
if(integrity[0].raw_lots!==318610||integrity[0].screened_lots!==4436||integrity[0].identity_rows!==4436)
 throw Error("Release 1 data intake acceptance not met: "+JSON.stringify(integrity[0]));
const candidates=await db`SELECT bbl,borough,block,lot,unitsres FROM (
 SELECT s.bbl,s.borough,p.block,p.lot,s.unitsres,
 ROW_NUMBER() OVER(PARTITION BY s.borough ORDER BY
    CASE WHEN s.screen_status='MF_TAX_LOT_NEEDS_ASSET_VERIFICATION' THEN 0 ELSE 1 END,
    CASE WHEN s.hcr_2024_evidence='NOT_LISTED_2024_FREE_MARKET_UNVERIFIED' THEN 0 ELSE 1 END,
    CASE WHEN s.unitsres BETWEEN 70 AND 600 THEN 0 ELSE 1 END, s.unitsres ASC,s.bbl) AS seq
 FROM radar_asset_screen s JOIN radar_properties p ON p.bbl=s.bbl
 LEFT JOIN radar_acris_universe_attempts a ON a.bbl=s.bbl
 WHERE (a.bbl IS NULL OR (a.status IN ('error','partial') AND a.checked_at<NOW()-INTERVAL '12 hours'))
 ) q ORDER BY seq,borough LIMIT 48`;
const run=await db`INSERT INTO radar_acris_universe_job_runs(status) VALUES('running') RETURNING id`;const runid=run[0].id;
let ok=0,failed=0,legalCount=0,masterCount=0;
for(const item of candidates){
  let legal:any[]=[],pages=0,partial=false,masters=0;
  try{
    const borough=item.borough==="MN"?"1":"3",block=Number(item.block),lot=Number(item.lot);
    if(!Number.isSafeInteger(block)||!Number.isSafeInteger(lot)||block<1||lot<1)throw Error("Invalid tax lot");
    for(let offset=0;offset<1500;offset+=300){
      const results=await fetchData("8h5j-fqxa",{borough,block:String(block),lot:String(lot),"$limit":"300","$offset":String(offset),"$order":"document_id"});
      pages++;legal.push(...results);
      if(results.length<300)break;
      if(offset===1200)partial=true;
    }
    const docs=[...new Set(legal.map(x=>String(x.document_id||"")).filter(v=>/^[A-Za-z0-9_-]{1,80}$/.test(v)))];
    // A document may appear on multiple ACRIS legal rows; duplicates are expected.
    for(const x of legal){
      if(!/^[A-Za-z0-9_-]{1,80}$/.test(String(x.document_id||"")))continue;
      const json=JSON.stringify(x);
      await db`INSERT INTO radar_acris_universe_legals(bbl,document_id,borough,good_through_date,property_type,record_type,raw,source_url,seen_at)
        VALUES(${item.bbl},${x.document_id},${item.borough},${x.good_through_date??null},${x.property_type??null},${x.record_type??null},
        ((${json}::jsonb #>> '{}')::jsonb),'https://data.cityofnewyork.us/resource/8h5j-fqxa.json',NOW())
        ON CONFLICT(bbl,document_id) DO UPDATE SET raw=EXCLUDED.raw,seen_at=NOW(),good_through_date=EXCLUDED.good_through_date`;
    }
    const uniqueMasters=new Set<string>();
    for(let i=0;i<docs.length;i+=50){
      const chunk=docs.slice(i,i+50);
      const where="document_id in ("+chunk.map(id=>"'"+id+"'").join(",")+")";
      const results=await fetchData("bnx9-e6tj",{"$where":where,"$limit":"1000"});
      if(results.length>=1000)partial=true;
      const found=new Set<string>();
      for(const x of results){
        if(!chunk.includes(String(x.document_id)))continue;
        found.add(String(x.document_id));
        const amount=x.document_amt===undefined||x.document_amt===null?null:Number(x.document_amt);
        const validAmount=amount!==null&&Number.isFinite(amount)?amount:null;
        const raw=JSON.stringify(x);
        await db`INSERT INTO radar_acris_documents(document_id,doc_type,document_amt,recorded_datetime,raw,source_url,last_seen)
           VALUES(${String(x.document_id)},${x.doc_type??null},${validAmount},${x.recorded_datetime??null},
           ((${raw}::jsonb #>> '{}')::jsonb),'https://data.cityofnewyork.us/resource/bnx9-e6tj.json',NOW())
           ON CONFLICT(document_id) DO UPDATE SET doc_type=EXCLUDED.doc_type,document_amt=EXCLUDED.document_amt,
           recorded_datetime=EXCLUDED.recorded_datetime,raw=EXCLUDED.raw,last_seen=NOW()`;
        await db`INSERT INTO radar_collateral_links(document_id,bbl) VALUES(${String(x.document_id)},${item.bbl})
          ON CONFLICT DO NOTHING`;
        if(!uniqueMasters.has(String(x.document_id))){uniqueMasters.add(String(x.document_id));masters++;}
      }
      if(chunk.some(id=>!found.has(id)))partial=true;
    }
    await db`INSERT INTO radar_acris_universe_attempts(bbl,status,legal_count,master_count,source_pages,truncated,error_text,checked_at)
       VALUES(${item.bbl},${partial?'partial':'success'},${docs.length},${masters},${pages},${partial},NULL,NOW())
       ON CONFLICT(bbl) DO UPDATE SET status=EXCLUDED.status,legal_count=EXCLUDED.legal_count,
       master_count=EXCLUDED.master_count,source_pages=EXCLUDED.source_pages,truncated=EXCLUDED.truncated,
       error_text=NULL,checked_at=NOW()`;
    ok++;legalCount+=docs.length;masterCount+=masters;
    console.log(JSON.stringify({event:"acris_universe_lot_collected",bbl:item.bbl,legal_documents:docs.length,
      matched_master_records:masters,pages,partial,warning:"Recorded metadata is not verified current financing."}));
  }catch(err:any){
    failed++;
    const message=String(err.message).slice(0,600);
    await db`INSERT INTO radar_acris_universe_attempts(bbl,status,legal_count,master_count,source_pages,truncated,error_text,checked_at)
       VALUES(${item.bbl},'error',${legal.length},${masters},${pages},true,${message},NOW())
       ON CONFLICT(bbl) DO UPDATE SET status='error',legal_count=EXCLUDED.legal_count,
       master_count=EXCLUDED.master_count,source_pages=EXCLUDED.source_pages,
       truncated=true,error_text=EXCLUDED.error_text,checked_at=NOW()`;
    console.error(JSON.stringify({event:"acris_universe_lot_error",bbl:item.bbl,error:message}));
  }
}
await db`UPDATE radar_acris_universe_job_runs SET attempted=${candidates.length},successful=${ok},failed=${failed},
 legal_records=${legalCount},master_records=${masterCount},status=${failed?'partial':'success'},completed_at=NOW() WHERE id=${runid}`;
console.log(JSON.stringify({event:"acris_universe_intake_run",attempted:candidates.length,
 completed:ok,failed,legal_documents:legalCount,master_documents:masterCount,
 source:"NYC ACRIS Legals and Master",interpretation:"Evidence discovery only, not verified payoff or maturity."}));
await db`UPDATE radar_acris_intake_leases SET locked_until=NOW(),last_heartbeat=NOW()
 WHERE name='main_acris_collector'`;
await db.close();
if(failed)process.exitCode=1;
