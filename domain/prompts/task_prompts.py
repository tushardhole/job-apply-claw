"""Task prompt builders that create the initial user message for the agent."""

from __future__ import annotations

import json

from domain.models import UserProfile


def build_apply_task_prompt(
    *,
    job_url: str,
    company_name: str,
    job_title: str,
    profile: UserProfile,
    resume_available: bool,
    cover_letter_available: bool,
    debug: bool,
) -> str:
    """Build the task prompt the LLM receives as its first user message."""

    profile_block = json.dumps(
        {
            "full_name": profile.full_name,
            "email": profile.email,
            "phone": profile.phone,
            "address": profile.address,
        },
        indent=2,
    )

    debug_line = (
        "debug: true  (do NOT click the final submit button)"
        if debug
        else "debug: false  (click the final submit button when ready)"
    )

    return (
        f"Apply to the following job:\n"
        f"\n"
        f"  URL:     {job_url}\n"
        f"  Company: {company_name}\n"
        f"  Title:   {job_title}\n"
        f"\n"
        f"User profile (static fields -- use these directly):\n"
        f"{profile_block}\n"
        f"\n"
        f"Available documents:\n"
        f"  resume:       {'yes' if resume_available else 'no'}\n"
        f"  cover_letter: {'yes' if cover_letter_available else 'no'}\n"
        f"\n"
        f"Mode:\n"
        f"  {debug_line}\n"
        f"\n"
        f"Start by navigating to the job URL and observing the page."
    )
