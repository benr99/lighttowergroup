
const key=Bun.env.RADAR_API_KEY;if(!key||key.includes("${{"))throw Error("RADAR_API_KEY missing");
const base="https://radar-research-ui-development.up.railway.app";
const checks:any[]=[];let bad=0;
const test=(name:string,pass:boolean,extra:any=null)=>{checks.push({name,pass,extra});if(!pass)bad++};
async function call(path:string,opts:{method?:string;body?:any;authorized?:boolean}={}){
 const method=opts.method||"GET",headers:any={Accept:"application/json"};
 if(opts.authorized!==false)headers.Authorization="Bearer "+key;
 if(opts.body!=null)headers["Content-Type"]="application/json";
 const response=await fetch(base+path,{method,headers,
 body:opts.body==null?undefined:JSON.stringify(opts.body),signal:AbortSignal.timeout(30000)});
 const type=response.headers.get("content-type")||"";
 let data:any;try{data=type.includes("json")?await response.json():await response.text()}catch{}
 return {code:response.status,data};
}
const h=await call("/universe");
let syntax=false,syntaxError="";
if(typeof h.data==="string"){
 const found=h.data.match(/<script>([\s\S]*?)<\/script>/i);
 if(found){try{new Function(found[1]);syntax=true}catch(e:any){syntaxError=String(e.message)}}
}
test("research UI GET healthy",h.code===200);
test("research UI JavaScript parses",syntax,{syntaxError});
test("all C D E panels rendered",typeof h.data==="string"&&
 ["cModelRun","dLeadCreate","eReadiness","bLoad","aLoad"].every(t=>h.data.includes('id="'+t+'"')));
for(const stage of ["c","d","e"]){
 const path=stage==="c"?"/api/milestone-c/status":stage==="d"?"/api/milestone-d/overview":"/api/milestone-e/status";
 const authed=await call(path);
 test(stage+" authenticated proxy GET 200",authed.code===200,{code:authed.code,error:authed.data?.error});
 const denied=await call(path,{authorized:false});
 test(stage+" unauthorized proxy 401",denied.code===401,{code:denied.code});
}
const status=await call("/api/milestone-e/status");
const e=status.data||{};

test("E release readiness correctly not passed",e.production_ready===false);
test("E lists unmet production operations",e.security_and_operations?.total>=9&&e.security_and_operations?.passed===0);
test("E shows collection incomplete",e.gates?.technical?.source_collection_coverage===false);
test("E preserves financial evidence safeguards",e.gates?.investment_evidence?.b_ten_actual_financing_facilities===false);
const policy=await call("/api/milestone-e/security-policy");
test("E explicitly flags shared-key auth",policy.code===200&&policy.data?.roles_and_individual_sessions==="NOT_IMPLEMENTED"&&
 policy.data?.go_live_allowed===false);
const invalidHistory=await call("/api/milestone-e/history?limit=1000");
test("E history is bounded",invalidHistory.code===400);
const history=await call("/api/milestone-e/history?limit=5");
test("E persists status snapshots",history.code===200&&history.data?.runs?.length>=1);
const overview=await call("/api/milestone-d/overview");
test("D no false qualified acquisitions",overview.data?.counts?.qualified_acquisitions===0);
const modelInput={annual_noi:1000000,purchase_price:20000000,max_ltv:0.65,min_dscr:1.25,
 min_debt_yield:0.09,annual_interest_rate:0.065,amortization_years:30,
 exit_cap_rate:0.055,annual_noi_growth:0.02,initial_capex:300000,
 annual_capex:50000,exit_sales_cost_rate:0.03,acquisition_cost_rate:0.02,
 financing_cost_rate:0.01,hold_years:5,assumed_existing_payoff:null,refinance_costs:200000,interest_only:false};
const m=await call("/api/milestone-c/model",{method:"POST",body:modelInput});
test("C model works through live research desk",m.code===200&&
 m.data?.results?.equity_cash_flows?.length===6,{status:m.code,error:m.data?.error});
test("C calculations don't invent debt or maturity",m.data?.results?.verified_current_payoff===false&&
 m.data?.results?.verified_contractual_maturity===false&&m.data?.results?.verified_distress===false);
const draft=await call("/api/milestone-d/outreach-draft?bbl=1000050010");
test("D draft review-only through dashboard",draft.code===200&&draft.data?.automatically_sent===false);
console.log(JSON.stringify({event:"milestone_cde_unified_workstation_acceptance",
 passed:checks.length-bad,failed:bad,
 e_technical:e.technical,e_investment_evidence:e.investment_evidence,
 e_operations:e.security_and_operations,
 tests:checks}));
if(bad)process.exitCode=1;
