import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {execFileSync,spawn} from 'node:child_process';
import {pathToFileURL} from 'node:url';
const [product, source, out] = process.argv.slice(2);
const {runRepositoryValidationCommand} = await import(pathToFileURL(path.join(product,'packages/part-a/src/replay/dependencyVersionBumpExecutor.ts')));
const input=JSON.parse(process.env.PUBLISHED_PIN_JSON),pins=Array.isArray(input)?input:[input];
const target=process.env.TARGET_SOURCE;
if(!['elixir-plug/plug','pallets/flask','fastapi/fastapi','gofiber/fiber','slimphp/Slim','psf/requests','guzzle/guzzle','google/gson'].includes(target))throw new Error('No independently qualified scoped producer');
const git=(...args)=>execFileSync('git',['-C',source,...args],{encoding:'utf8',maxBuffer:32*1024*1024});
const record={scope:'Independent additional validation of exact published changes; supplements and does not alter product receipts',source:target,started_at:new Date().toISOString(),updates:[],status:'running'};
const save=()=>fs.writeFile(path.join(out,'published-control.json'),JSON.stringify(record,null,2)+'\n');
const clean=sha=>{git('reset','--hard');git('clean','-ffdqx');git('checkout','--detach',sha);};
async function producer(dir){
 await fs.mkdir(dir,{recursive:true});
 const child=spawn(process.execPath,['--import',path.join(product,'packages/part-a/node_modules/tsx/dist/loader.mjs'),path.join(path.dirname(new URL(import.meta.url).pathname),'upstream_control.mjs'),product,source,dir],{cwd:product,env:process.env,stdio:['ignore','inherit','inherit']});
 const code=await new Promise((resolve,reject)=>{child.once('error',reject);child.once('exit',resolve);});
 const phase=JSON.parse(await fs.readFile(path.join(dir,'upstream-control.json'),'utf8'));
 return {code,phase};
}
if(target==='slimphp/Slim'){
 clean(pins[0].base_sha);const {code,phase}=await producer(path.join(out,'php84-original-baseline'));record.baseline=phase;await save();
 if(code!==0||phase.status!=='passed'){record.status='new_php_baseline_failed';await save();process.exit(2);}
}
for(const pin of pins){
 if(git('rev-parse',pin.head_sha+'^').trim()!==pin.base_sha)throw new Error('Published source parent mismatch');
 const patch=git('diff','--binary',pin.base_sha,pin.head_sha);
 if(crypto.createHash('sha256').update(patch).digest('hex')!==pin.published_patch_sha256)throw new Error('Published patch binding mismatch');
 const update={...pin,phases:[]};record.updates.push(update);
 const dir=path.join(out,pin.head_sha);await fs.mkdir(dir,{recursive:true});await fs.writeFile(path.join(dir,'independent-published.patch'),patch);await save();
 if(target==='elixir-plug/plug'){
  process.env.MIX_ENV='docs';
  for(const [name,sha] of [['unchanged_docs_baseline',pin.base_sha],['exact_published_docs_update',pin.head_sha]]){
   clean(sha);const phase={name,head_sha:git('rev-parse','HEAD').trim(),commands:[]};update.phases.push(phase);await save();
   for(const command of [{executable:'mix',args:['deps.get']},{executable:'mix',args:['docs']}]){
    const deadline=Date.now()+20*60_000;
    const r=await runRepositoryValidationCommand(source,'.',command,20*60_000,deadline);phase.commands.push(r);await save();if(r.exitCode!==0)break;
   }
   phase.status=phase.commands.length===2&&phase.commands.every(c=>c.exitCode===0)?'passed':'failed';await save();
  }
  update.status=update.phases.every(p=>p.status==='passed')?'passed':update.phases[0].status!=='passed'?'baseline_context_failed':'published_update_failed';
 }else{
  clean(pin.head_sha);
  const {code,phase}=await producer(dir);update.phases.push(phase);update.status=code===0&&phase.status==='passed'?'passed':'published_producer_failed';
  if(target==='slimphp/Slim'){try{update.resolved_target=JSON.parse(execFileSync('composer',['show','phpunit/phpunit','--format=json'],{cwd:source,env:process.env,encoding:'utf8'}));}catch(error){update.resolved_target_error=String(error);}}
 }
 await save();clean(pin.base_sha);
}
record.status=record.updates.every(u=>u.status==='passed')?'passed':'one_or_more_published_checks_failed';
record.finished_at=new Date().toISOString();await save();process.exitCode=record.status==='passed'?0:2;
