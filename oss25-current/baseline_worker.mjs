import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';
const [product, request] = process.argv.slice(2);
const input = JSON.parse(await fs.readFile(request,'utf8'));
const load = relative => import(pathToFileURL(path.join(product,relative)));
const { repositoryEnvironment, adoptEnvironment } = await load('scripts/lib/repository-environment.mjs');
const { resolveValidationPlan } = await load('packages/part-a/src/replay/repositoryValidationPlan.ts');
const { runRepositoryValidationCommand, readRubyValidationRuntimeVersion } = await load('packages/part-a/src/replay/dependencyVersionBumpExecutor.ts');
const record = { status:'running', started_at:new Date().toISOString(), source_sha:input.sourceSha, commands:[] };
const save = () => fs.writeFile(input.result, JSON.stringify(record,null,2)+'\n');
try {
  const actual = execFileSync('git',['-C',input.work,'rev-parse','HEAD'],{encoding:'utf8'}).trim();
  if (actual !== input.sourceSha) throw new Error('Independent baseline source revision mismatch');
  const prepared = await repositoryEnvironment({rootDir:input.work,manifestPath:input.manifest,ecosystem:input.ecosystem,packageName:input.packageName,deadlineAt:input.deadlineAt});
  record.environment = prepared.log;adoptEnvironment(prepared.env);
  const ruby = input.ecosystem==='gem' ? await readRubyValidationRuntimeVersion(input.work,undefined,input.deadlineAt) : undefined;
  const plan = await resolveValidationPlan(input.work,input.directory,input.ecosystem,input.packageName,[input.manifest],ruby===undefined?undefined:{ruby});
  record.plan = plan;
  const checks = plan.validationCommands?.length ? plan.validationCommands : plan.testCommands.map(command=>({command,workingDirectory:input.directory||'.',origin:plan.source}));
  const commands = [
    ...(plan.prepareCommands??[]).map(c=>({...c,kind:'preparation'})),
    ...(plan.installCommand ? [{command:plan.installCommand,workingDirectory:plan.installWorkingDirectory??(input.directory||'.'),kind:'installation'}] : []),
    ...checks.map(c=>({...c,kind:'validation'})),
  ];
  await save();
  for (const c of commands) {
    if (Date.now()>=input.deadlineAt) {record.commands.push({kind:c.kind,command:c.command,status:'not_attempted_baseline_deadline'});continue;}
    try {
      const result = await runRepositoryValidationCommand(input.work,c.workingDirectory??(input.directory||'.'),c.command,Math.max(1,input.deadlineAt-Date.now()),input.deadlineAt);
      record.commands.push({kind:c.kind,origin:c.origin,...result});
    } catch(error) {record.commands.push({kind:c.kind,command:c.command,status:'execution_error',error:error instanceof Error?error.message:String(error)});}
    await save();
  }
  record.status = record.commands.length>0 && record.commands.every(c=>c.exitCode===0) ? 'passed' : 'original_source_checks_failed';
  record.runtime_validation_commands = checks.length;
  record.validation_coverage = checks.length ? 'Original-source checks retained with complete bounded output' : 'Install only; cannot prove runtime validation';
  record.source_head_after = execFileSync('git',['-C',input.work,'rev-parse','HEAD'],{encoding:'utf8'}).trim();
} catch(error) {record.status='baseline_worker_error';record.error=error instanceof Error?error.message:String(error);}
record.finished_at=new Date().toISOString();await save();
process.exitCode = record.status==='passed'?0:2;
