
const api="https://radar-milestone-a-research-api-development.up.railway.app";
const key=Bun.env.RADAR_API_KEY;
if(!key||key.includes("${{"))throw Error("RADAR_API_KEY must be injected by Railway");
const results:any[]=[];let failures=0;
function check(name:string,condition:boolean,details:any=null){
 results.push({name,pass:!!condition,details});if(!condition)failures++;
}
async function get(path:string,authorized=true){
 const response=await fetch(api+path,{headers:{"Accept":"application/json",...(authorized?{"Authorization":"Bearer "+key}:{})},signal:AbortSignal.timeout(45000)});
 const type=response.headers.get("content-type")||"";
 let data:any;
 if(type.includes("json"))data=await response.json();
 else data=await response.text();
 return {status:response.status,data,headers:response.headers};
}
const noAuth=await get("/api/milestone-a/summary",false);
check("unauthenticated summary rejected",noAuth.status===401);
const summary=await get("/api/milestone-a/summary");
const d=summary.data?.counts||{};
check("summary reads correctly",summary.status===200);
check("full PLUTO population",d.raw_lots===318610);
check("all qualifying lots screen",d.qualifying_tax_lots===4436&&d.research_asset_ids===4436&&d.regulation_screened_lots===4436);
check("all source checks successful",d.hpd_source_checks_complete===4436&&d.dof_source_checks_complete===4436);
check("2024 HCR match accounting",d.hcr_2024_listed===2540&&d.not_on_2024_hcr_unverified===1896);
check("historical HPD sales signals",d.ll7_sale_lots===82&&d.speculation_watch_sale_lots===31);
check("no unsupported regulated-status certification",d.verified_free_market===0&&summary.data?.free_market_certification_complete===false);
check("source evidence and review exceptions",d.evidence_records>=55683&&d.unresolved_asset_identifications===4436);
check("borough totals",summary.data?.by_borough?.length===2&&summary.data.by_borough.reduce((n:number,x:any)=>n+x.candidate_lots,0)===4436);
check("active identity and regulation taxonomy",summary.data?.identity_categories?.length>=4&&summary.data?.regulation_categories?.length>=5);
const assets=await get("/api/milestone-a/assets?limit=50&max_units=600");
check("bounded asset search",assets.status===200&&assets.data?.records?.length===50&&assets.data.records.every((x:any)=>x.residential_units_per_lot<=600));
const first=assets.data?.records?.[0]?.bbl;
if(!first)throw Error("No BBL from safe bounded sample");
const one=await get("/api/milestone-a/asset?bbl="+first);
check("evidence-backed property details",one.status===200&&one.data?.asset?.bbl===first&&one.data?.evidence?.length>=1);
check("property explicitly unverified",one.data?.verified_free_market===false&&one.data?.verified_unit_level_regulation===false&&one.data?.current_economic_owner_verified===false);
check("property review tasks",one.data?.review_items?.some((x:any)=>x.review_kind==="LEGAL_RENT_STATUS")&&one.data?.review_items?.some((x:any)=>x.review_kind==="ECONOMIC_ASSET_IDENTITY"));
const ex=await get("/api/milestone-a/exceptions?limit=20&offset=0");
check("exceptions have full coverage",ex.status===200&&ex.data?.count===4436);
const bad=await get("/api/milestone-a/asset?bbl=invalid");
check("invalid BBL rejected",bad.status===400);
const badBorough=await get("/api/milestone-a/assets?borough=BX");
check("invalid borough rejected",badBorough.status===400);
const unauthorizedExport=await get("/api/milestone-a/export.csv",false);
check("private CSV access enforced",unauthorizedExport.status===401);
const csv=await get("/api/milestone-a/export.csv");
const lines=String(csv.data||"").trimEnd().split("\n");
check("full candidate CSV export",csv.status===200&&lines.length===4437,{count:lines.length});
check("CSV reports historical regulation, not assumed free-market",lines[0].includes("historical_hcr_2024")&&lines[0].includes("legal_free_market_certified")&&lines[0].includes("identity_triage"));

const ui="https://radar-research-ui-development.up.railway.app";
const browser=await fetch(ui+"/universe",{method:"GET",signal:AbortSignal.timeout(30000)});
const page=await browser.text();
const match=page.match(/<script>([\s\S]*?)<\/script>/i);
let parsed=false,syntaxError="";
if(match){try{new Function(match[1]);parsed=true}catch(err:any){syntaxError=String(err.message)}}
check("milestone_a_ui_browser_script",browser.status===200&&parsed&&
 page.includes('id="aLoad"')&&page.includes('id="aExport"')&&page.includes('id="aEvidence"'),
 {status:browser.status,parsed,syntaxError});
const viaUi=await fetch(ui+"/api/milestone-a/summary",{headers:{"Authorization":"Bearer "+key},
 signal:AbortSignal.timeout(45000)});
const proxyData=await viaUi.json().catch(()=>({}));
check("milestone_a_ui_authenticated_proxy",viaUi.status===200&&proxyData?.counts?.research_asset_ids===4436,
 {status:viaUi.status,count:proxyData?.counts?.research_asset_ids});
const noProxy=await fetch(ui+"/api/milestone-a/summary",{signal:AbortSignal.timeout(30000)});
check("milestone_a_ui_proxy_rejects_unauthorized",noProxy.status===401,{status:noProxy.status});
const proxyCsv=await fetch(ui+"/api/milestone-a/export.csv",{headers:{"Authorization":"Bearer "+key},
 signal:AbortSignal.timeout(45000)});
const csvText=await proxyCsv.text();
check("milestone_a_ui_csv_export",proxyCsv.status===200&&csvText.trimEnd().split("\n").length===4437,
 {status:proxyCsv.status,lines:csvText.trimEnd().split("\n").length});
console.log(JSON.stringify({event:"milestone_a_authenticated_acceptance_suite",passed:results.length-failures,
 failed:failures,candidates:d.qualifying_tax_lots,exported_lines:lines.length,
 hpd:d.hpd_source_checks_complete,dof:d.dof_source_checks_complete,
 historic_hcr:d.hcr_2024_listed,unlisted_unverified:d.not_on_2024_hcr_unverified,
 sample_bbl:first,results}));
if(failures)process.exitCode=1;
