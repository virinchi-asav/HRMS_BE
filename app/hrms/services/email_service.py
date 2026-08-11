import logging

import aiosmtplib
from email.message import EmailMessage

from app.hrms.core.config import hrms_settings

logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, html_body: str, cc: str | None = None) -> bool:
    """Generic SMTP sender, replacing Laravel's Mail::to(...)->send(...) - reads the same
    SMTP settings the Laravel .env used (MAIL_HOST/MAIL_PORT/MAIL_USERNAME/MAIL_PASSWORD)."""
    message = EmailMessage()
    message["From"] = f"{hrms_settings.hrms_mail_from_name} <{hrms_settings.hrms_mail_from_address}>"
    message["To"] = to
    if cc:
        message["Cc"] = cc
    message["Subject"] = subject
    message.set_content("This email requires an HTML-capable mail client to view.")
    message.add_alternative(html_body, subtype="html")

    try:
        await aiosmtplib.send(
            message,
            hostname=hrms_settings.hrms_smtp_host,
            port=hrms_settings.hrms_smtp_port,
            username=hrms_settings.hrms_smtp_username or None,
            password=hrms_settings.hrms_smtp_password or None,
            start_tls=hrms_settings.hrms_smtp_use_tls,
        )
        return True
    except (aiosmtplib.SMTPException, OSError) as e:
        logger.error("Error sending email to %s: %s", to, e)
        return False


def _wrap(title: str, *paragraphs: str, link: tuple[str, str] | None = None) -> str:
    """Common HTML shell for the notification emails below - a heading, one or more
    paragraphs, and an optional (url, label) call-to-action link."""
    body = f"<h3>{title}</h3>" + "".join(f"<p>{p}</p>" for p in paragraphs)
    if link:
        url, label = link
        body += f"<p><a href='{url}'>{label}</a></p>"
    return body


# ---------------------------------------------------------------------------
# User onboarding
# ---------------------------------------------------------------------------


async def send_onboarding_email(to_email: str, name: str, password: str) -> bool:
    """Sent once, right after a user account is created (admin quick-add, the external
    HR-system webhook sync, and the bulk XLSX candidate import all call this) - carries
    the temporary password so the new user can actually log in."""
    login_url = f"{hrms_settings.hrms_frontend_base_url}/login"
    html = _wrap(
        f"Welcome to MKS HRMS, {name}!",
        "Your account has been created. Here are your login details:",
        f"<b>Email:</b> {to_email}<br><b>Temporary Password:</b> {password}",
        "Please log in and change your password as soon as possible.",
        link=(login_url, "Log in to MKS HRMS"),
    )
    return await send_email(to_email, "Welcome to MKS HRMS - Your Account Details", html)


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


async def send_training_pending_approval_email(
    bu_head_email: str, bu_head_name: str, topic: str, trainer_name: str, training_id: int
) -> bool:
    """Sent to the BU Head the moment a new Training is created, since it starts life
    PENDING_APPROVAL and only they can approve/reject it."""
    url = f"{hrms_settings.hrms_frontend_base_url}/hrms/training/{training_id}"
    html = _wrap(
        "Training Approval Needed",
        f"Hi {bu_head_name},",
        f"A new training <b>{topic}</b> (Trainer: {trainer_name}) has been created and is awaiting your approval.",
        link=(url, "Review Training"),
    )
    return await send_email(bu_head_email, f"Approval Needed: {topic}", html)


async def send_training_approved_email(to_email: str, to_name: str, topic: str, training_id: int) -> bool:
    """Sent once per recipient when a Training is approved - called once for the
    Trainer and once per Trainee, since each needs their own addressed copy."""
    url = f"{hrms_settings.hrms_frontend_base_url}/hrms/training/{training_id}"
    html = _wrap(
        "Training Approved",
        f"Hi {to_name},",
        f"The training <b>{topic}</b> has been approved and is now active.",
        link=(url, "View Training"),
    )
    return await send_email(to_email, f"Training Approved: {topic}", html)


async def send_training_rejected_email(to_email: str, to_name: str, topic: str, reason: str | None, training_id: int) -> bool:
    """Sent once per recipient when a Training is rejected - called for the HR user who
    created it and for the assigned Trainer (not Trainees, since a training that never
    got approved was never announced to them)."""
    url = f"{hrms_settings.hrms_frontend_base_url}/hrms/training/{training_id}"
    paragraphs = [f"Hi {to_name},", f"The training <b>{topic}</b> has been rejected by the BU Head."]
    if reason:
        paragraphs.append(f"<b>Reason:</b> {reason}")
    html = _wrap("Training Rejected", *paragraphs, link=(url, "View Training"))
    return await send_email(to_email, f"Training Rejected: {topic}", html)


async def send_training_completed_email(hr_email: str, topic: str, trainer_name: str, training_id: int) -> bool:
    """Sent to the HR user who created the Training once its Trainer marks it
    COMPLETED."""
    url = f"{hrms_settings.hrms_frontend_base_url}/hrms/training/{training_id}"
    html = _wrap(
        "Training Completed",
        f"The training <b>{topic}</b> has been marked completed by its Trainer, {trainer_name}.",
        link=(url, "View Training"),
    )
    return await send_email(hr_email, f"Training Completed: {topic}", html)


# ---------------------------------------------------------------------------
# Task assessment
# ---------------------------------------------------------------------------


async def send_task_assigned_email(trainee_email: str, trainee_name: str, task_title: str, time_limit_minutes: int, task_id: int) -> bool:
    """Sent once per trainee the moment they're assigned to a task - both at task
    creation (if trainee_ids were included up front) and via a later assign call."""
    url = f"{hrms_settings.hrms_frontend_base_url}/hrms/task-assessments/{task_id}/take"
    html = _wrap(
        "New Task Assessment Assigned",
        f"Hi {trainee_name},",
        f"You have been assigned a new task assessment: <b>{task_title}</b> "
        f"({time_limit_minutes} minute time limit once started).",
        link=(url, "Take Assessment"),
    )
    return await send_email(trainee_email, f"New Task Assessment: {task_title}", html)


async def send_task_result_email(
    hr_email: str,
    trainee_name: str,
    task_title: str,
    passed: bool | None,
    percentage: float | None,
    marks_obtained: int | None,
    total_marks: int | None,
    task_id: int,
) -> bool:
    """Sent to the HR user who created the task every time a trainee's attempt is
    finalized (submitted, auto-submitted on timeout/tab-switch, or force-closed) -
    fires on both a pass AND a fail, since HR needs to know either way."""
    url = f"{hrms_settings.hrms_frontend_base_url}/hrms/task-assessments/{task_id}/report"
    result_label = "Passed" if passed else "Failed"
    score = f"{marks_obtained} / {total_marks} ({percentage}%)" if percentage is not None else "N/A"
    html = _wrap(
        f"Task Assessment {result_label}",
        f"<b>{trainee_name}</b> has completed the task assessment <b>{task_title}</b>.",
        f"<b>Result:</b> {result_label}<br><b>Score:</b> {score}",
        link=(url, "View Report"),
    )
    return await send_email(hr_email, f"Task Assessment {result_label}: {trainee_name} - {task_title}", html)
