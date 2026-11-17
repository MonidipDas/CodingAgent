"""Single-user web server for the Docker coding agent."""
from collections import deque
import os
from pathlib import Path
import subprocess
import sys
import threading
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field


app = FastAPI(title="CodingAgent", docs_url=None, redoc_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]"])
lock = threading.Lock()
jobs = {}


@app.middleware("http")
async def local_access(request: Request, call_next):
    if request.client is None or request.client.host not in {"127.0.0.1", "::1"}:
        return JSONResponse({"detail": "This app accepts local connections only"}, status_code=403)
    origin = request.headers.get("origin")
    if request.method == "POST" and origin and origin != str(request.base_url).rstrip("/"):
        return JSONResponse({"detail": "Cross-origin requests are not allowed"}, status_code=403)
    return await call_next(request)


class Task(BaseModel):
    prompt: str = Field(min_length=1, max_length=12000)
    steps: int = Field(default=15, ge=1, le=50)


def run_job(job_id, workspace, task):
    try:
        # Fixed executable and argument list. Task text never enters a host shell.
        with subprocess.Popen(
            [sys.executable, "-u", "-m", "agent", "--steps", str(task.steps), "--", str(workspace), task.prompt],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", errors="replace",
        ) as process:
            for line in process.stdout:
                with lock:
                    jobs[job_id]["logs"].append(line[-4000:])
            code = process.wait()
        with lock:
            jobs[job_id]["status"] = "completed" if code == 0 else "failed"
            jobs[job_id]["exit_code"] = code
    except Exception:
        with lock:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["logs"].append("Worker failed to start or read output. Check server logs.")


@app.get("/", response_class=HTMLResponse)
def home():
    return PAGE


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/jobs", status_code=202)
def submit(task: Task):
    configured = os.getenv("AGENT_WORKSPACE")
    if not configured or not os.getenv("GROQ_API_KEY"):
        raise HTTPException(503, "Configure AGENT_WORKSPACE and GROQ_API_KEY on the server")
    workspace = Path(configured).resolve()
    if not workspace.is_dir():
        raise HTTPException(503, "Configured workspace is unavailable")
    with lock:
        if any(job["status"] == "running" for job in jobs.values()):
            raise HTTPException(409, "A task is already running. Wait for it to finish.")
        if len(jobs) >= 50:
            jobs.pop(next(iter(jobs)))
        job_id = uuid.uuid4().hex
        jobs[job_id] = {"status": "running", "logs": deque(maxlen=200), "exit_code": None}
        threading.Thread(target=run_job, args=(job_id, workspace, task), daemon=True).start()
    return {"id": job_id}


@app.get("/api/jobs/{job_id}")
def status(job_id: str):
    with lock:
        job = jobs.get(job_id)
        if job is None:
            raise HTTPException(404, "Task not found")
        return {"status": job["status"], "logs": "".join(job["logs"]), "exit_code": job["exit_code"]}


PAGE = """<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CodingAgent</title>
<style>
body{margin:0;background:#101817;color:#e6eee9;font:16px system-ui,sans-serif}
main{max-width:850px;margin:60px auto;padding:24px}h1{font-size:36px;letter-spacing:-1px}
label{display:block;margin:24px 0 8px}input,textarea,button{font:inherit;border-radius:8px;padding:12px;box-sizing:border-box}
input,textarea{width:100%;background:#1c2825;color:inherit;border:1px solid #496158}
textarea{min-height:150px}button{margin-top:18px;background:#b9eebd;border:0;color:#142a19;cursor:pointer}
button:disabled{opacity:.5;cursor:wait}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#17221e;padding:20px;border-radius:8px;max-height:500px;overflow:auto}
#status{color:#b9eebd}p{line-height:1.6}
</style><main><h1>CodingAgent</h1><p>Describe a change for the server workspace. The agent retrieves relevant code, edits files, and runs checks inside Docker.</p>
<form id="form">
<label for="task">Coding task</label><textarea id="task" maxlength="12000" required placeholder="Add input validation and run the existing tests"></textarea>
<button id="run">Run task</button></form><p id="status" role="status">Ready</p><pre id="logs" aria-label="Task output">Task output will appear here.</pre></main>
<script>
const form=document.getElementById('form'), button=document.getElementById('run');
const state=document.getElementById('status'), logs=document.getElementById('logs');
async function request(url, options={}) {
  const response=await fetch(url,{...options,headers:{'Content-Type':'application/json'}});
  const body=await response.json();
  if(!response.ok) throw new Error(typeof body.detail==='string'?body.detail:'Request failed');
  return body;
}
form.addEventListener('submit',async event=>{
  event.preventDefault(); button.disabled=true; state.textContent='Starting'; logs.textContent='';
  try {
    const job=await request('/api/jobs',{method:'POST',body:JSON.stringify({prompt:document.getElementById('task').value})});
    let result;
    do {
      await new Promise(resolve=>setTimeout(resolve,1500));
      result=await request('/api/jobs/'+job.id);
      state.textContent=result.status; logs.textContent=result.logs || 'Working…';
    } while(result.status==='running');
  } catch(error) {state.textContent=error.message;}
  finally {button.disabled=false;}
});
</script></html>"""
