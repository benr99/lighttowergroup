
import {SQL} from "bun";
if(!Bun.env.DATABASE_URL)throw Error("DATABASE_URL required");
const db=new SQL(Bun.env.DATABASE_URL);
await db`CREATE TABLE IF NOT EXISTS radar_b_document_reference_edges (
 bbl TEXT NOT NULL REFERENCES radar_r22_dossiers(bbl),
 source_document_id TEXT NOT NULL,target_document_id TEXT NOT NULL,
 source_reference_url TEXT NOT NULL,
 link_basis TEXT NOT NULL,
 target_indexed_for_dossier BOOLEAN NOT NULL DEFAULT FALSE,
 legal_relationship_verified BOOLEAN NOT NULL DEFAULT FALSE,
 updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 PRIMARY KEY(bbl,source_document_id,target_document_id))`;
await db`CREATE TABLE IF NOT EXISTS radar_b_document_components (
 bbl TEXT NOT NULL REFERENCES radar_r22_dossiers(bbl),
 component_research_id TEXT NOT NULL,
 document_count INT NOT NULL,
 explicit_recorded_edges INT NOT NULL,
 latest_recording TIMESTAMPTZ,
 multi_lot_documents INT NOT NULL DEFAULT 0,
 legal_facility_verified BOOLEAN NOT NULL DEFAULT FALSE,
 documented_contractual_maturity DATE,
 current_principal_verified NUMERIC,
 state TEXT NOT NULL DEFAULT 'DOCUMENT_REFERENCE_COMPONENT_LEGAL_REVIEW_REQUIRED',
 generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 PRIMARY KEY(bbl,component_research_id))`;
await db`CREATE TABLE IF NOT EXISTS radar_b_component_members(
 bbl TEXT NOT NULL REFERENCES radar_r22_dossiers(bbl),
 document_id TEXT NOT NULL,component_research_id TEXT NOT NULL,
 source_record_url TEXT NOT NULL,
 PRIMARY KEY(bbl,document_id))`;
await db`CREATE TABLE IF NOT EXISTS radar_b_milestone_checks(
 id BIGSERIAL PRIMARY KEY,passed BOOLEAN,
 dossiers INT,events INT,edges INT,components INT,
 matched_edges INT,documents_without_full_reference_review INT,
 maturity_claims_verified INT,principal_verified_count INT,
 explanatory_notes TEXT,checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW())`;
