import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
const [product, source, out] = process.argv.slice(2);
const {runRepositoryValidationCommand} = await import(pathToFileURL(path.join(product,'packages/part-a/src/replay/dependencyVersionBumpExecutor.ts')));
const pin=JSON.parse(process.env.PUBLISHED_PIN_JSON);
if(process.env.TARGET_SOURCE!=='elixir-plug/plug')throw new Error('No independently qualified scoped producer');
const git=(...args)=>execFileSync('git',['-C',source,...args],{encoding:'utf8',maxBuffer:32*1024*1024});
if(git('rev-parse',pin.head_sha+'^').trim()!==pin.base_sha)throw new Error('Published source parent mismatch');
const patch=git('diff','--binary',pin.base_sha,pin.head_sha);
if(crypto.createHash('sha256').update(patch).digest('hex')!==pin.published_patch_sha256)throw new Error('Published patch binding mismatch');
await fs.writeFile(path.join(out,'independent-published.patch'),patch);
const record={scope:'Independent additional validation of documentation-only dependency; supplements and does not alter product receipts',...pin,started_at:new Date().toISOString(),phases:[],status:'running'};
const save=()=>fs.writeFile(path.join(out,'published-control.json'),JSON.stringify(record,null,2)+'\n');
process.env.MIX_ENV='docs';
for(const [name,sha] of [['unchanged_docs_baseline',pin.base_sha],['exact_published_docs_update',pin.head_sha]]){
 git('reset','--hard');git('clean','-ffdqx');git('checkout','--detach',sha);
 const phase={name,head_sha:git('rev-parse','HEAD').trim(),commands:[]};record.phases.push(phase);await save();
 for(const command of [{executable:'mix',args:['deps.get']},{executable:'mix',args:['docs']}]){
  const deadline=Date.now()+20*60_000;
  const r=await runRepositoryValidationCommand(source,'.',command,20*60_000,deadline);phase.commands.push(r);await save();if(r.exitCode!==0)break;
 }
 phase.status=phase.commands.length===2&&phase.commands.every(c=>c.exitCode===0)?'passed':'failed';await save();
}
record.status=record.phases.every(p=>p.status==='passed')?'passed':record.phases[0].status!=='passed'?'baseline_context_failed':'published_update_failed';
record.finished_at=new Date().toISOString();git('reset','--hard');git('clean','-ffdqx');git('checkout','--detach',pin.base_sha);await save();process.exitCode=record.status==='passed'?0:2;
