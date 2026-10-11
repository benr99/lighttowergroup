
import {SQL} from "bun";
const db=Bun.env.DATABASE_URL?new SQL(Bun.env.DATABASE_URL):null;
const auth=(r:Request)=>!!Bun.env.RADAR_API_KEY&&r.headers.get("authorization")==="Bearer "+Bun.env.RADAR_API_KEY;
const json=(x:any,status=200)=>new Response(JSON.stringify(x),{status,headers:{"Content-Type":"application/json; charset=utf-8",
 "Cache-Control":"no-store","X-Content-Type-Options":"nosniff"}});
async function overview(){
 const [collection,docs,dossiers,runs]=await Promise.all([
 db!`SELECT
  (SELECT COUNT(*)::int FROM radar_asset_screen) AS full_universe,
  (SELECT COUNT(*)::int FROM radar_acris_universe_attempts) AS attempts,
  (SELECT COUNT(*)::int FROM radar_acris_universe_attempts WHERE status='success') AS completed_lots,
  (SELECT COUNT(*)::int FROM radar_acris_universe_attempts WHERE status='partial') AS incomplete_lots,
  (SELECT COUNT(*)::int FROM radar_acris_universe_attempts WHERE status='error') AS failed_lots,
  (SELECT COUNT(*)::int FROM radar_acris_universe_attempts WHERE truncated) AS truncated_lots,
  (SELECT MAX(checked_at) FROM radar_acris_universe_attempts) AS latest_lot_check`,
 db!`SELECT
  (SELECT COUNT(*)::int FROM radar_acris_documents) AS unique_acris_master_documents,
  (SELECT COUNT(*)::int FROM radar_acris_universe_legals) AS unique_document_to_candidate_links,
  (SELECT COUNT(*)::int FROM radar_acris_party_evidence) AS indexed_recording_party_rows,
  (SELECT COUNT(*)::int FROM radar_acris_collateral_lots) AS indexed_document_collateral_lot_links,
  (SELECT COUNT(*)::int FROM radar_r22_refchecks WHERE source_complete) AS complete_reference_checks,
  (SELECT COUNT(*)::int FROM radar_r22_crossrefs) AS recorded_crossreference_rows`,
 db!`SELECT
  (SELECT COUNT(*)::int FROM radar_r22_dossiers) AS sample_dossiers,
  (SELECT COUNT(*)::int FROM radar_r22_document_events) AS dossier_financing_events,
  (SELECT COUNT(*)::int FROM radar_b_document_components) AS provisional_document_components,
  (SELECT COUNT(*)::int FROM radar_b_component_members) AS documents_assigned_component,
  (SELECT COUNT(*)::int FROM radar_b_document_reference_edges WHERE target_indexed_for_dossier) AS direct_reference_links_in_sample,
  (SELECT COUNT(*)::int FROM radar_b_document_source_checks WHERE source_status='COMPLETE') AS full_party_collateral_source_checks,
  (SELECT COUNT(*)::int FROM radar_r22_document_events e WHERE NOT EXISTS(
   SELECT 1 FROM radar_r22_refchecks r WHERE r.document_id=e.document_id AND r.source_complete)) AS reference_checks_still_needed,
  (SELECT COUNT(*)::int FROM radar_r22_maturity_submissions WHERE qa_status='PENDING_SECONDARY_REVIEW') AS submitted_maturity_claims_pending,
  (SELECT COUNT(*)::int FROM radar_b_document_components WHERE legal_facility_verified) AS verified_current_facilities`,
 db!`SELECT attempted,successful,failed,legal_records,master_records,status,completed_at
   FROM radar_acris_universe_job_runs WHERE completed_at IS NOT NULL ORDER BY id DESC LIMIT 3`
 ]);
 const collectionRows=await db!`SELECT s.borough,COUNT(*)::int AS candidate_lots,
    COUNT(*) FILTER(WHERE c.status='success')::int AS complete,
    COUNT(*) FILTER(WHERE c.status='partial')::int AS partial,
    COUNT(*) FILTER(WHERE c.status='error')::int AS error,
    COUNT(*) FILTER(WHERE c.bbl IS NULL)::int AS not_attempted
    FROM radar_asset_screen s LEFT JOIN radar_acris_universe_attempts c ON c.bbl=s.bbl
    GROUP BY s.borough ORDER BY s.borough`;
 const c=collection[0],d=dossiers[0];
 return {release:"MILESTONE_B",collection:{...c,remaining_unattempted:c.full_universe-c.attempts,
   completeness_percent:Number((100*c.completed_lots/c.full_universe).toFixed(2))},
  by_borough:collectionRows,documents:docs[0],research_dossiers:d,
  recent_collection_runs:runs,acceptance_gates:{
   full_universe_collection_cleared:c.attempts===c.full_universe&&c.completed_lots===c.full_universe,
   ten_document_reference_hypotheses_created:d.sample_dossiers===10&&d.dossier_financing_events===d.documents_assigned_component,
   all_ten_primary_instruments_independently_audited:false,
   ten_current_facilities_verified:d.verified_current_facilities>=10,
   known_maturity_or_payoff_verification_complete:false},
  caveats:[
    "ACRIS document amounts and recording dates are NOT outstanding loan balances or contractual maturities.",
    "Connected reference components are not certified loan families, and party metadata is not current lender verification.",
    "Success means indexed source rows collected within collector limits, not completeness of physical instrument contents.",
    "A property with no indexed mortgage may have financing absent from ACRIS or held at an entity level."
  ]};
}
Bun.serve({port:Number(Bun.env.PORT||3000),async fetch(req:Request){
 const u=new URL(req.url);
 if(u.pathname==="/health")return json({ok:!!db,component:"capital-stack-milestone-b-api"},db?200:503);
 if(!auth(req))return json({error:"Unauthorized"},401);
 if(!db)return json({error:"Database unavailable"},503);
 try{
 if(u.pathname==="/api/milestone-b/coverage"){
  if(req.method!=="GET")return json({error:"GET required"},405);
  return json(await overview());
 }
 if(u.pathname==="/api/milestone-b/dossier"){
  const bbl=u.searchParams.get("bbl")||"";
  if(!/^[0-9]{10}$/.test(bbl))return json({error:"Valid BBL required"},400);
  const dossier=await db`SELECT bbl,priority_order,address,residential_units,regulation_evidence,
   loan_reconstruction_state,loan_maturity_state,current_debt_verified,legal_free_market_verified
   FROM radar_r22_dossiers WHERE bbl=${bbl}`;
  if(!dossier.length)return json({error:"Not in the first ten research dossiers"},404);
  const [components,edges,checks,maturity]=await Promise.all([
  db`SELECT component_research_id,document_count,explicit_recorded_edges,
    latest_recording,multi_lot_documents,legal_facility_verified,state
    FROM radar_b_document_components WHERE bbl=${bbl}
    ORDER BY document_count DESC,component_research_id LIMIT 200`,
  db`SELECT source_document_id,target_document_id,source_reference_url,link_basis,
    target_indexed_for_dossier,legal_relationship_verified FROM radar_b_document_reference_edges
    WHERE bbl=${bbl} ORDER BY source_document_id LIMIT 300`,
  db`SELECT e.document_id,e.doc_type,e.recorded_datetime,e.doc_amt AS original_recorded_instrument_amount,
    e.collateral_lots,e.source_master_url,m.component_research_id,
    coalesce(r.source_complete,false) AS references_checked,
    coalesce(s.source_status,'NOT_CHECKED') AS parties_and_collateral_status
    FROM radar_r22_document_events e
    LEFT JOIN radar_b_component_members m ON m.bbl=e.bbl AND m.document_id=e.document_id
    LEFT JOIN radar_r22_refchecks r ON r.document_id=e.document_id
    LEFT JOIN radar_b_document_source_checks s ON s.document_id=e.document_id
    WHERE e.bbl=${bbl} ORDER BY e.recorded_datetime DESC NULLS LAST LIMIT 200`,
  db`SELECT contractual_maturity,extraction_status,confidence,source_document_id,
     source_url,source_page FROM radar_r22_maturity_research WHERE bbl=${bbl}`
  ]);
  return json({dossier:dossier[0],reference_connected_components:components,
   source_recorded_reference_edges:edges,recording_events:checks,
   maturity_research:maturity[0]??null,current_principal_verified:false,
   current_lender_verified:false,legal_loan_family_verified:false,free_market_status_verified:false,
   next_steps:["Obtain executed mortgage documents and all amendments from ACRIS imagery",
    "Verify references and legal consequences of each modification, release or satisfaction",
    "Obtain lender/servicer confirmation or payoff for actual outstanding principal",
    "Obtain source-page proof and independent review of contractual maturity",
    "Confirm rent regulation and property operating metrics before distressed underwriting"]});
 }
 if(u.pathname==="/api/milestone-b/research-queue"){
  const take=Number(u.searchParams.get("limit")??"25");
  if(!Number.isSafeInteger(take)||take<1||take>100)return json({error:"limit must be 1 to 100"},400);
  const list=await db`SELECT d.bbl,d.priority_order,d.address,d.borough,d.residential_units,
    d.loan_maturity_state,d.current_debt_verified,
    (SELECT COUNT(*)::int FROM radar_r22_document_events e WHERE e.bbl=d.bbl) AS recorded_events,
    (SELECT COUNT(*)::int FROM radar_r22_document_events e WHERE e.bbl=d.bbl
      AND NOT EXISTS(SELECT 1 FROM radar_r22_refchecks r WHERE r.document_id=e.document_id AND r.source_complete)) AS incomplete_reference_reviews,
    (SELECT COUNT(*)::int FROM radar_r22_document_events e WHERE e.bbl=d.bbl
      AND NOT EXISTS(SELECT 1 FROM radar_b_document_source_checks c WHERE c.document_id=e.document_id AND c.source_status='COMPLETE')) AS incomplete_party_collateral_reviews,
    (SELECT COUNT(*)::int FROM radar_b_document_reference_edges r WHERE r.bbl=d.bbl
       AND r.target_indexed_for_dossier) AS documentary_reference_links
   FROM radar_r22_dossiers d ORDER BY d.priority_order LIMIT ${take}`;
  return json({research_queue:list,verified_acquisition_candidates:0,
   stage:"UNVERIFIED_PUBLIC_RECORD_DOSSIERS",
   warning:"Research ordering is not an actionable distress score or a claim of approaching maturity."});
 }
 return json({error:"Not found"},404);
 }catch(err:any){
  console.error(JSON.stringify({event:"milestone_b_api_failed",path:u.pathname,error:String(err.message)}));
  return json({error:"Data service internal error"},500);
 }
}});
