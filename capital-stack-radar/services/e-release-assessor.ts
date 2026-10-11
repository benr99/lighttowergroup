
import {SQL} from "bun";
if(!Bun.env.DATABASE_URL)throw Error("DATABASE_URL required");
const db=new SQL(Bun.env.DATABASE_URL);
await db`CREATE TABLE IF NOT EXISTS radar_e_release_gates(
 id BIGSERIAL PRIMARY KEY,scope TEXT NOT NULL DEFAULT 'development',
 technical_gates JSONB NOT NULL,investment_evidence_gates JSONB NOT NULL,
 operational_gates JSONB NOT NULL,
 all_production_gates_passed BOOLEAN NOT NULL DEFAULT FALSE,
 summary JSONB NOT NULL,run_at TIMESTAMPTZ NOT NULL DEFAULT NOW())`;
await db`CREATE INDEX IF NOT EXISTS radar_e_release_gates_recent ON radar_e_release_gates(run_at DESC)`;
async function checkHealth(url:string){
 try{
  const res=await fetch(url,{signal:AbortSignal.timeout(10000),headers:{Accept:"application/json"}});
  const body=await res.json().catch(()=>({}));
  return {http:res.status,pass:res.status===200&&body?.ok===true};
 }catch(e:any){return {http:null,pass:false,error:String(e.message).slice(0,200)}}
}
const [
 a,b,c,d,security,health
]=await Promise.all([
 db`SELECT COUNT(*)::int AS assets,(SELECT COUNT(*)::int FROM radar_a_regulation_review) AS regulation,
  (SELECT COUNT(*)::int FROM radar_a_asset_register WHERE ownership_verification='VERIFIED') AS ownership_verified,
  (SELECT COUNT(*)::int FROM radar_a_regulation_review WHERE legal_free_market_certified) AS legally_free_market
  FROM radar_a_asset_register`,
 db`SELECT
 (SELECT COUNT(*)::int FROM radar_asset_screen) AS target,
 (SELECT COUNT(*)::int FROM radar_acris_universe_attempts WHERE status='success') AS complete,
 (SELECT COUNT(*)::int FROM radar_acris_universe_attempts WHERE status='partial') AS partial,
 (SELECT COUNT(*)::int FROM radar_acris_universe_attempts WHERE status='error') AS failed,
 (SELECT COUNT(*)::int FROM radar_r22_dossiers) AS dossiers,
 (SELECT COUNT(*)::int FROM radar_b_document_components WHERE legal_facility_verified) AS verified_facilities,
 (SELECT COUNT(*)::int FROM radar_b_document_components WHERE documented_contractual_maturity IS NOT NULL) AS verified_maturities`,
 db`SELECT
 (SELECT COUNT(*)::int FROM radar_c_underwriting_scenarios) AS scenarios,
 (SELECT COUNT(*)::int FROM radar_c_underwriting_scenarios WHERE independent_review_complete) AS independently_reviewed,
 (SELECT COUNT(*)::int FROM radar_c_underwriting_scenarios WHERE investment_recommendation_verified) AS verified_underwriting`,
 db`SELECT
 (SELECT COUNT(*)::int FROM radar_d_acquisition_leads) AS leads,
 (SELECT COUNT(*)::int FROM radar_d_acquisition_leads WHERE acquisition_qualified) AS acquisition_qualified,
 (SELECT COUNT(*)::int FROM radar_d_professional_contacts) AS researched_professionals`,
 db`SELECT
 (SELECT COUNT(*)::int FROM radar_a_integrity_watch_runs WHERE pass) AS a_integrity_pass_exists,
 (SELECT COUNT(*)::int FROM radar_e_release_gates) AS prior_release_gate_runs`,
 Promise.all([
 checkHealth("https://radar-research-ui-development.up.railway.app/health"),
 checkHealth("https://radar-milestone-b-research-api-development.up.railway.app/health"),
 checkHealth("https://radar-c-underwriting-engine-development.up.railway.app/health"),
 checkHealth("https://radar-d-origination-workflow-development.up.railway.app/health"),
 checkHealth("https://radar-milestone-a-research-api-development.up.railway.app/health")])
]);
const h=health.map((x,i)=>({service:["research-ui","milestone-b-api","underwriting-api","origination-api","milestone-a-api"][i],...x}));
const technical={
 a_register_coverage:a[0].assets===4436&&a[0].regulation===4436,
 source_collection_coverage:b[0].complete===b[0].target,
 all_technical_http_services_healthy:h.every(x=>x.pass),
 c_underwriting_service_active:h[2].pass,
 d_origination_service_active:h[3].pass,
 original_dossiers_loaded:b[0].dossiers>=10
};
const evidence={
 independently_verified_legal_asset_identity:a[0].ownership_verified>=10,
 verified_free_market_for_relevant_cases:a[0].legally_free_market>=10,
 b_financing_universe_reconciled:b[0].complete===b[0].target&&b[0].partial===0&&b[0].failed===0,
 b_ten_actual_financing_facilities:b[0].verified_facilities>=10,
 b_ten_documented_maturities:b[0].verified_maturities>=10,
 c_ten_underwriting_models_reviewed:c[0].independently_reviewed>=10,
 c_ten_verified_investment_models:c[0].verified_underwriting>=10,
 d_actionable_researched_acquisitions:d[0].acquisition_qualified>=10
};
const operational={
 rollback_from_staging_tested:false,
 github_ci_cd_deployment_verified:false,
 per_user_role_based_access_confirmed:false,
 third_party_penetration_test_passed:false,
 postgres_pitr_enabled_and_tested_restore:false,
 encrypted_backups_independently_verified:false,
 regulatory_data_commercial_licensing_confirmed:false,
 automated_incident_notification_tested:false,
 disaster_recovery_rto_rpo_verified:false
};
const passed=Object.values(technical).every(Boolean)&&Object.values(evidence).every(Boolean)&&Object.values(operational).every(Boolean);
const summary={
 counted_assets:a[0],financing:b[0],underwriting:c[0],origination:d[0],
 services:h,
 stage:"DEVELOPMENT_ENGINEERING_WITH_OPEN_VERIFICATION_REQUIREMENTS",
 warning:"No secured production launch claim until ALL actual evidence and operational gates pass. Automated assessment does not itself configure Railway backups, RBAC or incident alerts."};
await db`INSERT INTO radar_e_release_gates(scope,technical_gates,investment_evidence_gates,
 operational_gates,all_production_gates_passed,summary)
 VALUES('development',${JSON.stringify(technical)}::jsonb,
  ${JSON.stringify(evidence)}::jsonb,${JSON.stringify(operational)}::jsonb,
  ${passed},${JSON.stringify(summary)}::jsonb)`;
console.log(JSON.stringify({event:"milestone_e_live_release_assessment",
 production_ready:passed,technical_passed:Object.values(technical).filter(Boolean).length,
 technical_total:Object.keys(technical).length,
 evidence_passed:Object.values(evidence).filter(Boolean).length,
 evidence_total:Object.keys(evidence).length,
 operations_passed:Object.values(operational).filter(Boolean).length,
 operations_total:Object.keys(operational).length,
 gates:{technical,evidence,operational},snapshot:summary}));
await db.close();
