from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.db.models import Job
from app.schemas.jobs import JobCreate, JobUpdate


def list_jobs(db: Session, *, active_only: bool = False, limit: int = 50, offset: int = 0) -> tuple[list[Job], int]:
    stmt: Select[tuple[Job]] = select(Job)
    count_stmt = select(func.count()).select_from(Job)
    if active_only:
        stmt = stmt.where(Job.is_active.is_(True))
        count_stmt = count_stmt.where(Job.is_active.is_(True))
    total = db.scalar(count_stmt) or 0
    items = list(db.scalars(stmt.order_by(Job.created_at.desc()).limit(limit).offset(offset)))
    return items, total


def get_job(db: Session, job_id: int) -> Job | None:
    return db.get(Job, job_id)


def create_job(db: Session, payload: JobCreate) -> Job:
    job = Job(**payload.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def update_job(db: Session, job: Job, payload: JobUpdate) -> Job:
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(job, key, value)
    db.commit()
    db.refresh(job)
    return job

