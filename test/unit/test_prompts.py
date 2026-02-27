from domain.models import UserProfile
from domain.prompts import SYSTEM_PROMPT, build_apply_task_prompt


def test_system_prompt_contains_static_field_rules() -> None:
    assert "Static fields" in SYSTEM_PROMPT
    assert "full name" in SYSTEM_PROMPT.lower()
    assert "email" in SYSTEM_PROMPT.lower()


def test_system_prompt_contains_dynamic_field_rules() -> None:
    assert "Dynamic fields" in SYSTEM_PROMPT
    assert "salary" in SYSTEM_PROMPT.lower()
    assert "work authorization" in SYSTEM_PROMPT.lower()
    assert "ask_user" in SYSTEM_PROMPT


def test_system_prompt_distinguishes_final_from_intermediate_submit() -> None:
    assert "FINAL submit" in SYSTEM_PROMPT
    assert "Next" in SYSTEM_PROMPT
    assert "Continue" in SYSTEM_PROMPT


def test_system_prompt_debug_skip_final_submit() -> None:
    assert "context.debug is true" in SYSTEM_PROMPT
    assert "skipped" in SYSTEM_PROMPT


def test_system_prompt_password_reset_rules() -> None:
    assert "Forgot Password" in SYSTEM_PROMPT
    assert "reset" in SYSTEM_PROMPT.lower()


def test_system_prompt_captcha_rules() -> None:
    assert "Text captcha" in SYSTEM_PROMPT
    assert "Image captcha" in SYSTEM_PROMPT


def test_build_apply_task_prompt_contains_job_info() -> None:
    profile = UserProfile(full_name="Jane", email="jane@test.com")
    prompt = build_apply_task_prompt(
        job_url="https://example.com/jobs/1",
        company_name="Example Corp",
        job_title="SWE",
        profile=profile,
        resume_available=True,
        cover_letter_available=False,
        debug=False,
    )
    assert "https://example.com/jobs/1" in prompt
    assert "Example Corp" in prompt
    assert "SWE" in prompt


def test_build_apply_task_prompt_contains_profile() -> None:
    profile = UserProfile(
        full_name="Jane Doe",
        email="jane@test.com",
        phone="+1234567890",
        address="123 Main St",
    )
    prompt = build_apply_task_prompt(
        job_url="https://x.com/j/1",
        company_name="X",
        job_title="T",
        profile=profile,
        resume_available=True,
        cover_letter_available=True,
        debug=False,
    )
    assert "Jane Doe" in prompt
    assert "jane@test.com" in prompt
    assert "+1234567890" in prompt
    assert "123 Main St" in prompt


def test_build_apply_task_prompt_debug_true() -> None:
    profile = UserProfile(full_name="A", email="a@b.com")
    prompt = build_apply_task_prompt(
        job_url="https://x.com",
        company_name="X",
        job_title="T",
        profile=profile,
        resume_available=True,
        cover_letter_available=True,
        debug=True,
    )
    assert "debug: true" in prompt
    assert "do NOT click the final submit" in prompt


def test_build_apply_task_prompt_debug_false() -> None:
    profile = UserProfile(full_name="A", email="a@b.com")
    prompt = build_apply_task_prompt(
        job_url="https://x.com",
        company_name="X",
        job_title="T",
        profile=profile,
        resume_available=True,
        cover_letter_available=True,
        debug=False,
    )
    assert "debug: false" in prompt
    assert "click the final submit button when ready" in prompt


def test_build_apply_task_prompt_document_availability() -> None:
    profile = UserProfile(full_name="A", email="a@b.com")

    prompt_both = build_apply_task_prompt(
        job_url="https://x.com", company_name="X", job_title="T",
        profile=profile, resume_available=True, cover_letter_available=True, debug=False,
    )
    assert "resume:       yes" in prompt_both
    assert "cover_letter: yes" in prompt_both

    prompt_none = build_apply_task_prompt(
        job_url="https://x.com", company_name="X", job_title="T",
        profile=profile, resume_available=False, cover_letter_available=False, debug=False,
    )
    assert "resume:       no" in prompt_none
    assert "cover_letter: no" in prompt_none
