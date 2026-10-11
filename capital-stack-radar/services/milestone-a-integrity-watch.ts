
import {SQL} from "bun";
if(!Bun.env.DATABASE_URL)throw Error("DATABASE_URL is required");
const db=new SQL(Bun.env.DATABASE_URL);
await db`CREATE TABLE IF NOT EXISTS radar_a_source_catalog(
 source_key TEXT PRIMARY KEY,source_name TEXT NOT NULL,source_url TEXT NOT NULL,
 snapshot_label TEXT NOT NULL,nominal_refresh_days INT NOT NULL,
 source_as_of TEXT,warehouse_last_imported TIMESTAMPTZ,
 verification_state TEXT NOT NULL DEFAULT 'SOURCE_METADATA_ONLY',
 limitations TEXT NOT NULL,updated_at TIMESTAMPTZ DEFAULT NOW())`;
await db`CREATE TABLE IF NOT EXISTS radar_a_integrity_watch_runs(
 id BIGSERIAL PRIMARY KEY,pass BOOLEAN NOT NULL,raw_lots INT,candidate_lots INT,
 asset_identity_coverage INT,regulation_coverage INT,hpd_success INT,
 dof_success INT,hcr_listed INT,ll7_matched_lots INT,speculation_watch_matched_lots INT,
 free_market_verified INT,open_review_tasks INT,source_evidence_rows INT,
 errors JSONB NOT NULL DEFAULT '[]'::jsonb,checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW())`;
const catalog=[
 ["PLUTO_26V2","NYC DCP Primary Land Use Tax Lot Output","https://data.cityofnewyork.us/resource/64uk-42ks.json",
  "26v2 NYC Open Data 2026-08-24",90,"2026-08-24","Census by tax lot, not verified economic property or rent unit status"],
 ["HCR_2024","NYS HCR registered-building lists (2024)","https://rentguidelinesboard.cityofnewyork.us/resources/rent-stabilized-building-lists/",
  "2024 registrations published by RGB November 2025",365,"2025-11","Historical owner registrations only; absent properties may still have regulated units"],
 ["HPD_JURISDICTION","HPD Buildings Subject to Jurisdiction","https://data.cityofnewyork.us/resource/kj4p-ruqc.json",
  "NYC HPD building registry",90,null,"Physical identifiers; neither rental eligibility nor HCR regulation"],
 ["DOF_EXEMPTIONS","DOF Property Exemption Detail","https://data.cityofnewyork.us/resource/muvi-b6kx.json",
  "NYC DOF updated 2026-06-15",180,"2026-06-15","Exemption type and benefit terms must be interpreted separately"],
 ["HPD_LL7_SALES","HPD Local Law 7 Qualified Transactions","https://data.cityofnewyork.us/resource/8wi4-bsy4.json",
  "May 7 2026 source",90,"2026-05-07","Historical qualified rent-regulated sales, not proof of current regulation"],
 ["HPD_SPECULATION_WATCH","HPD Speculation Watch List","https://data.cityofnewyork.us/resource/adax-9mit.json",
  "May 7 2026 source",90,"2026-05-07","Historic sales watchlist, not present financial distress"]
];
for(const x of catalog){
 await db`INSERT INTO radar_a_source_catalog(
  source_key,source_name,source_url,snapshot_label,nominal_refresh_days,source_as_of,limitations)
  VALUES(${x[0]},${x[1]},${x[2]},${x[3]},${x[4]},${x[5]},${x[6]})
  ON CONFLICT(source_key) DO UPDATE SET source_url=EXCLUDED.source_url,
    limitations=EXCLUDED.limitations,updated_at=NOW()`;
}
await db`UPDATE radar_a_source_catalog SET warehouse_last_imported=
 CASE source_key
 WHEN 'PLUTO_26V2' THEN (SELECT MAX(completed_at) FROM radar_universe_progress)
 WHEN 'HCR_2024' THEN (SELECT MAX(completed_at) FROM radar_hcr_2024_runs WHERE status='success')
 WHEN 'HPD_JURISDICTION' THEN (SELECT MAX(checked_at) FROM radar_hpd_checks WHERE status='success')
 WHEN 'DOF_EXEMPTIONS' THEN (SELECT MAX(checked_at) FROM radar_dof_exemption_checks WHERE status='success')
 WHEN 'HPD_LL7_SALES' THEN (SELECT MAX(completed_at) FROM radar_a_hpd_signal_import_runs
   WHERE source_name='HPD_LL7_QUALIFIED_TRANSACTION' AND completeness='ALL_SOURCE_ROWS_LOADED')
 WHEN 'HPD_SPECULATION_WATCH' THEN (SELECT MAX(completed_at) FROM radar_a_hpd_signal_import_runs
   WHERE source_name='HPD_SPECULATION_WATCH_HISTORIC' AND completeness='ALL_SOURCE_ROWS_LOADED')
 ELSE NULL END,
 verification_state='SOURCE_IMPORTED_WITH_PROVENANCE',updated_at=NOW()`;
