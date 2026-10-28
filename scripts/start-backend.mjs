import {spawn} from 'node:child_process';
import {existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root=fileURLToPath(new URL('../',import.meta.url));
const python=path.join(root,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
if(!existsSync(python)){console.error('Create .venv and install requirements-dev.txt first. See README.md.');process.exit(1);}
const child=spawn(python,['-m','uvicorn','backend.app:app','--host','127.0.0.1','--port','8765'],{cwd:root,stdio:'inherit'});
child.on('error',()=>{console.error('Unable to start the local Python backend.');process.exitCode=1;});
child.on('exit',code=>{process.exitCode=code??1;});
