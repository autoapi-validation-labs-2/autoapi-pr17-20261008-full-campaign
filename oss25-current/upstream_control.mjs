import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {execFileSync} from 'node:child_process';
const [product,source,out]=process.argv.slice(2);
const load=p=>import(pathToFileURL(path.join(product,p)));
const {repositoryEnvironment,adoptEnvironment}=await load('scripts/lib/repository-environment.mjs');
const {runRepositoryValidationCommand}=await load('packages/part-a/src/replay/dependencyVersionBumpExecutor.ts');
const deadlineAt=Date.now()+60*60_000;
const target=process.env.TARGET_SOURCE;
const cmd=(executable,...args)=>({executable,args});
const configs={
 'fastapi/fastapi':{manifest:'pyproject.toml',ecosystem:'pypi',name:'fastapi',commands:[cmd('uv','sync','--no-dev','--group','tests','--extra','all'),cmd('mkdir','-p','coverage'),cmd('uv','run','--no-sync','bash','scripts/test-cov.sh')]},
 'vuejs/core':{manifest:'package.json',ecosystem:'npm',name:'vue',commands:[cmd('corepack','pnpm','install','--no-frozen-lockfile','--config.strict-dep-builds=false'),cmd('pnpm','run','test-unit')]},
 'trpc/trpc':{manifest:'package.json',ecosystem:'npm',name:'@trpc/server',commands:[cmd('corepack','pnpm','install','--no-frozen-lockfile','--config.strict-dep-builds=false'),cmd('pnpm','test','--coverage')]},
 'gofiber/fiber':{manifest:'go.mod',ecosystem:'go',name:'github.com/gofiber/fiber/v3',commands:[cmd('go','mod','download'),cmd('go','test','./...','-race','-count=5','-shuffle=on')]},
 'puma/puma':{manifest:'Gemfile',ecosystem:'gem',name:'puma',commands:[cmd('bundle','install'),cmd('bundle','exec','rake','rubocop')]},
 'fastify/fastify':{manifest:'package.json',ecosystem:'npm',name:'fastify',commands:[cmd('npm','install'),cmd('npm','run','unit')]},
 'vitejs/vite':{manifest:'package.json',ecosystem:'npm',name:'vite',commands:[cmd('corepack','pnpm','install','--no-frozen-lockfile','--config.strict-dep-builds=false'),cmd('pnpm','build'),cmd('pnpm','run','test-unit')]},
 'sinatra/sinatra':{manifest:'Gemfile',ecosystem:'gem',name:'sinatra',commands:[cmd('bundle','install'),cmd('bundle','exec','rake')]},
 'google/gson':{manifest:'pom.xml',ecosystem:'maven',name:'com.google.code.gson:gson',commands:[cmd('mvn','clean','test','--projects','gson','--activate-profiles','gson-subset')]},
 'BurntSushi/ripgrep':{manifest:'Cargo.toml',ecosystem:'cargo',name:'ripgrep',commands:[cmd('cargo','test','--verbose','--workspace','--features','unstable-index'),cmd('cargo','test','--verbose','--workspace','--features','pcre2')]},
};
const config=configs[target];if(!config)throw new Error('No frozen upstream test producer selected for '+target);
const record={status:'running',scope:'Actual frozen Linux CI runtime test producer for '+target+'; independent of product-inferred test-plan coverage',source_sha:execFileSync('git',['-C',source,'rev-parse','HEAD'],{encoding:'utf8'}).trim(),commands:[],started_at:new Date().toISOString()};
const save=()=>fs.writeFile(path.join(out,'upstream-control.json'),JSON.stringify(record,null,2)+'\n');
try{
 const prepared=await repositoryEnvironment({rootDir:source,manifestPath:config.manifest,ecosystem:config.ecosystem,packageName:config.name,deadlineAt});record.environment=prepared.log;adoptEnvironment(prepared.env);
 if(target==='fastapi/fastapi')process.env.COVERAGE_FILE=path.join(source,'coverage','.coverage.linux-control');
 if(target==='fastify/fastify')delete process.env.NODE_ENV;
 if(target==='puma/puma')delete process.env.PUMA_NO_RUBOCOP;
 if(target==='vuejs/core')process.env.PUPPETEER_SKIP_DOWNLOAD='true';
 if(target==='trpc/trpc')process.env.MUTE_REACT_ACT_WARNINGS='1';
 if(target==='sinatra/sinatra')for(const name of ['rack','rack_session','puma','tilt','zeitwerk'])process.env[name]='stable';
 const commands=config.commands;
 for(const command of commands){const result=await runRepositoryValidationCommand(source,'.',command,Math.max(1,deadlineAt-Date.now()),deadlineAt);record.commands.push(result);await save();if(result.exitCode!==0)break;}
 record.status=record.commands.length===commands.length&&record.commands.every(c=>c.exitCode===0)?'passed':'original_ci_producer_failed';
}catch(error){record.status='control_error';record.error=error instanceof Error?error.message:String(error);}
record.finished_at=new Date().toISOString();await save();process.exitCode=record.status==='passed'?0:2;
