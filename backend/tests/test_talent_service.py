from app.db.models import Job
from app.schemas.talents import TalentCard, TalentFilter
from app.services.talent_service import filter_talent_cards, greeting_message


def _card(**updates) -> TalentCard:
    values = {
        "boss_uid": "candidate-1",
        "name": "测试候选人",
        "city": "广州",
        "education_level": "本科",
        "experience": "在校/应届",
        "intention": "Python 开发",
        "expected_salary": "5-10K",
        "skills": ["Python", "RAG"],
        "raw_text": "广州 本科 在校/应届 Python 开发 5-10K RAG",
    }
    values.update(updates)
    return TalentCard(**values)


def test_filter_talent_cards_applies_hard_filters_and_keywords() -> None:
    filters = TalentFilter(
        job_id=1,
        city="广州",
        education=["本科"],
        experience=["应届"],
        intentions=["Python"],
        salary_keywords=["5-10K"],
        required_keywords=["Python", "Java"],
    )
    results = filter_talent_cards([_card(), _card(boss_uid="2", city="深圳", raw_text="深圳 本科 Python")], filters)
    assert len(results) == 1
    assert results[0][1] == ["Python"]


def test_greeting_message_only_requests_resume() -> None:
    job = Job(title="Agent 应用开发实习生")
    message = greeting_message(_card(), job)
    assert "PDF 简历" in message
    assert "薪资承诺" not in message
