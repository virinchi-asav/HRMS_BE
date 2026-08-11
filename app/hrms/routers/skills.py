from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.hrms.core.deps import CurrentHrmsUser, get_current_hrms_user, get_hrms_db
from app.hrms.models.user import UserEntity
from app.hrms.schemas.skill import SkillResponse, SkillReviewRequest, SkillUpsertRequest
from app.hrms.services import skill_service
from app.utils.pagination import page_result_to_dict

router = APIRouter(prefix="/api/hrms/skills", tags=["hrms-skills"], dependencies=[Depends(get_current_hrms_user)])


@router.get("")
async def list_skills(
    page: int = 0,
    size: int = 10,
    department: str | None = None,
    skills: list[str] | None = Query(None),
    active_in_the_project: int | None = None,
    skill_gap: str | None = None,
    reporter_id: list[int] | None = Query(None),
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    db: AsyncSession = Depends(get_hrms_db),
):
    user = await db.get(UserEntity, current_user.id)
    result = await skill_service.list_skills(
        db, user, page, size, department, skills, active_in_the_project, skill_gap, reporter_id
    )
    page_dict = page_result_to_dict(result["page"], lambda s: SkillResponse.model_validate(s).model_dump())
    names = await skill_service.get_user_names(db, {item["user_id"] for item in page_dict["content"]})
    for item in page_dict["content"]:
        item["user_name"] = names.get(item["user_id"])

    return {
        "page": page_dict,
        "departments": result["departments"],
        "full_skills": result["full_skills"],
        "department_proficiencies": result["department_proficiencies"],
        "total_unpaginated": len(result["skills_without_pagination"]),
        "reporters": [{"id": r.id, "name": r.name} for r in result["reporters"]],
    }


@router.get("/form-options")
async def form_options(
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user), db: AsyncSession = Depends(get_hrms_db)
):
    user = await db.get(UserEntity, current_user.id)
    return {
        "skill_configs": [
            {"id": c.id, "skill_name": c.skill_name, "skill_category": c.skill_category}
            for c in await skill_service.get_skill_configs_for_department(db, user.department)
        ],
        "accounts": await skill_service.get_accounts(db),
        "used_skill_names": await skill_service.get_used_skill_names(db, current_user.id),
    }


@router.get("/export")
async def export_skills(
    department: str | None = None,
    skills: list[str] | None = Query(None),
    active_in_the_project: int | None = None,
    skill_gap: str | None = None,
    reporter_id: list[int] | None = Query(None),
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    db: AsyncSession = Depends(get_hrms_db),
):
    user = await db.get(UserEntity, current_user.id)
    content = await skill_service.export_skills_xlsx(
        db, user, department, skills, active_in_the_project, skill_gap, reporter_id
    )
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=filtered_skills.xlsx"},
    )


@router.post("/attachments")
async def upload_attachment(
    file: UploadFile = File(...), current_user: CurrentHrmsUser = Depends(get_current_hrms_user)
):
    stored_name = await skill_service.upload_staged_attachment(current_user.id, file)
    return {"filename": stored_name}


@router.get("/{skill_id}", response_model=SkillResponse)
async def get_skill(skill_id: str, db: AsyncSession = Depends(get_hrms_db)):
    skill = await skill_service.get_skill_by_skill_id(db, skill_id)
    if skill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    return skill


@router.post("", response_model=SkillResponse)
async def create_skill(
    payload: SkillUpsertRequest,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    db: AsyncSession = Depends(get_hrms_db),
):
    user = await db.get(UserEntity, current_user.id)
    return await skill_service.create_skill(db, user, payload)


@router.put("/{skill_id}")
async def update_skill(
    skill_id: str,
    payload: SkillUpsertRequest,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    db: AsyncSession = Depends(get_hrms_db),
):
    """Branches exactly like SkillController::update: a manager reviewing a direct
    reportee's skill gets the narrow review-only update; everyone else (the skill's
    owner, or an Admin editing a non-reportee's skill) gets the full edit path."""
    skill = await skill_service.get_skill_by_skill_id(db, skill_id)
    if skill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")

    user = await db.get(UserEntity, current_user.id)
    if await skill_service.is_reviewing_reportees_skill(db, user, skill):
        review_payload = SkillReviewRequest(
            start_date=payload.start_date,
            end_date=payload.end_date,
            account=payload.account,
            notes=payload.notes,
            project_name=payload.project_name,
            no_skill_gap=payload.no_skill_gap,
            sub_skills=payload.sub_skills,
        )
        message = await skill_service.update_skill_as_reviewer(db, user, skill, review_payload)
        return {"message": message}

    updated = await skill_service.update_skill_as_owner(db, user, skill, payload)
    return {"message": "Skill configuration updated successfully.", "skill": SkillResponse.model_validate(updated).model_dump()}


@router.delete("/{skill_id}")
async def delete_skill(skill_id: str, db: AsyncSession = Depends(get_hrms_db)):
    ok = await skill_service.delete_skill(db, skill_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    return {"message": "Skill deleted successfully."}


@router.post("/{skill_id}/restore")
async def restore_skill(skill_id: str, db: AsyncSession = Depends(get_hrms_db)):
    ok = await skill_service.restore_skill(db, skill_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    return {"message": "Skill restored"}
