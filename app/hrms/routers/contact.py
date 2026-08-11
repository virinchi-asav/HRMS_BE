from fastapi import APIRouter
from pydantic import BaseModel, EmailStr

from app.hrms.core.config import hrms_settings
from app.hrms.services.email_service import send_email

router = APIRouter(prefix="/api/hrms/public", tags=["hrms-public"])


class ContactFormRequest(BaseModel):
    """Mirrors the footer contact form (layouts.footer.blade.php) which posted to
    /send-mail -> MksController::sendMailNormal - a method that didn't actually exist in
    the source controller (a dead route). Implemented properly here since the feature
    (a visitor contact form) is clearly intended, even though its backend was missing."""

    name: str
    last_name: str | None = None
    number: str | None = None
    email: EmailStr
    comments: str


@router.post("/contact")
async def submit_contact_form(payload: ContactFormRequest):
    notify_email = hrms_settings.hrms_onboarding_notify_email or hrms_settings.hrms_mail_from_address
    html = (
        f"<p>New contact form submission:</p>"
        f"<p><b>Name:</b> {payload.name} {payload.last_name or ''}<br>"
        f"<b>Email:</b> {payload.email}<br>"
        f"<b>Phone:</b> {payload.number or ''}</p>"
        f"<p>{payload.comments}</p>"
    )
    await send_email(notify_email, "Website Contact Form Submission", html)
    return {"message": "Thank you for contacting us. We will get back to you soon."}