let totalEvents=0,totalGroups=0,totalEdges=0,matched=0;
const dossiers=await db`SELECT bbl,priority_order,address FROM radar_r22_dossiers ORDER BY priority_order`;
for(const d of dossiers){
 const bbl=String(d.bbl);
 const docs=await db`SELECT document_id,recorded_datetime,doc_type,source_master_url,
    collateral_lots FROM radar_r22_document_events WHERE bbl=${bbl}`;
 const set=new Set(docs.map((x:any)=>String(x.document_id)));
 const crfnDocs=await db`SELECT e.document_id,e.crfn FROM radar_r22_document_events e
    WHERE e.bbl=${bbl} AND e.crfn IS NOT NULL AND trim(e.crfn)<>''`;
 const crfnMap=new Map(crfnDocs.map((x:any)=>[String(x.crfn),String(x.document_id)]));
 const references=await db`SELECT e.document_id AS source_document_id,c.referenced_document_id,
    c.reference_crfn,c.source_url
    FROM radar_r22_document_events e JOIN radar_r22_crossrefs c
    ON c.source_document_id=e.document_id WHERE e.bbl=${bbl}`;
 await db`DELETE FROM radar_b_document_reference_edges WHERE bbl=${bbl}`;
 const edges:any[]=[];
 for(const r of references){
    const sourceId=String(r.source_document_id);
    const exactId=r.referenced_document_id?String(r.referenced_document_id):null;
    const crfn=r.reference_crfn?String(r.reference_crfn):null;
    const target=exactId||(crfn?crfnMap.get(crfn):null);
    if(!target||! /^[A-Za-z0-9_-]{1,80}$/.test(target)||target===sourceId)continue;
    const inDossier=set.has(target);
    const basis=exactId?'ACRIS_EXPLICIT_REFERENCED_DOCUMENT_ID':'ACRIS_REFERENCE_CRFN_MATCH';
    await db`INSERT INTO radar_b_document_reference_edges(
      bbl,source_document_id,target_document_id,source_reference_url,
      link_basis,target_indexed_for_dossier)
      VALUES(${bbl},${sourceId},${target},${r.source_url},${basis},${inDossier})
      ON CONFLICT(bbl,source_document_id,target_document_id) DO UPDATE SET
      updated_at=NOW(),link_basis=EXCLUDED.link_basis,
      target_indexed_for_dossier=EXCLUDED.target_indexed_for_dossier`;
    edges.push({source:sourceId,target,inside:inDossier});
 }
 const parent=new Map([...set].map(k=>[k,k]));
 const find=(id:string):string=>{let p=parent.get(id)||id;while(p!==parent.get(p)){const n=parent.get(p);if(!n)break;p=n;}let curr=id;while(parent.get(curr)!==p){const n=parent.get(curr)!;parent.set(curr,p);curr=n;}return p;};
 const union=(x:string,y:string)=>{const a=find(x),b=find(y);if(a!==b)parent.set(a<b?b:a,a<b?a:b)};
 for(const edge of edges)if(edge.inside)union(edge.source,edge.target);
 const components=new Map<string,string[]>();
 for(const id of set){const root=find(id);const list=components.get(root)||[];list.push(id);components.set(root,list)}
 await db`DELETE FROM radar_b_component_members WHERE bbl=${bbl}`;
 await db`DELETE FROM radar_b_document_components WHERE bbl=${bbl}`;
 const byId=new Map(docs.map((x:any)=>[String(x.document_id),x]));
 let caseMatched=0;
 for(const [_,members] of components){
    members.sort();const id="COMP:"+members[0];
    const links=edges.filter(x=>x.inside&&members.includes(x.source)&&members.includes(x.target));
    const last=members.map(x=>byId.get(x)?.recorded_datetime).filter(Boolean)
      .map(x=>new Date(x).valueOf()).reduce((m,n)=>Math.max(m,n),0);
    const multi=members.filter(x=>Number(byId.get(x)?.collateral_lots||0)>1).length;
    await db`INSERT INTO radar_b_document_components(
       bbl,component_research_id,document_count,explicit_recorded_edges,
       latest_recording,multi_lot_documents)
       VALUES(${bbl},${id},${members.length},${links.length},
       ${last?new Date(last):null},${multi})`;
    for(const doc of members){
       const link=byId.get(doc)?.source_master_url||"https://data.cityofnewyork.us/resource/bnx9-e6tj.json";
       await db`INSERT INTO radar_b_component_members(bbl,document_id,component_research_id,source_record_url)
         VALUES(${bbl},${doc},${id},${link})`;
    }
    caseMatched+=links.length;
 }
 totalEvents+=docs.length;totalGroups+=components.size;totalEdges+=edges.length;matched+=caseMatched;
 console.log(JSON.stringify({event:"milestone_b_dossier_graph_materialized",bbl,document_events:docs.length,
   explicit_reference_edges:edges.length,matching_in_case:caseMatched,
   preliminary_components:components.size,verified_current_facilities:0}));
}
const metrics=await db`SELECT
  (SELECT COUNT(*)::int FROM radar_r22_dossiers) AS dossiers,
  (SELECT COUNT(*)::int FROM radar_r22_document_events) AS events,
  (SELECT COUNT(*)::int FROM radar_b_document_reference_edges) AS edges,
  (SELECT COUNT(*)::int FROM radar_b_document_reference_edges WHERE target_indexed_for_dossier) AS matched_edges,
  (SELECT COUNT(*)::int FROM radar_b_document_components) AS components,
  (SELECT COUNT(*)::int FROM radar_b_component_members) AS members,
  (SELECT COUNT(*)::int FROM radar_r22_document_events d
     WHERE NOT EXISTS(SELECT 1 FROM radar_r22_refchecks c WHERE c.document_id=d.document_id AND c.source_complete)) AS unchecked,
  (SELECT COUNT(*)::int FROM radar_b_document_components WHERE legal_facility_verified) AS verified_facilities,
  (SELECT COUNT(*)::int FROM radar_b_document_components WHERE documented_contractual_maturity IS NOT NULL) AS verified_maturity,
  (SELECT COUNT(*)::int FROM radar_b_document_components WHERE current_principal_verified IS NOT NULL) AS verified_principal`;
const v=metrics[0];
const passed=v.dossiers===10&&v.events===v.members&&v.events>=450&&
  v.verified_facilities===0&&v.verified_maturity===0&&v.verified_principal===0;
await db`INSERT INTO radar_b_milestone_checks(passed,dossiers,events,edges,components,matched_edges,
    documents_without_full_reference_review,maturity_claims_verified,principal_verified_count,explanatory_notes)
 VALUES(${passed},${v.dossiers},${v.events},${v.edges},${v.components},
    ${v.matched_edges},${v.unchecked},${v.verified_maturity},${v.verified_principal},
    'Reference components are research-only; no live obligations or borrower/creditor relationships certified')`;
console.log(JSON.stringify({event:"milestone_b_loan_graph_integrity",passed,metrics:v,
 caveat:"Connected components of indexed references are NOT legally reconstructed loan families. Unchecked documents and multi-lot collateral remain material gaps."}));
await db.close();
if(!passed)process.exitCode=1;
