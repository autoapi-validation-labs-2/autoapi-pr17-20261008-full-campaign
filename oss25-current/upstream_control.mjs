import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {execFileSync} from 'node:child_process';
const [product,source,out]=process.argv.slice(2);
const load=p=>import(pathToFileURL(path.join(product,p)));
const {repositoryEnvironment,adoptEnvironment}=await load('scripts/lib/repository-environment.mjs');
const {runRepositoryValidationCommand}=await load('packages/part-a/src/replay/dependencyVersionBumpExecutor.ts');
const deadlineAt=Date.now()+60*60_000;
const record={status:'running',scope:'FastAPI actual frozen Linux CI test producer, instead of the artifact-only coverage consumer selected by the product',source_sha:execFileSync('git',['-C',source,'rev-parse','HEAD'],{encoding:'utf8'}).trim(),commands:[],started_at:new Date().toISOString()};
const save=()=>fs.writeFile(path.join(out,'upstream-control.json'),JSON.stringify(record,null,2)+'\n');
try{
 const prepared=await repositoryEnvironment({rootDir:source,manifestPath:'pyproject.toml',ecosystem:'pypi',packageName:'fastapi',deadlineAt});record.environment=prepared.log;adoptEnvironment(prepared.env);
 process.env.COVERAGE_FILE=path.join(source,'coverage','.coverage.linux-control');
 const commands=[{executable:'uv',args:['sync','--no-dev','--group','tests','--extra','all']},{executable:'mkdir',args:['-p','coverage']},{executable:'uv',args:['run','--no-sync','bash','scripts/test-cov.sh']}];
 for(const command of commands){const result=await runRepositoryValidationCommand(source,'.',command,Math.max(1,deadlineAt-Date.now()),deadlineAt);record.commands.push(result);await save();if(result.exitCode!==0)break;}
 record.status=record.commands.length===commands.length&&record.commands.every(c=>c.exitCode===0)?'passed':'original_ci_producer_failed';
}catch(error){record.status='control_error';record.error=error instanceof Error?error.message:String(error);}
record.finished_at=new Date().toISOString();await save();process.exitCode=record.status==='passed'?0:2;