const v=await db`SELECT
 (SELECT COUNT(*)::int FROM radar_pluto_raw) AS raw_lots,
 (SELECT COUNT(*)::int FROM radar_asset_screen) AS screened_lots,
 (SELECT COUNT(*)::int FROM radar_a_asset_register) AS assets,
 (SELECT COUNT(*)::int FROM radar_a_regulation_review) AS regulation,
 (SELECT COUNT(*)::int FROM radar_a_regulation_review WHERE historical_hcr_2024) AS hcr,
 (SELECT COUNT(*)::int FROM radar_hpd_checks c JOIN radar_asset_screen s ON s.bbl=c.bbl WHERE c.status='success') AS hpd,
 (SELECT COUNT(*)::int FROM radar_dof_exemption_checks c JOIN radar_asset_screen s ON s.bbl=c.bbl WHERE c.status='success') AS dof,
 (SELECT COUNT(*)::int FROM radar_a_regulation_review WHERE hpd_ll7_historic_transactions>0) AS ll7,
 (SELECT COUNT(*)::int FROM radar_a_regulation_review WHERE hpd_speculation_watch_historic>0) AS spec,
 (SELECT COUNT(*)::int FROM radar_a_regulation_review WHERE legal_free_market_certified) AS free_market,
 (SELECT COUNT(*)::int FROM radar_a_review_items WHERE status='OPEN') AS review_tasks,
 (SELECT COUNT(*)::int FROM radar_a_evidence) AS evidence,
 (SELECT COUNT(*)::int FROM radar_a_asset_register a WHERE NOT EXISTS(
  SELECT 1 FROM radar_a_regulation_review r WHERE r.bbl=a.bbl)) AS missing_reg,
 (SELECT COUNT(*)::int FROM radar_asset_screen s WHERE NOT EXISTS(
  SELECT 1 FROM radar_a_asset_register a WHERE a.bbl=s.bbl)) AS missing_asset,
 (SELECT COUNT(*)::int FROM radar_a_source_catalog WHERE warehouse_last_imported IS NULL) AS missing_sources`;
const r=v[0],errors:string[]=[];
for(const [name,valid] of Object.entries({
 full_source:r.raw_lots===318610,
 candidate_count:r.screened_lots===4436,
 asset_coverage:r.assets===4436,
 regulation_coverage:r.regulation===4436,
 hcr_history:r.hcr===2540,
 hpd_complete:r.hpd===4436,
 dof_complete:r.dof===4436,
 source_hpd_ll7:r.ll7===82,
 source_hpd_speculation:r.spec===31,
 no_unsupported_free_market:r.free_market===0,
 reviews_assigned:r.review_tasks>=8872,
 evidence_registry:r.evidence>=55000,
 no_missing_identity:r.missing_asset===0,
 no_missing_regulation:r.missing_reg===0,
 all_sources_materialized:r.missing_sources===0
})){if(!valid)errors.push(name)}
await db`INSERT INTO radar_a_integrity_watch_runs(
 pass,raw_lots,candidate_lots,asset_identity_coverage,regulation_coverage,
 hpd_success,dof_success,hcr_listed,ll7_matched_lots,speculation_watch_matched_lots,
 free_market_verified,open_review_tasks,source_evidence_rows,errors)
 VALUES(${errors.length===0},${r.raw_lots},${r.screened_lots},${r.assets},${r.regulation},
 ${r.hpd},${r.dof},${r.hcr},${r.ll7},${r.spec},${r.free_market},
 ${r.review_tasks},${r.evidence},((${JSON.stringify(errors)}::jsonb #>> '{}')::jsonb))`;
const last=await db`SELECT source_key,snapshot_label,source_as_of,warehouse_last_imported,
 verification_state,nominal_refresh_days FROM radar_a_source_catalog ORDER BY source_key`;
console.log(JSON.stringify({event:"milestone_a_integrity_watch",pass:errors.length===0,
 metrics:r,failed_gates:errors,catalog:last,
 note:"Hard coverage gates. All legal regulation claims remain unverified pending documentary analyst review."}));
await db.close();
if(errors.length)process.exitCode=1;
