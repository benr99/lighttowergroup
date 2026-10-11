
import {SQL} from "bun";
const db=Bun.env.DATABASE_URL?new SQL(Bun.env.DATABASE_URL):null;
const response=(x:any,status=200)=>new Response(JSON.stringify(x),{status,headers:{"Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store","X-Content-Type-Options":"nosniff","Referrer-Policy":"no-referrer"}});
const authenticated=(req:Request)=>!!Bun.env.RADAR_API_KEY&&req.headers.get("authorization")==="Bearer "+Bun.env.RADAR_API_KEY;
const number=(d:any,k:string,min:number,max:number,required=true)=>{
 const x=d?.[k];
 if(!required&&(x==null||x===""))return null;
 if(typeof x!=="number"||!Number.isFinite(x)||x<min||x>max)throw Error(k+" must be a finite number from "+min+" to "+max);
 return x;
};
function calculate(input:any){
 const noi=number(input,"annual_noi",1000,1e9),price=number(input,"purchase_price",10000,1e10),
  ltv=number(input,"max_ltv",0.1,0.85),dscr=number(input,"min_dscr",1,2.5),
  yieldMin=number(input,"min_debt_yield",0.04,0.25),
  rate=number(input,"annual_interest_rate",0.01,0.25),
  amort=number(input,"amortization_years",5,40),
  exitCap=number(input,"exit_cap_rate",0.02,0.25),
  noiGrowth=number(input,"annual_noi_growth",-0.12,0.20),
  initialCapex=number(input,"initial_capex",0,1e9),
  annualCapex=number(input,"annual_capex",0,1e8),
  salesCost=number(input,"exit_sales_cost_rate",0,0.12),
  acquisitionCost=number(input,"acquisition_cost_rate",0,0.12),
  financingCost=number(input,"financing_cost_rate",0,0.12),
  hold=number(input,"hold_years",1,15),
  assumedPayoff=number(input,"assumed_existing_payoff",0,1e10,false),
  refinanceCosts=number(input,"refinance_costs",0,1e9,false)??0;
 if(!Number.isInteger(amort)||!Number.isInteger(hold))throw Error("Hold and amortization years must be whole numbers");
 if(input.interest_only!==undefined&&typeof input.interest_only!=="boolean")throw Error("interest_only must be boolean");
 const monthly=rate/12,N=12*amort;
 const constant=input.interest_only?rate:12*monthly/(1-Math.pow(1+monthly,-N));
 const debtLimits={ltv:price*ltv,dscr:noi/(dscr*constant),debt_yield:noi/yieldMin};
 const newDebt=Math.min(...Object.values(debtLimits));
 const limiting=Object.entries(debtLimits).filter(([_,v])=>Math.abs(v-newDebt)<=Math.max(0.01,newDebt*1e-10)).map(([k])=>k);
 const initialEquity=price+initialCapex+price*acquisitionCost+newDebt*financingCost-newDebt;
 let balance=newDebt,operatingNoi=noi;
 const cashflows=[-initialEquity],details:any[]=[];
 for(let year=1;year<=hold;year++){
  const annualService=constant*newDebt;
  if(!input.interest_only){
   for(let m=0;m<12;m++){const interest=balance*monthly;const principal=Math.max(0,annualService/12-interest);balance=Math.max(0,balance-principal)}
  }
  const annualOperations=operatingNoi-annualService-annualCapex;
  let exitNet=null;
  if(year===hold){
   const nextNoi=operatingNoi*(1+noiGrowth),sale=nextNoi/exitCap;
   exitNet=sale*(1-salesCost)-balance;
  }
  const total=annualOperations+(exitNet??0);
  details.push({year,noi:operatingNoi,debt_service:annualService,annual_capex:annualCapex,
    remaining_debt:balance,operating_cash_flow:annualOperations,exit_net_after_debt:exitNet,
    equity_cash_flow:total});
  cashflows.push(total);
  operatingNoi*=1+noiGrowth;
 }
 const npv=(r:number)=>cashflows.reduce((v,cf,i)=>v+cf/Math.pow(1+r,i),0);
 let irr:number|null=null;
 let lower=-0.95,upper=5;
 if(npv(lower)>0&&npv(upper)<0){for(let i=0;i<130;i++){const mid=(lower+upper)/2;if(npv(mid)>0)lower=mid;else upper=mid}irr=(lower+upper)/2}
 const netProceeds=cashflows.slice(1).reduce((n,x)=>n+x,0);
 const minNoi=noi/constant/newDebt;
 const gap=assumedPayoff==null?null:assumedPayoff+refinanceCosts-newDebt;
 return {classification:"ASSUMPTION_ONLY_FINANCIAL_SCENARIO",
  interpretation:"No uploaded NOI, payoff, ownership, legal rent status or maturity is independently verified by this calculation.",

  limits:debtLimits,annual_debt_service_constant:constant,
  limiting_constraints:limiting,acquisition_new_debt_capacity:newDebt,
  first_year_debt_service:newDebt*constant,
  first_year_dscr:noi/(newDebt*constant),first_year_debt_yield:noi/newDebt,
  implied_cap_rate_on_purchase:noi/price,
  initial_equity_required:initialEquity,loan_balance_at_exit:balance,
  equity_cash_flows:cashflows,annual_projection:details,
  illustrative_irr:irr,illustrative_equity_multiple:netProceeds/initialEquity,
  hypothetical_refinance_gap:gap,
  hypothetical_refinance_equity_shortfall:gap==null?null:Math.max(0,gap),
  payoff_required_for_gap:true, verified_actual_noi:false,verified_current_payoff:false,
  verified_distress:false,verified_contractual_maturity:false,verified_regulatory_eligibility:false};
}
async function migrate(){
 if(!db)throw Error("Database unavailable");
 await db`CREATE TABLE IF NOT EXISTS radar_c_underwriting_scenarios(
 id BIGSERIAL PRIMARY KEY,bbl TEXT NOT NULL REFERENCES radar_asset_screen(bbl),
 inputs JSONB NOT NULL,output JSONB NOT NULL,
 source_citations JSONB NOT NULL DEFAULT '[]'::jsonb,
 researcher TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'ANALYST_ASSUMPTIONS_UNVERIFIED',
 independent_review_complete BOOLEAN NOT NULL DEFAULT FALSE,
 investment_recommendation_verified BOOLEAN NOT NULL DEFAULT FALSE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())`;
 await db`CREATE INDEX IF NOT EXISTS radar_c_underwriting_scenarios_bbl_idx
 ON radar_c_underwriting_scenarios(bbl,created_at DESC)`;
 await db`CREATE TABLE IF NOT EXISTS radar_c_scenario_audit(
 id BIGSERIAL PRIMARY KEY,scenario_id BIGINT NOT NULL REFERENCES radar_c_underwriting_scenarios(id),
 event_kind TEXT NOT NULL,actor TEXT NOT NULL,comment TEXT,created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())`;
}
let migrated=false;
async function ensure(){if(!migrated){await migrate();migrated=true}}
Bun.serve({port:Number(Bun.env.PORT||3000),async fetch(req:Request){
 const u=new URL(req.url);
 if(u.pathname==="/health")return response({ok:!!db,service:"radar-c-scenario-underwriting"},db?200:503);
 if(!authenticated(req))return response({error:"Unauthorized"},401);
 try{
  if(!db)return response({error:"Storage unavailable"},503);
  await ensure();
  if(u.pathname==="/api/milestone-c/model"){
   if(req.method!=="POST")return response({error:"POST required"},405);
   let input:any;try{input=await req.json()}catch{return response({error:"Valid JSON required"},400)}
   try{
    const output=calculate(input);
    delete (output as any).value_by_inplace_cap_rate;
    return response({model_version:"ACQUISITION_V1",inputs:input,results:output});
   }catch(err:any){return response({error:String(err.message)},400)}
  }
  if(u.pathname==="/api/milestone-c/scenarios"){
   if(req.method==="GET"){
    const bbl=u.searchParams.get("bbl")||"";
    if(!/^[0-9]{10}$/.test(bbl))return response({error:"Valid BBL required"},400);
    const rows=await db`SELECT id,bbl,inputs,output,source_citations,researcher,status,
     independent_review_complete,investment_recommendation_verified,created_at
     FROM radar_c_underwriting_scenarios WHERE bbl=${bbl} ORDER BY id DESC LIMIT 50`;
    return response({bbl,cases:rows,legal_or_financial_facts_verified_by_system:false});
   }
   if(req.method!=="POST")return response({error:"GET or POST required"},405);
   let v:any;try{v=await req.json()}catch{return response({error:"Valid JSON required"},400)}
   const bbl=String(v.bbl||""),researcher=String(v.researcher||"").trim();
   if(!/^[0-9]{10}$/.test(bbl)||researcher.length<2||researcher.length>100)
    return response({error:"Valid research BBL and analyst required"},400);
   if(!Array.isArray(v.source_citations)||v.source_citations.length<1||v.source_citations.length>30||
      v.source_citations.some((r:any)=>typeof r?.url!=="string"||!/^https:\/\//.test(r.url)||
       typeof r?.kind!=="string"||r.kind.length>80))
    return response({error:"At least one explicit source citation or analyst assumption provenance required"},400);
   let model:any;try{model=calculate(v.inputs)}catch(err:any){return response({error:String(err.message)},400)}
   delete (model as any).value_by_inplace_cap_rate;
   const present=await db`SELECT 1 FROM radar_asset_screen WHERE bbl=${bbl}`;
   if(!present.length)return response({error:"BBL not in screen universe"},404);
   const a=await db`INSERT INTO radar_c_underwriting_scenarios(
     bbl,inputs,output,source_citations,researcher)
     VALUES(${bbl},${JSON.stringify(v.inputs)}::jsonb,${JSON.stringify(model)}::jsonb,
      ${JSON.stringify(v.source_citations)}::jsonb,${researcher})
     RETURNING id,bbl,status,created_at`;
   await db`INSERT INTO radar_c_scenario_audit(scenario_id,event_kind,actor,comment)
     VALUES(${a[0].id},'SCENARIO_CREATED_UNVERIFIED',${researcher},
       'Calculations are assumptions; no source verification or investment recommendation')`;
   return response({scenario:a[0],verified:false,model_version:"ACQUISITION_V1"},201);
  }
  if(u.pathname==="/api/milestone-c/status"){
   const s=await db`SELECT
    (SELECT COUNT(*)::int FROM radar_c_underwriting_scenarios) AS analyst_scenarios,
    (SELECT COUNT(*)::int FROM radar_c_underwriting_scenarios
      WHERE independent_review_complete) AS independently_reviewed,
    (SELECT COUNT(*)::int FROM radar_c_underwriting_scenarios
      WHERE investment_recommendation_verified) AS verified_investments,
    (SELECT COUNT(*)::int FROM radar_r22_dossiers) AS first_financing_dossiers`;
   return response({capability:"EXPLICIT_ASSUMPTIONS_ACQUISITION_AND_REFINANCE_MODEL",
    counts:s[0],actual_underwriting_complete:false,
    note:"The model does not auto-import ACRIS face amounts, infer missing payoff amounts, or represent rent status as verified."});
  }
  return response({error:"Not found"},404);
 }catch(e:any){console.error(JSON.stringify({event:"milestone_c_request_error",path:u.pathname,error:String(e.message)}));return response({error:"Internal error"},500)}
}});
