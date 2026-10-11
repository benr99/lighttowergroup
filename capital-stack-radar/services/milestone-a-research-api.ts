
import {SQL} from "bun";
const db=Bun.env.DATABASE_URL?new SQL(Bun.env.DATABASE_URL):null;
const json=(x:any,status=200)=>new Response(JSON.stringify(x),{status,headers:{
 "Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store",
 "X-Content-Type-Options":"nosniff"}});
const authorized=(req:Request)=>!!Bun.env.RADAR_API_KEY&&req.headers.get("authorization")==="Bearer "+Bun.env.RADAR_API_KEY;
function csvField(x:any){
 let value=String(x??"");
 if(/^[=+@-]/.test(value.trimStart()))value="'"+value;
 return '"'+value.replaceAll('"','""')+'"';
}
async function summary(){
 const base=await db!`SELECT
  (SELECT COUNT(*)::int FROM radar_pluto_raw) AS raw_lots,
  (SELECT COUNT(*)::int FROM radar_asset_screen) AS qualifying_tax_lots,
  (SELECT COUNT(*)::int FROM radar_a_asset_register) AS research_asset_ids,
  (SELECT COUNT(*)::int FROM radar_a_asset_register WHERE analyst_exception) AS unresolved_asset_identifications,
  (SELECT COUNT(*)::int FROM radar_a_regulation_review) AS regulation_screened_lots,
  (SELECT COUNT(*)::int FROM radar_a_regulation_review WHERE historical_hcr_2024) AS hcr_2024_listed,
  (SELECT COUNT(*)::int FROM radar_a_regulation_review WHERE NOT historical_hcr_2024) AS not_on_2024_hcr_unverified,
  (SELECT COUNT(*)::int FROM radar_a_regulation_review WHERE legal_free_market_certified) AS verified_free_market,
  (SELECT COUNT(*)::int FROM radar_a_evidence) AS evidence_records,
  (SELECT COUNT(*)::int FROM radar_a_physical_link_clusters) AS physical_link_clusters,
  (SELECT COUNT(*)::int FROM radar_a_regulation_review WHERE hpd_checked) AS hpd_source_checks_complete,
  (SELECT COUNT(*)::int FROM radar_a_regulation_review WHERE dof_checked) AS dof_source_checks_complete,
  (SELECT COUNT(*)::int FROM radar_a_regulation_review WHERE hpd_ll7_historic_transactions>0) AS ll7_sale_lots,
  (SELECT COUNT(*)::int FROM radar_a_regulation_review WHERE hpd_speculation_watch_historic>0) AS speculation_watch_sale_lots,
  (SELECT COUNT(*)::int FROM radar_a_review_items WHERE status='OPEN') AS open_review_tasks`;
 const identity=await db!`SELECT identity_triage,COUNT(*)::int AS candidate_lots
  FROM radar_a_asset_register GROUP BY identity_triage ORDER BY candidate_lots DESC`;
 const regulation=await db!`SELECT review_category,COUNT(*)::int AS candidate_lots,
  COUNT(*) FILTER(WHERE historical_hcr_2024)::int AS hcr_2024_list_matches
  FROM radar_a_regulation_review GROUP BY review_category ORDER BY candidate_lots DESC`;
 const coverage=await db!`SELECT a.borough,COUNT(*)::int AS candidate_lots,
  COUNT(*) FILTER(WHERE r.historical_hcr_2024)::int AS hcr_2024_listed,
  COUNT(*) FILTER(WHERE r.hpd_checked)::int AS hpd_collected,
  COUNT(*) FILTER(WHERE r.dof_checked)::int AS dof_collected,
  COUNT(*) FILTER(WHERE a.legal_economic_asset_verification='VERIFIED')::int AS verified_economic_assets
  FROM radar_a_asset_register a JOIN radar_a_regulation_review r ON r.bbl=a.bbl GROUP BY a.borough ORDER BY a.borough`;
 const sourceRuns=await db!`SELECT DISTINCT ON(source_name) source_name,source_rows,processed_rows,matched_candidates,
  completeness,completed_at FROM radar_a_hpd_signal_import_runs ORDER BY source_name,id DESC`;
 const latest=await db!`SELECT status,raw_tax_lots,candidate_lots,asset_research_rows,regulatory_reviews,
  assets_with_review_exception,hcr_matched_candidates,unlisted_hcr_candidates,
  source_hpd_checked,source_dof_checked,uncovered_candidate_lots,
  unsupported_free_market_claims,created_at
  FROM radar_a_acceptance_runs ORDER BY id DESC LIMIT 1`;
 const b=base[0],ok=b.raw_lots===318610&&b.qualifying_tax_lots===4436&&
  b.research_asset_ids===4436&&b.regulation_screened_lots===4436&&
  b.hpd_source_checks_complete===4436&&b.dof_source_checks_complete===4436&&
  b.verified_free_market===0&&b.evidence_records>=4436;
 return {
   release:"MILESTONE_A_EVIDENCE_SCREEN",technical_coverage_gate:ok,
   source_population:"Manhattan and Brooklyn PLUTO 26v2, 70+ residential units per tax lot",
   counts:b,by_borough:coverage,identity_categories:identity,regulation_categories:regulation,
   hpd_historic_sales_source_runs:sourceRuns,last_acceptance:latest[0]??null,
   legal_rental_asset_verification_complete:false,free_market_certification_complete:false,
   investment_eligibility_certified:false,
   interpretation:"Each LOT:... is a stable lot-level research record, not a verified independent rental asset. Shared HPD BIN is a physical link, not ownership or additivity. HCR nonlisting is not free-market evidence."
 };
}
Bun.serve({port:Number(Bun.env.PORT||3000),async fetch(req:Request){
 const u=new URL(req.url);
 if(u.pathname==="/health")return json({ok:!!db,service:"radar-milestone-a-research-api"},db?200:503);
 if(!authorized(req))return json({error:"Unauthorized"},401);
 if(!db)return json({error:"Database unavailable"},503);
 try{
  if(u.pathname==="/api/milestone-a/summary"){
   if(req.method!=="GET")return json({error:"GET only"},405);
   return json(await summary());
  }
  if(u.pathname==="/api/milestone-a/assets"||u.pathname==="/api/milestone-a/exceptions"){
   const borough=u.searchParams.get("borough"),regulation=u.searchParams.get("regulation"),
    identity=u.searchParams.get("identity"),maxRaw=u.searchParams.get("max_units");
   if(borough&&!["BK","MN"].includes(borough))return json({error:"Invalid borough"},400);
   const upper=maxRaw==null?null:Number(maxRaw);
   if(upper!=null&&(!Number.isSafeInteger(upper)||upper<70||upper>100000))
     return json({error:"Invalid max_units"},400);
   const limit=Number(u.searchParams.get("limit")??"50"),offset=Number(u.searchParams.get("offset")??"0");
   if(!Number.isSafeInteger(limit)||limit<1||limit>100||!Number.isSafeInteger(offset)||offset<0||offset>10000)
     return json({error:"Invalid pagination"},400);
   const exceptionsOnly=u.pathname.endsWith("exceptions")||u.searchParams.get("exceptions_only")==="true";
   const rows=await db`SELECT a.asset_research_id,a.bbl,a.borough,a.source_address,a.pluto_owner_name,
     a.residential_units_per_lot,a.screen_type,a.primary_bin,a.bin_count,a.physical_group_id,
     a.shared_bin_lot_count,a.hpd_building_count,a.identity_triage,a.ownership_verification,
     a.legal_economic_asset_verification,a.analyst_exception,
     r.review_category,r.historical_hcr_2024,r.dof_exemption_record_count,
     r.hpd_ll7_historic_transactions,r.hpd_speculation_watch_historic,
     r.hpd_checked,r.dof_checked,r.current_unit_level_regulation,
     r.legal_free_market_certified
    FROM radar_a_asset_register a JOIN radar_a_regulation_review r ON r.bbl=a.bbl
    WHERE (${borough}::text IS NULL OR a.borough=${borough})
    AND (${regulation}::text IS NULL OR r.review_category=${regulation})
    AND (${identity}::text IS NULL OR a.identity_triage=${identity})
    AND (${upper}::int IS NULL OR a.residential_units_per_lot<=${upper})
    AND (${exceptionsOnly}=FALSE OR a.analyst_exception)
    ORDER BY
      CASE WHEN a.identity_triage IN('SHARED_BIN_MULTIPLE_TAX_LOTS_REVIEW','MULTIPLE_PHYSICAL_BUILDINGS_PER_TAX_LOT') THEN 0
           WHEN a.identity_triage='CONDO_COOP_ECONOMIC_IDENTITY_EXCEPTION' THEN 1 ELSE 2 END,
      a.borough,a.bbl LIMIT ${limit} OFFSET ${offset}`;
   const total=await db`SELECT COUNT(*)::int AS n FROM radar_a_asset_register a
      JOIN radar_a_regulation_review r ON r.bbl=a.bbl
      WHERE (${borough}::text IS NULL OR a.borough=${borough})
      AND (${regulation}::text IS NULL OR r.review_category=${regulation})
      AND (${identity}::text IS NULL OR a.identity_triage=${identity})
      AND (${upper}::int IS NULL OR a.residential_units_per_lot<=${upper})
      AND (${exceptionsOnly}=FALSE OR a.analyst_exception)`;
   return json({count:total[0].n,records:rows,limit,offset,
     selection:"Tax-lot research candidates; NONE automatically verified as independently saleable, free-market rental assets."});
  }
  if(u.pathname==="/api/milestone-a/asset"){
    const bbl=u.searchParams.get("bbl")||"";
    if(!/^[0-9]{10}$/.test(bbl))return json({error:"Valid 10-digit BBL required"},400);
    const rows=await db`SELECT a.*,r.review_category,r.historical_hcr_2024,
      r.dof_exemption_record_count,r.hpd_ll7_historic_transactions,
      r.hpd_speculation_watch_historic,r.current_unit_level_regulation,
      r.legal_free_market_certified,r.hpd_checked,r.dof_checked,
      r.review_flags,r.sources_to_check,r.last_screened
      FROM radar_a_asset_register a JOIN radar_a_regulation_review r ON r.bbl=a.bbl
      WHERE a.bbl=${bbl}`;
    if(!rows.length)return json({error:"Not a qualifying research lot"},404);
    const evidence=await db`SELECT evidence_type,source_record_id,source_url,source_year,
       evidence_interpretation,provenance,last_seen FROM radar_a_evidence
       WHERE bbl=${bbl} ORDER BY evidence_type,source_record_id LIMIT 300`;
    const review=await db`SELECT review_kind,priority,reason,status,created_at,last_checked
      FROM radar_a_review_items WHERE bbl=${bbl} ORDER BY priority,review_kind`;
    const membership=await db`SELECT linked_candidate_lots,relation_type,status,
       legal_common_ownership_confirmed,units_should_be_aggregated
      FROM radar_a_physical_link_clusters WHERE physical_group_id=${rows[0].physical_group_id}`;
    return json({asset:rows[0],evidence,review_items:review,
      physical_link_cluster:membership[0]??null,
      links_truncated:evidence.length===300,
      current_economic_owner_verified:false,
      verified_unit_level_regulation:false,
      verified_free_market:false,
      warning:"A shared BIN and historical HCR/HPD records are not conclusive evidence of common ownership, current rent status, or independently saleable property boundaries."});
  }
  if(u.pathname==="/api/milestone-a/export.csv"){
    if(req.method!=="GET")return json({error:"GET only"},405);
    const rows=await db`SELECT a.bbl,a.asset_research_id,a.borough,a.source_address,
       a.residential_units_per_lot,a.pluto_owner_name,a.screen_type,
       a.primary_bin,a.bin_count,a.physical_group_id,a.shared_bin_lot_count,
       a.hpd_building_count,a.identity_triage,a.ownership_verification,
       a.legal_economic_asset_verification,r.review_category,r.historical_hcr_2024,
       r.hpd_checked,r.dof_checked,r.dof_exemption_record_count,
       r.hpd_ll7_historic_transactions,r.hpd_speculation_watch_historic,
       r.current_unit_level_regulation,r.legal_free_market_certified,a.source_pluto_url
       FROM radar_a_asset_register a JOIN radar_a_regulation_review r ON r.bbl=a.bbl
       ORDER BY a.borough,a.bbl`;
    if(rows.length!==4436)return json({error:"Expected 4436 rows before export; reconciliation required"},503);
    const keys=Object.keys(rows[0]);const result=[keys.join(","),...rows.map(x=>keys.map(k=>csvField(x[k])).join(","))].join("\n");
    return new Response(result,{headers:{"Content-Type":"text/csv; charset=utf-8",
      "Content-Disposition":'attachment; filename="capital-stack-radar-milestone-a-research-register.csv"',
      "Cache-Control":"no-store","X-Content-Type-Options":"nosniff"}});
  }
  return json({error:"Not found"},404);
 }catch(err:any){
  console.error(JSON.stringify({event:"milestone_a_research_api_error",route:u.pathname,error:String(err.message)}));
  return json({error:"Internal data service error"},500);
 }
}});
