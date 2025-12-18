# scripts/run_jobs_now.py
"""
Run news_fetch_job and retrain_job synchronously and print JSON output.
Use this from PowerShell to avoid quoting headaches.
"""
import json
from app.scheduler import news_fetch_job, retrain_job

def run():
    print("=== NEWS JOB ===")
    nj = news_fetch_job()
    print(json.dumps(nj, indent=2))
    print()
    print("=== RETRAIN JOB ===")
    rj = retrain_job()
    print(json.dumps(rj, indent=2))

if __name__ == "__main__":
    run()
