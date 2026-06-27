from types import SimpleNamespace

from app.services.candidate_pipeline import STAGE_STATUS, resolve_pipeline_stage


def test_pipeline_stage_prioritizes_pending_review():
    candidate = SimpleNamespace(status="resume_requested")

    stage, label, next_action = resolve_pipeline_stage(
        candidate,
        resume_count=1,
        parsed_resume_count=1,
        best_score=88.0,
        pending_action_count=1,
    )

    assert stage == "pending_review"
    assert STAGE_STATUS[stage] == "pending_review"
    assert label == "待人工确认"
    assert next_action == "处理待确认动作"


def test_pipeline_stage_scored_when_score_exists_without_pending_action():
    candidate = SimpleNamespace(status="resume_requested")

    stage, label, next_action = resolve_pipeline_stage(
        candidate,
        resume_count=1,
        parsed_resume_count=1,
        best_score=92.0,
        pending_action_count=0,
    )

    assert stage == "scored"
    assert STAGE_STATUS[stage] == "scored"
    assert label == "已评分"
    assert next_action == "等待每日推荐或人工筛选"


def test_pipeline_stage_keeps_resume_requested_without_resume():
    candidate = SimpleNamespace(status="resume_requested")

    stage, label, next_action = resolve_pipeline_stage(
        candidate,
        resume_count=0,
        parsed_resume_count=0,
        best_score=None,
        pending_action_count=0,
    )

    assert stage == "resume_requested"
    assert STAGE_STATUS[stage] == "resume_requested"
    assert label == "已索要简历"
    assert next_action == "等待候选人发送简历"
