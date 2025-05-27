from app.scheduler import scheduler

def test_jobs_registered() -> None:
    # Three jobs should be registered by name without starting the scheduler
    names = {job.name for job in scheduler.get_jobs()}
    assert {"fetch_all_fixtures", "purge_memory_cache", "purge_old_snapshots"} <= names
