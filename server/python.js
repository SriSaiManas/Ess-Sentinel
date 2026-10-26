import {spawn} from 'node:child_process';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
let active=0;
export async function python(operation,args={}){
 if(active>=2)throw Object.assign(new Error('Two analytics tasks are running. Retry shortly.'),{status:429});
 active++;
 try{return await new Promise((resolve,reject)=>{
  const child=spawn(process.env.PYTHON_BIN||'python',[path.join(root,'ml-service/bridge.py')],{cwd:root,env:{...process.env,ARTIFACT_DIR:process.env.ARTIFACT_DIR||path.join(root,'var/artifacts'),OMP_NUM_THREADS:'1',OPENBLAS_NUM_THREADS:'1'},stdio:['pipe','pipe','pipe']});
  let stdout='',stderr='',done=false;
  const finish=(err,data)=>{if(done)return;done=true;clearTimeout(timer);err?reject(err):resolve(data)};
  const timer=setTimeout(()=>{child.kill('SIGKILL');finish(Object.assign(new Error('Analytics timed out; check audit history before retrying a write.'),{status:504}))},Number(process.env.ML_TIMEOUT_MS||300000));
  child.stdout.on('data',b=>{stdout+=b;if(stdout.length>100*1024*1024){child.kill();finish(Object.assign(new Error('Analytics response exceeds limit'),{status:413}))}});
  child.stderr.on('data',b=>{stderr=(stderr+b).slice(-3000)});
  child.on('error',()=>finish(Object.assign(new Error('Python runtime unavailable'),{status:503})));
  child.on('close',()=>{try{const r=JSON.parse(stdout);if(!r.ok)throw Object.assign(new Error(r.error),{status:r.type==='ValueError'?422:503});finish(null,r.data)}catch(e){finish(e.status?e:Object.assign(new Error('Python service failed; inspect runtime dependencies.'),{status:503}))}});
  child.stdin.on('error',()=>{});child.stdin.end(JSON.stringify({operation,args}));
 })}finally{active--}
}
