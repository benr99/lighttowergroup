
import {SQL} from "bun";
const db=Bun.env.DATABASE_URL?new SQL(Bun.env.DATABASE_URL):null;
const response=(x:any,status=200)=>new Response(JSON.stringify(x),{status,headers:{"Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store","X-Content-Type-Options":"nosniff","Referrer-Policy":"no-referrer"}});
const auth=(r:Request)=>!!Bun.env.RADAR_API_KEY&&r.headers.get("authorization")==="Bearer "+Bun.env.RADAR_API_KEY;
Bun.serve({port:Number(Bun.env.PORT||3000),async fetch(req:Request){
 const u=new URL(req.url);
 if(u.pathname==="/health")return response({ok:!!db,component:"radar-e-security-release-gate"},db?200:503);
 if(!auth(req))return response({error:"Unauthorized"},401);
 if(!db)return response({error:"Database unavailable"},503);
 try{
  if(u.pathname==="/api/milestone-e/status"){
   const rows=await db`SELECT id,scope,technical_gates,investment_evidence_gates,
    operational_gates,all_production_gates_passed,summary,run_at
    FROM radar_e_release_gates ORDER BY id DESC LIMIT 1`;
   if(!rows.length)return response({error:"No verified release assessment recorded"},503);
   const x=rows[0];
   const parsed=(value:any)=>typeof value==="string"?JSON.parse(value):value;
   const tech=parsed(x.technical_gates),invest=parsed(x.investment_evidence_gates),ops=parsed(x.operational_gates),meta=parsed(x.summary);
   const summary=(obj:any)=>({passed:Object.values(obj).filter(Boolean).length,
      total:Object.keys(obj).length,
      failures:Object.entries(obj).filter(([_,v])=>v!==true).map(([name])=>name)});
   return response({assessment_id:x.id,checked_at:x.run_at,production_ready:x.all_production_gates_passed,
    technical:summary(tech),investment_evidence:summary(invest),
    security_and_operations:summary(ops),
    gates:{technical:tech,investment_evidence:invest,
     security_and_operations:ops},
    counts:meta?.counted_assets,
    financing:meta?.financing,underwriting:meta?.underwriting,
    origination:meta?.origination,service_health:meta?.services,
    status:"DEVELOPMENT_WITH_UNVERIFIED_PRODUCTION_REQUIREMENTS",
    warning:"All unresolved gates must pass independently. Software deployment does not certify property legal status, loan terms, backup recovery, security or commercial data rights."});
  }
  if(u.pathname==="/api/milestone-e/history"){
   const n=Number(u.searchParams.get("limit")??"20");
   if(!Number.isSafeInteger(n)||n<1||n>100)return response({error:"limit must be 1-100"},400);
   const rows=await db`SELECT id,run_at,scope,all_production_gates_passed,
    technical_gates,investment_evidence_gates,operational_gates
    FROM radar_e_release_gates ORDER BY id DESC LIMIT ${n}`;
   return response({runs:rows});
  }
  if(u.pathname==="/api/milestone-e/security-policy"){
   return response({environment:"development",authentication:"SHARED_PRIVATE_API_KEY",
     roles_and_individual_sessions:"NOT_IMPLEMENTED",
     protection_confirmed:["Existing API Bearer auth gates","TLS-served Railway domains","Private key stored in service variables","Reproducible acceptance checks"],
     not_verified:[
      "Per-user sessions, MFA or role-based authorization",
      "Production-staging separation and Git-controlled automated rollbacks",
      "Confirmed encrypted database backups and successful restore",
      "Independent penetration test and OWASP coverage",
      "Source-license rights for commercial redistribution",
      "Incident paging and recovery playbook exercised"],
     go_live_allowed:false,
     note:"This endpoint documents gaps; it does not itself implement those controls."});
  }
  return response({error:"Not found"},404);
 }catch(err:any){console.error(JSON.stringify({event:"milestone_e_api_error",error:String(err.message)}));
  return response({error:"Internal status error"},500)}
}});
