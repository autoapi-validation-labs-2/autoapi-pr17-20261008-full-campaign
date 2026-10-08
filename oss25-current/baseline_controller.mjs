import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
const [product, source, out] = process.argv.slice(2);
const load = relative => import(pathToFileURL(path.join(product, relative)));
const { discoverRepositoryManifests, isLockfile } = await load('scripts/lib/repository-manifest-scan.mjs');
const { ownershipFor } = await load('scripts/lib/candidate-ownership.mjs');
const { primaryManifestPath, EXECUTOR_SUPPORTED_ECOSYSTEMS } = await load('scripts/lib/executor-admission.mjs');
const { resolveValidationPlan } = await load('packages/part-a/src/replay/repositoryValidationPlan.ts');
const { candidateRepositoryIdentity, createCandidateCheckout, runCandidateProcess } = await load('scripts/lib/isolated-candidate.mjs');
const deadlineAt = Date.now() + 60 * 60_000;
const report = { started_at: new Date().toISOString(), status: 'running', groups: [], excluded_manifests: [], coverage: 'All distinct unchanged-source validation plans for owned project manifests; no dependency edits, models or publication.' };
const save = () => fs.writeFile(path.join(out, 'independent-baseline.json'), JSON.stringify(report, null, 2) + '\n');
await save();
try {
  const manifests = await discoverRepositoryManifests(source);
  const ownership = await ownershipFor(source, { manifests });
  const identity = await candidateRepositoryIdentity(source, deadlineAt);
  report.source_sha = identity.baseSha;
  const byDirectory = new Map();
  for (const manifest of manifests) {
    if (!EXECUTOR_SUPPORTED_ECOSYSTEMS.has(manifest.ecosystem) || isLockfile(manifest.path)) continue;
    const verdict = ownership.classifyManifest(manifest.path);
    if (!verdict.owned) { report.excluded_manifests.push({ path: manifest.path, reason: verdict.reason }); continue; }
    const key = `${manifest.ecosystem}:${path.posix.dirname(manifest.path)}`;
    const previous = byDirectory.get(key);
    if (previous === undefined || primaryManifestPath(manifest.ecosystem, [previous.path, manifest.path]) === manifest.path) byDirectory.set(key, manifest);
  }
  const seen = new Map();
  for (const [key, manifest] of byDirectory) {
    if (Date.now() >= deadlineAt) { report.groups.push({key, manifest: manifest.path, status:'not_attempted_baseline_deadline'}); continue; }
    const directory = path.posix.dirname(manifest.path).replace(/^\.$/, '');
    const packageName = manifest.dependencies?.find(d => d.name)?.name ?? 'unchanged-source-baseline';
    const plan = await resolveValidationPlan(source, directory, manifest.ecosystem, packageName, [manifest.path]);
    const checks = plan.validationCommands?.length ? plan.validationCommands : plan.testCommands.map(command => ({ command, workingDirectory: directory || '.', origin: plan.source }));
    const fingerprint = JSON.stringify({ ecosystem: manifest.ecosystem, prepare: plan.prepareCommands, install: plan.installCommand, installDirectory: plan.installWorkingDirectory ?? (directory || '.'), checks });
    if (seen.has(fingerprint)) { report.groups.push({key, manifest:manifest.path, status:'covered_by_identical_plan', covered_by:seen.get(fingerprint), plan}); await save(); continue; }
    const index = report.groups.length;
    seen.set(fingerprint, key);
    const work = path.join(path.dirname(source), `independent-baseline-${index}`);
    await createCandidateCheckout(identity, work, deadlineAt);
    const request = path.join(out, `independent-baseline-request-${index}.json`);
    const result = path.join(out, `independent-baseline-result-${index}.json`);
    await fs.writeFile(request, JSON.stringify({ work, directory, manifest:manifest.path, ecosystem:manifest.ecosystem, packageName, result, deadlineAt, sourceSha:identity.baseSha }));
    const processResult = await runCandidateProcess({ command:process.execPath, args:['--import',path.join(product,'packages/part-a/node_modules/tsx/dist/loader.mjs'),path.join(import.meta.dirname,'baseline_worker.mjs'),product,request], cwd:product, env:process.env, deadlineAt, trackDescendants:true });
    let observed; try { observed = JSON.parse(await fs.readFile(result,'utf8')); } catch { observed = {status:'worker_failed_without_report', stderr:processResult.stderr?.slice(-8000)}; }
    report.groups.push({ key, manifest:manifest.path, source_sha:identity.baseSha, worker_status:processResult.status, ...observed });
    await save();
    if (!String(processResult.reason ?? '').includes('cleanup_failed')) await fs.rm(work, {recursive:true,force:true});
    else { report.status='baseline_control_error'; throw new Error('Baseline descendant cleanup failed; no workspace reuse'); }
  }
  report.status = report.groups.every(g => ['passed','covered_by_identical_plan'].includes(g.status)) ? 'passed' : 'baseline_failures_recorded';
} catch(error) { report.status='baseline_control_error';report.error=error instanceof Error ? error.message : String(error); }
report.finished_at = new Date().toISOString();await save();
process.exitCode = report.status === 'passed' ? 0 : 2;
