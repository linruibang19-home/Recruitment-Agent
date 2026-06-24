from __future__ import annotations

from app.db.models import Candidate, Job


def generate_interview_invite(candidate: Candidate, job: Job) -> str:
    name = candidate.name or "您好"
    return (
        f"{name}，您好。我们已查看您的简历，您的经历与“{job.title}”岗位较为匹配，"
        "希望邀请您参加一次线上面试，进一步沟通岗位内容和项目经历。"
        "请问您近期哪些时间方便？确认后我们再与您约定具体时间。"
    )
