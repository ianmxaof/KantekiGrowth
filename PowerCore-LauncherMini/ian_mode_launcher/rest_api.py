from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import PlainTextResponse, FileResponse
from auto_updater_agent import check_for_update, apply_update
from log_prompt_sync_agent import sync_to_cloud, repair_logs
from agent_health_monitor import get_status
from crash_reporter_agent import report_crash
from plugin_security_scanner import scan_plugin
import json
import os
import psutil

app = FastAPI()

SWARM_HEALTH_LOG = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../swarm_health.log'))
AGENT_LOGS = {
    'rest_api': 'bootstrap_gui.log',
    'main_exe': 'logs/ian_mode_launcher.log',
    'gui': 'logs/ian_mode_launcher_gui.log',
}

@app.get("/status")
def status():
    return get_status()

@app.get("/plugins")
def plugins():
    with open('plugin_registry.json') as f:
        return json.load(f)

@app.post("/update")
def update():
    url, hash_ = check_for_update()
    if url:
        return {"updated": apply_update(url, hash_)}
    return {"updated": False}

@app.post("/sync")
def sync():
    sync_to_cloud()
    repair_logs()
    return {"synced": True}

@app.post("/crash_report")
def crash_report(file: UploadFile = File(...)):
    # Accepts crash report file (stub)
    return {"received": True}

@app.post("/scan_plugin")
def scan(file: UploadFile = File(...)):
    # Save uploaded file and scan
    path = f"tmp_{file.filename}"
    with open(path, 'wb') as f:
        f.write(file.file.read())
    result = scan_plugin(path)
    return {"safe": result}

@app.get("/swarm_health")
def swarm_health():
    if not os.path.exists(SWARM_HEALTH_LOG):
        raise HTTPException(status_code=404, detail="Swarm health log not found.")
    with open(SWARM_HEALTH_LOG, 'r') as f:
        return PlainTextResponse(f.read())

@app.post("/restart_agent")
def restart_agent(request: Request):
    data = request.json() if request.headers.get('content-type') == 'application/json' else {}
    name = data.get('name')
    if not name:
        raise HTTPException(status_code=400, detail="Agent name required.")
    killed = False
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            if name in proc.info['name'] or (proc.info['cmdline'] and name in ' '.join(proc.info['cmdline'])):
                proc.kill()
                killed = True
        except Exception:
            continue
    # Stub: launch logic (should match your launcher logic)
    # For now, just return status
    return {"restarted": killed}

@app.post("/kill_agent")
def kill_agent(request: Request):
    data = request.json() if request.headers.get('content-type') == 'application/json' else {}
    name = data.get('name')
    if not name:
        raise HTTPException(status_code=400, detail="Agent name required.")
    killed = False
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            if name in proc.info['name'] or (proc.info['cmdline'] and name in ' '.join(proc.info['cmdline'])):
                proc.kill()
                killed = True
        except Exception:
            continue
    return {"killed": killed}

@app.get("/logs")
def get_logs(agent: str):
    log_path = AGENT_LOGS.get(agent)
    if not log_path or not os.path.exists(log_path):
        raise HTTPException(status_code=404, detail="Log file not found.")
    return FileResponse(log_path)

@app.get("/config")
def get_config():
    # Stub: return static config
    return {"config": "stub"}

@app.post("/config")
def set_config(request: Request):
    # Stub: accept and log config
    data = request.json() if request.headers.get('content-type') == 'application/json' else {}
    return {"received": data}

@app.post("/backup_restore")
def backup_restore(request: Request):
    # Stub: trigger backup/restore
    data = request.json() if request.headers.get('content-type') == 'application/json' else {}
    return {"status": "backup/restore stub", "received": data}

@app.get("/resource_usage")
def resource_usage():
    usage = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info', 'cwd']):
        try:
            name = proc.info['name']
            cmd = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
            cpu = proc.cpu_percent(interval=0.1)
            mem = proc.memory_info().rss // 1024
            cwd = proc.info.get('cwd', '')
            usage.append({
                'pid': proc.info['pid'],
                'name': name,
                'cmd': cmd,
                'cpu': cpu,
                'mem_kb': mem,
                'cwd': cwd
            })
        except Exception:
            continue
    return usage

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("rest_api:app", host="127.0.0.1", port=8000, reload=True) 