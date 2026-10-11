
import {SQL} from "bun";
if(!Bun.env.DATABASE_URL)throw Error("DATABASE_URL required");
const db=new SQL(Bun.env.DATABASE_URL);
const runName="MILESTONE_A_V1";
const now=()=>new Date().toISOString();
try{
  await db`CREATE TABLE IF NOT EXISTS radar_a_schema_migrations (
   version TEXT PRIMARY KEY,applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),notes TEXT NOT NULL)`;
  await db`INSERT INTO radar_a_schema_migrations(version,notes)
   VALUES('2026_10_11_a1','Conservative economic-asset hypotheses and evidence-based regulation review')
   ON CONFLICT(version) DO NOTHING`;
  await db`CREATE TABLE IF NOT EXISTS radar_a_asset_register (
   bbl TEXT PRIMARY KEY REFERENCES radar_asset_screen(bbl),
   asset_research_id TEXT NOT NULL UNIQUE,borough TEXT NOT NULL,
   source_address TEXT,pluto_owner_name TEXT,
   residential_units_per_lot INT,screen_type TEXT NOT NULL,
   primary_bin TEXT,bin_count INT NOT NULL DEFAULT 0,
   physical_group_id TEXT,shared_bin_lot_count INT NOT NULL DEFAULT 0,
   hpd_building_count INT NOT NULL DEFAULT 0,
   ownership_verification TEXT NOT NULL DEFAULT 'NOT_VERIFIED',
   legal_economic_asset_verification TEXT NOT NULL DEFAULT 'NOT_VERIFIED',
   rent_unit_count_verified BOOLEAN NOT NULL DEFAULT FALSE,
   identity_triage TEXT NOT NULL,
   analyst_exception BOOLEAN NOT NULL DEFAULT TRUE,
   source_pluto_url TEXT,as_of TIMESTAMPTZ NOT NULL DEFAULT NOW(),
   CHECK(asset_research_id LIKE 'LOT:%'))`;
  await db`CREATE INDEX IF NOT EXISTS radar_a_asset_register_physical_idx
    ON radar_a_asset_register(physical_group_id)`;
  await db`CREATE TABLE IF NOT EXISTS radar_a_physical_link_clusters (
   physical_group_id TEXT PRIMARY KEY,
   linked_candidate_lots INT NOT NULL,confirmed_borough TEXT NOT NULL,
   relation_type TEXT NOT NULL,
   legal_common_ownership_confirmed BOOLEAN NOT NULL DEFAULT FALSE,
   units_should_be_aggregated BOOLEAN NOT NULL DEFAULT FALSE,
   status TEXT NOT NULL DEFAULT 'MANUAL_REVIEW_REQUIRED',
   refreshed_at TIMESTAMPTZ NOT NULL DEFAULT NOW())`;
  await db`CREATE TABLE IF NOT EXISTS radar_a_regulation_review (
   bbl TEXT PRIMARY KEY REFERENCES radar_asset_screen(bbl),
   evidence_level TEXT NOT NULL DEFAULT 'PRELIMINARY_SOURCE_SCREEN',
   historical_hcr_2024 BOOLEAN NOT NULL DEFAULT FALSE,
   dof_exemption_record_count INT NOT NULL DEFAULT 0,
   hpd_checked BOOLEAN NOT NULL DEFAULT FALSE,
   dof_checked BOOLEAN NOT NULL DEFAULT FALSE,
   pluto_construction_year INT,pluto_condo_coop_indicator BOOLEAN NOT NULL DEFAULT FALSE,
   review_category TEXT NOT NULL,
   current_unit_level_regulation TEXT NOT NULL DEFAULT 'UNRESOLVED',
   legal_free_market_certified BOOLEAN NOT NULL DEFAULT FALSE,
   sources_to_check JSONB NOT NULL DEFAULT '[]'::jsonb,
   review_flags JSONB NOT NULL DEFAULT '[]'::jsonb,
   last_screened TIMESTAMPTZ NOT NULL DEFAULT NOW())`;
  await db`CREATE TABLE IF NOT EXISTS radar_a_evidence (
   bbl TEXT NOT NULL REFERENCES radar_asset_screen(bbl),
   evidence_type TEXT NOT NULL,source_record_id TEXT NOT NULL,
   source_url TEXT NOT NULL,
   source_year INT,evidence_interpretation TEXT NOT NULL,
   provenance JSONB NOT NULL DEFAULT '{}'::jsonb,
   last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
   PRIMARY KEY(bbl,evidence_type,source_record_id))`;
  await db`CREATE INDEX IF NOT EXISTS radar_a_evidence_type_idx ON radar_a_evidence(evidence_type,bbl)`;
  await db`CREATE TABLE IF NOT EXISTS radar_a_review_items (
    bbl TEXT NOT NULL REFERENCES radar_asset_screen(bbl),
    review_kind TEXT NOT NULL,priority INT NOT NULL,
    reason TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'OPEN',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_checked TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY(bbl,review_kind))`;
  await db`CREATE TABLE IF NOT EXISTS radar_a_acceptance_runs (
    id BIGSERIAL PRIMARY KEY,
    status TEXT NOT NULL,raw_tax_lots INT,candidate_lots INT,
    asset_research_rows INT,regulatory_reviews INT,
    assets_with_review_exception INT,hcr_matched_candidates INT,
    unlisted_hcr_candidates INT,physical_link_clusters INT,
    source_hpd_checked INT,source_dof_checked INT,
    uncovered_candidate_lots INT,unsupported_free_market_claims INT,
    failure_detail TEXT,created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())`;
  await db`UPDATE radar_asset_screen s SET
    hpd_checked=coalesce(hc.status='success',false),
    dof_checked=coalesce(dc.status='success',false),
    hpd_buildings=coalesce(h.buildings,0),
    hpd_distinct_bins=coalesce(h.bins,0),
    dof_exemption_records=coalesce(d.records,0)
    FROM radar_pluto_raw r
    LEFT JOIN radar_hpd_checks hc ON hc.bbl=r.bbl
    LEFT JOIN radar_dof_exemption_checks dc ON dc.bbl=r.bbl
    LEFT JOIN (SELECT bbl,COUNT(DISTINCT building_id)::int AS buildings,
      COUNT(DISTINCT NULLIF(trim(bin),''))::int AS bins FROM radar_hpd_buildings GROUP BY bbl) h ON h.bbl=r.bbl
    LEFT JOIN (SELECT bbl,COUNT(*)::int AS records FROM radar_dof_exemptions GROUP BY bbl) d ON d.bbl=r.bbl
    WHERE r.bbl=s.bbl AND r.unitsres>=70`;
  const srcChecks=await db`SELECT
    (SELECT COUNT(*)::int FROM radar_asset_screen) AS candidates,
    (SELECT COUNT(*)::int FROM radar_hpd_checks c JOIN radar_asset_screen s ON s.bbl=c.bbl WHERE c.status='success') AS hpd_success,
    (SELECT COUNT(*)::int FROM radar_hpd_checks c JOIN radar_asset_screen s ON s.bbl=c.bbl WHERE c.status='partial') AS hpd_partial,
    (SELECT COUNT(*)::int FROM radar_hpd_checks c JOIN radar_asset_screen s ON s.bbl=c.bbl WHERE c.status='error') AS hpd_error,
    (SELECT COUNT(*)::int FROM radar_dof_exemption_checks c JOIN radar_asset_screen s ON s.bbl=c.bbl WHERE c.status='success') AS dof_success,
    (SELECT COUNT(*)::int FROM radar_dof_exemption_checks c JOIN radar_asset_screen s ON s.bbl=c.bbl WHERE c.status='partial') AS dof_partial,
    (SELECT COUNT(*)::int FROM radar_dof_exemption_checks c JOIN radar_asset_screen s ON s.bbl=c.bbl WHERE c.status='error') AS dof_error`;
  console.log(JSON.stringify({event:"milestone_a_source_enrichment_status_reconciled",coverage:srcChecks[0]}));
  const source=await db`SELECT borough,COUNT(*)::int AS stored_lots,
    COUNT(*) FILTER(WHERE unitsres>=70)::int AS candidate_lots
    FROM radar_pluto_raw GROUP BY borough ORDER BY borough`;
  if(source.length!==2||source.find((r:any)=>r.borough==='MN')?.stored_lots!==42504||
     source.find((r:any)=>r.borough==='BK')?.stored_lots!==276106)
    throw Error("Source PLUTO counts unexpected; abandon asset registry rebuild");
  const hcr=await db`SELECT borough,COUNT(*)::int AS listed_bbls
    FROM radar_hcr_2024_registrations GROUP BY borough ORDER BY borough`;
  if(hcr.find((r:any)=>r.borough==='BK')?.listed_bbls!==16926||
     hcr.find((r:any)=>r.borough==='MN')?.listed_bbls!==13729)
    throw Error("HCR source counts unexpectedly changed");
  const prepare=await db`WITH hpd AS (
     SELECT bbl,COUNT(DISTINCT building_id)::int AS building_count,
       COUNT(DISTINCT NULLIF(trim(bin),'')) FILTER (WHERE trim(coalesce(bin,'')) ~ '^[0-9]{7}$')::int AS bin_count,
       MIN(bin) FILTER(WHERE trim(coalesce(bin,'')) ~ '^[0-9]{7}$') AS only_bin
     FROM radar_hpd_buildings GROUP BY bbl
   ),bin_refs AS (
     SELECT bin,COUNT(DISTINCT bbl)::int AS linked_lots
     FROM radar_hpd_buildings
     WHERE trim(coalesce(bin,'')) ~ '^[0-9]{7}$'
     GROUP BY bin)
   INSERT INTO radar_a_asset_register(
    bbl,asset_research_id,borough,source_address,pluto_owner_name,
    residential_units_per_lot,screen_type,primary_bin,bin_count,
    physical_group_id,shared_bin_lot_count,hpd_building_count,identity_triage,
    analyst_exception,source_pluto_url,as_of)
   SELECT s.bbl,'LOT:'||s.bbl,s.borough,
     r.raw->>'address',r.raw->>'ownername',s.unitsres,s.screen_status,
     CASE WHEN coalesce(h.bin_count,0)=1 THEN h.only_bin ELSE NULL END,
     coalesce(h.bin_count,0),
     CASE WHEN coalesce(h.bin_count,0)=1 THEN 'BIN:'||h.only_bin ELSE NULL END,
     CASE WHEN coalesce(h.bin_count,0)=1 THEN coalesce(br.linked_lots,0) ELSE 0 END,
     coalesce(h.building_count,0),
     CASE WHEN s.condo_flag OR s.coop_flag THEN 'CONDO_COOP_ECONOMIC_IDENTITY_EXCEPTION'
      WHEN coalesce(h.bin_count,0)>1 THEN 'MULTIPLE_PHYSICAL_BUILDINGS_PER_TAX_LOT'
      WHEN coalesce(h.bin_count,0)=0 AND s.hpd_checked THEN 'NO_VALID_HPD_BIN_AFTER_CHECK'
      WHEN coalesce(h.bin_count,0)=0 THEN 'HPD_IDENTITY_NOT_YET_COLLECTED'
      WHEN coalesce(br.linked_lots,0)>1 THEN 'SHARED_BIN_MULTIPLE_TAX_LOTS_REVIEW'
      ELSE 'SINGLE_BIN_LOT_LEVEL_ONLY_NOT_ECONOMICALLY_VERIFIED' END,
     TRUE,r.source_url,NOW()
   FROM radar_asset_screen s
   JOIN radar_pluto_raw r ON r.bbl=s.bbl
   LEFT JOIN hpd h ON h.bbl=s.bbl
   LEFT JOIN bin_refs br ON br.bin=h.only_bin AND h.bin_count=1
   ON CONFLICT(bbl) DO UPDATE SET borough=EXCLUDED.borough,
    source_address=EXCLUDED.source_address,pluto_owner_name=EXCLUDED.pluto_owner_name,
    residential_units_per_lot=EXCLUDED.residential_units_per_lot,
    screen_type=EXCLUDED.screen_type,primary_bin=EXCLUDED.primary_bin,bin_count=EXCLUDED.bin_count,
    physical_group_id=EXCLUDED.physical_group_id,shared_bin_lot_count=EXCLUDED.shared_bin_lot_count,
    hpd_building_count=EXCLUDED.hpd_building_count,identity_triage=EXCLUDED.identity_triage,
    source_pluto_url=EXCLUDED.source_pluto_url,as_of=NOW()`;
  console.log(JSON.stringify({event:"milestone_a_asset_register_created",stage:"asset_screen_upsert_done"}));
  await db`INSERT INTO radar_a_physical_link_clusters(
    physical_group_id,linked_candidate_lots,confirmed_borough,relation_type,
    refreshed_at)
   SELECT physical_group_id,COUNT(*)::int,MIN(borough),
     'SHARED_HPD_BIN_PHYSCIAL_LINK_NOT_COMMON_OWNERSHIP',NOW()
   FROM radar_a_asset_register WHERE physical_group_id IS NOT NULL
   GROUP BY physical_group_id HAVING COUNT(*)>1
   ON CONFLICT(physical_group_id) DO UPDATE
   SET linked_candidate_lots=EXCLUDED.linked_candidate_lots,refreshed_at=NOW()`;
  console.log(JSON.stringify({event:"milestone_a_physical_links_refreshed"}));
  await db`INSERT INTO radar_a_regulation_review(
    bbl,historical_hcr_2024,dof_exemption_record_count,hpd_checked,
    dof_checked,pluto_construction_year,pluto_condo_coop_indicator,
    review_category,sources_to_check,review_flags,last_screened)
   SELECT s.bbl,h.bbl IS NOT NULL,s.dof_exemption_records,s.hpd_checked,s.dof_checked,
     s.yearbuilt,(s.condo_flag OR s.coop_flag),
     CASE WHEN s.condo_flag OR s.coop_flag THEN 'SPECIAL_LEGAL_FORM_REVIEW'
      WHEN h.bbl IS NOT NULL THEN 'HCR_2024_REGISTRATION_HISTORY'
      WHEN s.yearbuilt IS NULL OR s.yearbuilt=0 THEN 'UNKNOWN_BUILD_YEAR_REVIEW'
      WHEN s.yearbuilt<1974 THEN 'POSSIBLE_HISTORICAL_RENT_REGULATION'
      WHEN s.dof_exemption_records>0 THEN 'DOF_EXEMPTION_LEGAL_REVIEW'
      ELSE 'POST_1973_UNLISTED_RESTRICTIONS_NOT_VERIFIED' END,
     jsonb_build_array('HCR_UNIT_LEVEL_HISTORY','HPD_REGULATORY_AGREEMENTS',
       'DOF_PROPERTY_TAX_INCENTIVES','CONDO_COOP_PLANS','CURRENT_LEASES'),
     jsonb_build_array(
       CASE WHEN h.bbl IS NOT NULL THEN 'HISTORICAL_HCR_LIST_MATCH'
            ELSE 'ABSENCE_NOT_PROOF_OF_UNRESTRICTED_RENT' END,
       CASE WHEN s.hpd_checked THEN 'HPD_COLLECTION_ATTEMPTED' ELSE 'HPD_COLLECTION_OUTSTANDING' END,
       CASE WHEN s.dof_checked THEN 'DOF_COLLECTION_ATTEMPTED' ELSE 'DOF_COLLECTION_OUTSTANDING' END,
       CASE WHEN s.dof_exemption_records>0 THEN 'DOF_EXEMPTION_RECORDS_REQUIRE_BENEFIT_INTERPRETATION'
            ELSE 'NO_MATCHING_DOF_EXEMPTION_IN_COLLECTED_SOURCE' END,
       CASE WHEN s.condo_flag OR s.coop_flag THEN 'CONDO_COOP_NOT_AUTOMATICALLY_RENTAL_ASSET'
            ELSE 'ECONOMIC_RENTAL_STATUS_NOT_VERIFIED' END),NOW()
   FROM radar_asset_screen s LEFT JOIN radar_hcr_2024_registrations h ON h.bbl=s.bbl
   ON CONFLICT(bbl) DO UPDATE SET
     historical_hcr_2024=EXCLUDED.historical_hcr_2024,
     dof_exemption_record_count=EXCLUDED.dof_exemption_record_count,
     hpd_checked=EXCLUDED.hpd_checked,dof_checked=EXCLUDED.dof_checked,
     pluto_construction_year=EXCLUDED.pluto_construction_year,
     pluto_condo_coop_indicator=EXCLUDED.pluto_condo_coop_indicator,
     review_category=EXCLUDED.review_category,
     sources_to_check=EXCLUDED.sources_to_check,review_flags=EXCLUDED.review_flags,
     last_screened=NOW()`;
  console.log(JSON.stringify({event:"milestone_a_regulation_triage_done"}));
  await db`INSERT INTO radar_a_evidence(bbl,evidence_type,source_record_id,source_url,
    source_year,evidence_interpretation,provenance,last_seen)
   SELECT s.bbl,'PLUTO_UNITS_AND_LOT','PLUTO:'||s.bbl,r.source_url,2026,
     'Tax lot geometry and residential units only, not an independently validated rental asset',
     jsonb_build_object('unitsres',s.unitsres,'landuse',s.landuse,'buildingclass',s.bldgclass,'yearbuilt',s.yearbuilt),NOW()
   FROM radar_asset_screen s JOIN radar_pluto_raw r ON r.bbl=s.bbl
   ON CONFLICT(bbl,evidence_type,source_record_id) DO UPDATE SET
    provenance=EXCLUDED.provenance,last_seen=NOW()`;
  await db`INSERT INTO radar_a_evidence(bbl,evidence_type,source_record_id,source_url,
    source_year,evidence_interpretation,provenance,last_seen)
   SELECT h.bbl,'HCR_2024_REGISTERED_BUILDING','HCR2024:'||h.bbl,h.source_pdf_url,2024,
      'Appears on historical list; not unit count or current rent status verification',
      jsonb_build_object('pdf_pages',h.source_pages,'source_pdf_sha256',h.source_pdf_sha256),NOW()
   FROM radar_hcr_2024_registrations h JOIN radar_asset_screen s ON s.bbl=h.bbl
   ON CONFLICT(bbl,evidence_type,source_record_id) DO UPDATE SET
     provenance=EXCLUDED.provenance,last_seen=NOW()`;
  await db`INSERT INTO radar_a_evidence(bbl,evidence_type,source_record_id,source_url,
    evidence_interpretation,provenance,last_seen)
   SELECT b.bbl,'HPD_BUILDING_ID','HPD:'||b.building_id,b.source_url,
     'HPD building jurisdiction and identifier record; neither unit regulation nor economic asset verification',
     jsonb_build_object('buildingid',b.building_id,'bin',b.bin,'address',CONCAT_WS(' ',b.house_number,b.street_name)),NOW()
   FROM radar_hpd_buildings b JOIN radar_asset_screen s ON s.bbl=b.bbl
   ON CONFLICT(bbl,evidence_type,source_record_id) DO UPDATE SET
    provenance=EXCLUDED.provenance,last_seen=NOW()`;
  await db`INSERT INTO radar_a_evidence(bbl,evidence_type,source_record_id,source_url,
    evidence_interpretation,provenance,last_seen)
   SELECT x.bbl,'DOF_EXEMPTION','DOF:'||x.record_key,x.source_url,
    'Property tax exemption entry; identify benefit before inferring rent restrictions',
    jsonb_build_object('exemption_code',x.exemption_code,
     'assessment_year',x.assessment_year,'nys_exemption_code',x.nys_exemption_code),NOW()
   FROM radar_dof_exemptions x JOIN radar_asset_screen s ON s.bbl=x.bbl
   ON CONFLICT(bbl,evidence_type,source_record_id) DO UPDATE SET
    provenance=EXCLUDED.provenance,last_seen=NOW()`;
  console.log(JSON.stringify({event:"milestone_a_evidence_ledger_done"}));
  await db`INSERT INTO radar_a_review_items(bbl,review_kind,priority,reason,last_checked)
   SELECT a.bbl,'ECONOMIC_ASSET_IDENTITY',
    CASE WHEN a.identity_triage IN ('SHARED_BIN_MULTIPLE_TAX_LOTS_REVIEW','MULTIPLE_PHYSICAL_BUILDINGS_PER_TAX_LOT') THEN 1
         WHEN a.identity_triage='CONDO_COOP_ECONOMIC_IDENTITY_EXCEPTION' THEN 2 ELSE 3 END,
    a.identity_triage,NOW() FROM radar_a_asset_register a
   ON CONFLICT(bbl,review_kind) DO UPDATE SET
    priority=EXCLUDED.priority,reason=EXCLUDED.reason,last_checked=NOW()`;
  await db`INSERT INTO radar_a_review_items(bbl,review_kind,priority,reason,last_checked)
    SELECT x.bbl,'LEGAL_RENT_STATUS',
      CASE WHEN x.historical_hcr_2024 THEN 1
      WHEN x.pluto_construction_year<1974 THEN 2 ELSE 3 END,
      x.review_category,NOW() FROM radar_a_regulation_review x
    ON CONFLICT(bbl,review_kind) DO UPDATE SET
     priority=EXCLUDED.priority,reason=EXCLUDED.reason,last_checked=NOW()`;
  const report=await db`SELECT
    (SELECT COUNT(*)::int FROM radar_pluto_raw) AS raw_lots,
    (SELECT COUNT(*)::int FROM radar_asset_screen) AS screened_lots,
    (SELECT COUNT(*)::int FROM radar_a_asset_register) AS asset_rows,
    (SELECT COUNT(*)::int FROM radar_a_regulation_review) AS regulation_rows,
    (SELECT COUNT(*)::int FROM radar_a_asset_register WHERE analyst_exception) AS exceptions,
    (SELECT COUNT(*)::int FROM radar_a_regulation_review WHERE historical_hcr_2024) AS hcr_listed,
    (SELECT COUNT(*)::int FROM radar_a_regulation_review WHERE NOT historical_hcr_2024) AS unlisted,
    (SELECT COUNT(*)::int FROM radar_a_physical_link_clusters) AS physical_link_clusters,
    (SELECT COUNT(*)::int FROM radar_a_regulation_review WHERE hpd_checked) AS hpd_checked,
    (SELECT COUNT(*)::int FROM radar_a_regulation_review WHERE dof_checked) AS dof_checked,
    (SELECT COUNT(*)::int FROM radar_asset_screen s WHERE NOT EXISTS
      (SELECT 1 FROM radar_a_asset_register a WHERE a.bbl=s.bbl)
      OR NOT EXISTS(SELECT 1 FROM radar_a_regulation_review r WHERE r.bbl=s.bbl)
      OR NOT EXISTS(SELECT 1 FROM radar_a_review_items q WHERE q.bbl=s.bbl AND q.review_kind='ECONOMIC_ASSET_IDENTITY')
      OR NOT EXISTS(SELECT 1 FROM radar_a_review_items q WHERE q.bbl=s.bbl AND q.review_kind='LEGAL_RENT_STATUS')
     ) AS uncovered,
    (SELECT COUNT(*)::int FROM radar_a_regulation_review WHERE legal_free_market_certified) AS unsupported_free_market,
    (SELECT COUNT(*)::int FROM radar_a_evidence) AS source_evidence_records`;
  const v=report[0];
  if(v.raw_lots!==318610||v.screened_lots!==4436||v.asset_rows!==4436||
     v.regulation_rows!==4436||v.exceptions!==4436||v.uncovered!==0||
     v.hcr_listed+v.unlisted!==4436||v.unsupported_free_market!==0||
     v.source_evidence_records<4436)
   throw Error("Milestone A invariant failed: "+JSON.stringify(v));
  await db`INSERT INTO radar_a_acceptance_runs(
   status,raw_tax_lots,candidate_lots,asset_research_rows,regulatory_reviews,
   assets_with_review_exception,hcr_matched_candidates,unlisted_hcr_candidates,
   physical_link_clusters,source_hpd_checked,source_dof_checked,
   uncovered_candidate_lots,unsupported_free_market_claims)
   VALUES('passed',${v.raw_lots},${v.screened_lots},${v.asset_rows},
    ${v.regulation_rows},${v.exceptions},${v.hcr_listed},${v.unlisted},
    ${v.physical_link_clusters},${v.hpd_checked},${v.dof_checked},
    ${v.uncovered},${v.unsupported_free_market})`;
  const dist=await db`SELECT review_category,COUNT(*)::int AS lots FROM radar_a_regulation_review
    GROUP BY review_category ORDER BY lots DESC`;
  const identity=await db`SELECT identity_triage,COUNT(*)::int AS lots FROM radar_a_asset_register
    GROUP BY identity_triage ORDER BY lots DESC`;
  console.log(JSON.stringify({event:"milestone_a_asset_and_regulation_gate_passed",report:v,
    regulation_categories:dist,identity_categories:identity,
    disclosure:"Asset IDs are stable lot-level RESEARCH records. Economic boundaries and free-market legal eligibility remain UNVERIFIED."}));
}catch(err:any){
  console.error(JSON.stringify({event:"milestone_a_asset_and_regulation_gate_failed",message:String(err.stack||err.message)}));
  process.exitCode=1;
}
await db.close();
