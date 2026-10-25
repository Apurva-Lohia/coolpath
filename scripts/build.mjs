/** Dependency-free, deterministic static build. Never copies private/source inputs. */
import {cpSync,existsSync,mkdirSync,readFileSync,readdirSync,rmSync,statSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root=fileURLToPath(new URL('../',import.meta.url));
const source=path.join(root,'dist'),output=path.join(root,'build');
const allowed=['index.html','app.mjs','routing.mjs','style.css','vendor','data'];
for(const name of allowed)if(!existsSync(path.join(source,name)))throw new Error(`Missing static asset: ${name}`);
function validate(dir){for(const name of readdirSync(dir)){const p=path.join(dir,name);if(statSync(p).isDirectory())validate(p);else if(!/\.(html|mjs|js|css|json|md)$/.test(name)&&name!=='LICENSE')throw new Error(`Unexpected static file: ${p}`);}}
validate(source);
if(!readFileSync(path.join(source,'index.html'),'utf8').includes('CoolPath'))throw new Error('Missing application entrypoint');
rmSync(output,{recursive:true,force:true});mkdirSync(output);
for(const name of allowed)cpSync(path.join(source,name),path.join(output,name),{recursive:true});
console.log('Built static CoolPath in build/ (no external build dependencies).');
