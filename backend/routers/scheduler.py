from fastapi import APIRouter, HTTPException
from backend.services.scheduler_service import SchedulerService
from typing import List, Dict, Any

router = APIRouter()
scheduler_service = SchedulerService()

@router.get("/jobs")
async def list_jobs():
    try:
        jobs = []
        for job in scheduler_service.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        return {"jobs": jobs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/trigger/{job_id}")
async def trigger_job(job_id: str):
    try:
        job = scheduler_service.scheduler.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Run the job immediately
        job.modify(next_run_time=None) # Pause? No.
        # To trigger immediately, we can add a one-off job or just call the function if we knew it.
        # APScheduler doesn't have a simple "run now" for existing recurring jobs without modifying them.
        # Easier approach: Add a new job with same func, run date = now.
        
        scheduler_service.scheduler.add_job(job.func, 'date', name=f"{job.name} (Manual Trigger)")
        return {"message": f"Job {job_id} triggered"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
