
import {SQL} from "bun";
const db=Bun.env.DATABASE_URL?new SQL(Bun.env.DATABASE_URL):null;
const json=(data:any,status=200)=>new Response(JSON.stringify(data),{status,headers:{"Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store","X-Content-Type-Options":"nosniff","Referrer-Policy":"no-referrer"}});
const authorized=(req:Request)=>!!Bun.env.RADAR_API_KEY&&req.headers.get("authorization")==="Bearer "+Bun.env.RADAR_API_KEY;
const validBBL=(s:any)=>/^[0-9]{10}$/.test(String(s||""));
async function initialize(){
 if(!db)throw Error("Storage unavailable");
 await db`CREATE TABLE IF NOT EXISTS radar_d_acquisition_leads(
  id BIGSERIAL PRIMARY KEY,bbl TEXT NOT NULL UNIQUE REFERENCES radar_asset_screen(bbl),
  pipeline_stage TEXT NOT NULL DEFAULT 'RESEARCH_ONLY',
  acquisition_qualified BOOLEAN NOT NULL DEFAULT FALSE,
  distress_verified BOOLEAN NOT NULL DEFAULT FALSE,
  documentary_maturity_verified BOOLEAN NOT NULL DEFAULT FALSE,
  current_payoff_verified BOOLEAN NOT NULL DEFAULT FALSE,
  regulation_review_verified BOOLEAN NOT NULL DEFAULT FALSE,
  priority_manual SMALLINT NOT NULL DEFAULT 3 CHECK(priority_manual BETWEEN 1 AND 5),
  investment_thesis TEXT NOT NULL,
  evidence_links JSONB NOT NULL DEFAULT '[]'::jsonb,
  next_action TEXT NOT NULL,
  created_by TEXT NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  CHECK(NOT acquisition_qualified OR
   (distress_verified AND documentary_maturity_verified AND
    current_payoff_verified AND regulation_review_verified)))`;
 await db`CREATE TABLE IF NOT EXISTS radar_d_lead_events(
   id BIGSERIAL PRIMARY KEY,lead_id BIGINT NOT NULL REFERENCES radar_d_acquisition_leads(id),
   event_kind TEXT NOT NULL,actor TEXT NOT NULL,
   event_data JSONB NOT NULL DEFAULT '{}'::jsonb,
   created_at TIMESTAMPTZ DEFAULT NOW())`;
 await db`CREATE TABLE IF NOT EXISTS radar_d_professional_contacts(
   id BIGSERIAL PRIMARY KEY,lead_id BIGINT NOT NULL REFERENCES radar_d_acquisition_leads(id),
   professional_name TEXT NOT NULL,public_role TEXT NOT NULL,organization TEXT,
   verified_contact_method BOOLEAN NOT NULL DEFAULT FALSE,
   public_profile_url TEXT NOT NULL,
   relationship_to_recorded_owner TEXT NOT NULL DEFAULT 'NOT_VERIFIED',
   updated_at TIMESTAMPTZ DEFAULT NOW())`;
 await db`CREATE INDEX IF NOT EXISTS radar_d_acq_stage_idx ON radar_d_acquisition_leads(pipeline_stage,priority_manual,updated_at)`;
}
let ready=false;async function setup(){if(!ready){await initialize();ready=true}}
const clean=(x:any,max:number)=>typeof x==="string"?x.trim().slice(0,max):"";
const validUrl=(x:any)=>{try{const v=new URL(x);return v.protocol==="https:"&&!v.username&&!v.password&&v.hostname.includes(".")}catch{return false}};
Bun.serve({port:Number(Bun.env.PORT||3000),async fetch(req:Request){
 const url=new URL(req.url);
 if(url.pathname==="/health")return json({ok:!!db,service:"capital-stack-radar-origination-workflow"},db?200:503);
 if(!authorized(req))return json({error:"Unauthorized"},401);
 try{
  if(!db)return json({error:"Database unavailable"},503);await setup();
  if(url.pathname==="/api/milestone-d/overview"){
   const tally=await db`SELECT
     (SELECT COUNT(*)::int FROM radar_d_acquisition_leads) AS tracked_research_leads,
     (SELECT COUNT(*)::int FROM radar_d_acquisition_leads WHERE acquisition_qualified) AS qualified_acquisitions,
     (SELECT COUNT(*)::int FROM radar_d_professional_contacts) AS public_professional_contacts,
     (SELECT COUNT(*)::int FROM radar_d_lead_events) AS logged_actions,
     (SELECT COUNT(*)::int FROM radar_r22_dossiers) AS financing_research_dossiers,
     (SELECT COUNT(*)::int FROM radar_a_asset_register) AS tax_lot_research_universe`;
   const leads=await db`SELECT d.id,d.bbl,d.pipeline_stage,d.priority_manual,
     d.acquisition_qualified,d.investment_thesis,d.next_action,d.created_by,d.updated_at,
     a.source_address,a.borough,a.residential_units_per_lot,r.review_category,
     r.legal_free_market_certified,
     (SELECT COUNT(*)::int FROM radar_d_professional_contacts c WHERE c.lead_id=d.id) AS sourced_professionals
     FROM radar_d_acquisition_leads d JOIN radar_a_asset_register a ON a.bbl=d.bbl
     JOIN radar_a_regulation_review r ON r.bbl=d.bbl
     ORDER BY d.priority_manual,d.updated_at DESC LIMIT 100`;
   return json({counts:tally[0],leads,
     stage:"RESEARCH_PIPELINE_NOT_VERIFIED_DISTRESSED_ACQUISITIONS",
     external_contacts_currently_verified:false,automated_outreach_sent:false,
     warning:"Property acquisition qualifications require primary-document verification; recorded debt is not a current balance."});
  }
  if(url.pathname==="/api/milestone-d/research-leads"){
   if(req.method==="GET"){
    const list=await db`SELECT id,bbl,pipeline_stage,acquisition_qualified,distress_verified,
      documentary_maturity_verified,current_payoff_verified,regulation_review_verified,
      priority_manual,investment_thesis,evidence_links,next_action,created_by,updated_at
      FROM radar_d_acquisition_leads ORDER BY priority_manual,updated_at DESC LIMIT 200`;
    return json({count:list.length,leads:list});
   }
   if(req.method!=="POST")return json({error:"GET or POST required"},405);
   let v:any;try{v=await req.json()}catch{return json({error:"Valid JSON required"},400)}
   const bbl=String(v?.bbl||""),analyst=clean(v?.analyst,100),
     thesis=clean(v?.thesis,2500),next=clean(v?.next_action,1000);
   if(!validBBL(bbl)||analyst.length<2||thesis.length<25||next.length<10)
    return json({error:"BBL, analyst, concrete thesis and next action required"},400);
   const priority=Number(v?.priority??3);
   if(!Number.isSafeInteger(priority)||priority<1||priority>5)return json({error:"Priority must be 1-5"},400);
   if(!Array.isArray(v?.evidence_links)||v.evidence_links.length<1||v.evidence_links.length>25||
       v.evidence_links.some((x:any)=>!validUrl(x?.url)||!clean(x?.description,300)))
    return json({error:"At least one HTTPS source with explanation required"},400);
   const asset=await db`SELECT 1 FROM radar_a_asset_register WHERE bbl=${bbl}`;
   if(!asset.length)return json({error:"Not in known asset research register"},404);
   const saved=await db`INSERT INTO radar_d_acquisition_leads(
      bbl,priority_manual,investment_thesis,next_action,evidence_links,created_by)
     VALUES(${bbl},${priority},${thesis},${next},${JSON.stringify(v.evidence_links)}::jsonb,${analyst})
     ON CONFLICT(bbl) DO UPDATE SET priority_manual=EXCLUDED.priority_manual,
       investment_thesis=EXCLUDED.investment_thesis,next_action=EXCLUDED.next_action,
       evidence_links=EXCLUDED.evidence_links,updated_at=NOW()
     RETURNING id,bbl,pipeline_stage,acquisition_qualified,priority_manual,updated_at`;
   await db`INSERT INTO radar_d_lead_events(lead_id,event_kind,actor,event_data)
       VALUES(${saved[0].id},'LEAD_RESEARCH_SAVED',${analyst},
         ${JSON.stringify({source_count:v.evidence_links.length,priority})}::jsonb)`;
   return json({lead:saved[0],current_distress_verified:false,
      next_step:"Verify legal property identity, regulation, debt terms and actual operating financials."},201);
  }
  if(url.pathname==="/api/milestone-d/leads/qualify"){
   if(req.method!=="POST")return json({error:"POST required"},405);
   let v:any;try{v=await req.json()}catch{return json({error:"Valid JSON required"},400)}
   if(!validBBL(v.bbl))return json({error:"Valid BBL required"},400);
   const proof=await db`SELECT
      (SELECT legal_free_market_certified FROM radar_a_regulation_review WHERE bbl=${v.bbl}) AS rent_proven,
      (SELECT legal_facility_verified FROM radar_b_document_components
       WHERE bbl=${v.bbl} AND legal_facility_verified LIMIT 1) AS facility_proven,
      (SELECT independent_review_complete FROM radar_c_underwriting_scenarios
       WHERE bbl=${v.bbl} AND independent_review_complete LIMIT 1) AS underwrite_proven`;
   if(!proof[0].rent_proven||!proof[0].facility_proven||!proof[0].underwrite_proven)
     return json({qualified:false,missing:["Verified rent regulation","Audited active loan family","Independently reviewed underwriting"].filter((_,i)=>![proof[0].rent_proven,proof[0].facility_proven,proof[0].underwrite_proven][i]),
       error:"Cannot qualify from unreviewed source records"},409);
   return json({qualified:false,error:"Documentary payoff, maturity, lender authority and property saleability need independent signed-off review"},409);
  }
  if(url.pathname==="/api/milestone-d/contacts"){
   if(req.method==="GET"){
    const bbl=url.searchParams.get("bbl")||"";
    if(!validBBL(bbl))return json({error:"Valid BBL required"},400);
    const rows=await db`SELECT c.id,c.professional_name,c.public_role,c.organization,c.public_profile_url,
      c.verified_contact_method,c.relationship_to_recorded_owner
      FROM radar_d_professional_contacts c JOIN radar_d_acquisition_leads d ON d.id=c.lead_id
      WHERE d.bbl=${bbl} ORDER BY c.id LIMIT 100`;
    return json({bbl,professionals:rows});
   }
   if(req.method!=="POST")return json({error:"GET or POST required"},405);
   let v:any;try{v=await req.json()}catch{return json({error:"Valid JSON required"},400)}
   const bbl=String(v.bbl||""),name=clean(v.name,130),role=clean(v.role,200),
    org=clean(v.organization,180),analyst=clean(v.analyst,100);
   if(!validBBL(bbl)||name.length<3||role.length<3||analyst.length<2||!validUrl(v.public_profile_url))
    return json({error:"Professional name, role, public source and analyst required"},400);
   const lead=await db`SELECT id FROM radar_d_acquisition_leads WHERE bbl=${bbl}`;
   if(!lead.length)return json({error:"Create research lead before professional research"},404);
   const saved=await db`INSERT INTO radar_d_professional_contacts(
    lead_id,professional_name,public_role,organization,public_profile_url)
     VALUES(${lead[0].id},${name},${role},${org},${v.public_profile_url})
     RETURNING id,professional_name,public_role,organization,verified_contact_method`;
   await db`INSERT INTO radar_d_lead_events(lead_id,event_kind,actor,event_data)
     VALUES(${lead[0].id},'PUBLIC_PROFESSIONAL_REFERENCE_ADDED',${analyst},
      ${JSON.stringify({contact_id:saved[0].id,source:v.public_profile_url})}::jsonb)`;
   return json({saved:saved[0],verified_owner_relationship:false,
     warning:"Professional identity source is not proof of owner control or preferred contact method."},201);
  }
  if(url.pathname==="/api/milestone-d/outreach-draft"){
   const bbl=url.searchParams.get("bbl")||"";
   if(!validBBL(bbl))return json({error:"Valid BBL required"},400);
   const records=await db`SELECT d.bbl,d.investment_thesis,d.next_action,d.acquisition_qualified,
      a.source_address,a.residential_units_per_lot
      FROM radar_d_acquisition_leads d JOIN radar_a_asset_register a ON a.bbl=d.bbl WHERE d.bbl=${bbl}`;
   if(!records.length)return json({error:"Research lead not found"},404);
   const x=records[0];
   const address=String(x.source_address||"the property");
   const draft="Subject: Introduction regarding "+address+"\n\nHello,\n\nI work on real estate acquisitions and financing research in New York. I have been reviewing publicly available records associated with "+address+" and would welcome a brief conversation to understand whether there are any current or future investment or financing objectives worth exploring.\n\nI have not verified the property's current financing position, and I'm not assuming any sale interest or distress. Please let me know if there is an appropriate person to contact.\n\nBest regards";
   return json({bbl,draft,mode:"REVIEW_BEFORE_SEND",automatically_sent:false,
     public_record_based:true,unverified_debt_or_sale_inferences_excluded:true});
  }
  return json({error:"Not found"},404);
 }catch(err:any){console.error(JSON.stringify({event:"milestone_d_service_error",path:url.pathname,error:String(err.message)}));
  return json({error:"Service error"},500)}
}});
