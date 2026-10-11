
const token=Bun.env.RADAR_API_KEY;
if(!token||token.includes("${{"))throw Error("Need Railway RADAR_API_KEY reference");
const base="https://radar-milestone-b-research-api-development.up.railway.app";
const checkResults:any[]=[];let failed=0;
function test(name:string,good:boolean,detail:any=null){checkResults.push({name,pass:!!good,detail});if(!good)failed++}
async function read(path:string,authorized=true){
 const r=await fetch(base+path,{headers:authorized?{"Authorization":"Bearer "+token,"Accept":"application/json"}:{"Accept":"application/json"},signal:AbortSignal.timeout(30000)});
 let data:any=null;try{data=await r.json()}catch{}
 return {code:r.status,data};
}
const unauthorized=await read("/api/milestone-b/coverage",false);
test("unauthorized coverage denied",unauthorized.code===401);
const status=await read("/api/milestone-b/coverage");
const d=status.data||{},c=d.collection||{},ds=d.research_dossiers||{};
test("coverage endpoint healthy",status.code===200);
test("full target count unchanged",c.full_universe===4436);
test("collection accounting consistent",c.remaining_unattempted===4436-c.attempts&&
 c.attempts===c.completed_lots+c.incomplete_lots+c.failed_lots);
test("percent reflects actual collection",Math.abs(c.completeness_percent-100*c.completed_lots/4436)<0.02);
test("boros reconcile",d.by_borough?.reduce((n:number,r:any)=>n+r.candidate_lots,0)===4436);
test("ten dossiers retained",ds.sample_dossiers===10);
test("document components coverage",ds.dossier_financing_events===452&&
 ds.documents_assigned_component===452&&ds.provisional_document_components>0);
test("unverified loan families never certified",ds.verified_current_facilities===0&&
 d.acceptance_gates?.all_ten_primary_instruments_independently_audited===false);
test("explicit collection gate truthfulness",
 d.acceptance_gates?.full_universe_collection_cleared===(c.completed_lots===4436&&c.attempts===4436));
const queue=await read("/api/milestone-b/research-queue?limit=10");
test("research queue available",queue.code===200&&queue.data?.research_queue?.length===10);
const bbl=queue.data?.research_queue?.[0]?.bbl;
const one=await read("/api/milestone-b/dossier?bbl="+encodeURIComponent(bbl||""));
test("dossier available",one.code===200&&one.data?.dossier?.bbl===bbl);
test("dossier source evidence",one.data?.recording_events?.length>0&&
 one.data?.reference_connected_components?.length>0&&
 one.data?.recording_events?.every((x:any)=>x.source_master_url));
test("never misrepresent mortgage as balance",one.data?.current_principal_verified===false&&
 one.data?.current_lender_verified===false&&one.data?.legal_loan_family_verified===false);
test("dossier event coverage",
 one.data?.recording_events?.reduce((n:number,x:any)=>n+1,0)>0);
const invalid=await read("/api/milestone-b/dossier?bbl=bad");
test("invalid BBL rejected",invalid.code===400);
const invalidLimit=await read("/api/milestone-b/research-queue?limit=1000");
test("unbounded page rejected",invalidLimit.code===400);
const missing=await read("/api/milestone-b/dossier?bbl=1999999999");
test("absent dossier rejected",missing.code===404);

const ui="https://radar-research-ui-development.up.railway.app";
const uir=await fetch(ui+"/universe",{signal:AbortSignal.timeout(30000)});
const html=await uir.text();
const script=html.match(/<script>([\s\S]*?)<\/script>/i);
let jsValid=false,jsError="";
if(script){try{new Function(script[1]);jsValid=true;}catch(err:any){jsError=String(err.message)}}
test("milestone_b_ui_browser_get",uir.status===200&&jsValid&&html.includes('id="bLoad"')&&html.includes('id="bRows"'),
 {status:uir.status,jsValid,jsError});
const proxy=await fetch(ui+"/api/milestone-b/coverage",{headers:{"Authorization":"Bearer "+token},
 signal:AbortSignal.timeout(30000)});
const proxied=await proxy.json().catch(()=>({}));
test("milestone_b_proxy_authenticated",proxy.status===200&&proxied?.collection?.full_universe===4436,
 {status:proxy.status,collection:proxied?.collection?.attempts});
const proxyDenied=await fetch(ui+"/api/milestone-b/coverage",{signal:AbortSignal.timeout(30000)});
test("milestone_b_proxy_denies_unauthorized",proxyDenied.status===401,{status:proxyDenied.status});
console.log(JSON.stringify({event:"milestone_b_api_and_quality_acceptance",passed:checkResults.length-failed,failed,
 collection:c,documents:d.documents,ten_dossier_coverage:ds,results:checkResults}));
if(failed)process.exitCode=1;
