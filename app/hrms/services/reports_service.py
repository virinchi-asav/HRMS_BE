from collections import defaultdict
from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.hrms.models.kms_file_view import KmsFileViewEntity
from app.hrms.models.task_assessment import TaskEntity
from app.hrms.models.training import TrainingProgramEntity
from app.hrms.models.user import UserEntity as HrmsUserEntity
from app.hrms.schemas.reports import (
    CategoryCount,
    KmsAccountUsageCount,
    KmsUsageReportResponse,
    KmsUserActivityRow,
    MonthlyCount,
    ReportSection,
    TrainingReportResponse,
)
from app.models.account import AccountEntity
from app.models.department import DepartmentEntity

UNSPECIFIED_ACCOUNT = "Unspecified"
NOT_LINKED_ACCOUNT = "Not linked to a training"


def _month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _month_range(months: int, today: date) -> tuple[date, list[str]]:
    """Whole-month window ending on the current month (e.g. months=3 covers this month
    and the 2 before it) - returns the window start plus every "YYYY-MM" key in it, in
    order, so a trend chart has a continuous x-axis even for months with zero counts."""
    first_of_this_month = today.replace(day=1)
    year, month = first_of_this_month.year, first_of_this_month.month - (months - 1)
    while month <= 0:
        month += 12
        year -= 1
    range_start = date(year, month, 1)

    keys = []
    y, m = range_start.year, range_start.month
    for _ in range(months):
        keys.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return range_start, keys


async def _account_lookup(kms_db: AsyncSession, account_ids: set[int]) -> dict[int, AccountEntity]:
    if not account_ids:
        return {}
    result = await kms_db.execute(select(AccountEntity).where(AccountEntity.account_id.in_(account_ids)))
    return {a.account_id: a for a in result.scalars().all()}


async def _department_names(kms_db: AsyncSession, department_ids: set[int]) -> dict[int, str]:
    if not department_ids:
        return {}
    result = await kms_db.execute(select(DepartmentEntity).where(DepartmentEntity.department_id.in_(department_ids)))
    return {d.department_id: d.department_name for d in result.scalars().all()}


def _sort_categories(categories: list[CategoryCount], sort: str | None) -> list[CategoryCount]:
    if sort == "count_asc":
        return sorted(categories, key=lambda c: c.count)
    if sort == "name_asc":
        return sorted(categories, key=lambda c: c.account_name.lower())
    return sorted(categories, key=lambda c: c.count, reverse=True)  # default: count_desc


def _build_section(
    items_account_ids: list[int | None],
    items_dates: list[date],
    month_keys: list[str],
    accounts_by_id: dict[int, AccountEntity],
    departments_by_id: dict[int, str],
    unspecified_label: str,
    sort: str | None,
) -> ReportSection:
    by_account_count: dict[tuple[int | None, int | None], int] = defaultdict(int)
    by_month_count: dict[str, int] = {k: 0 for k in month_keys}

    for account_id, item_date in zip(items_account_ids, items_dates):
        account = accounts_by_id.get(account_id) if account_id else None
        department_id = account.department_id if account else None
        by_account_count[(account_id, department_id)] += 1
        key = _month_key(item_date)
        if key in by_month_count:
            by_month_count[key] += 1

    categories = [
        CategoryCount(
            account_id=account_id,
            account_name=(accounts_by_id[account_id].account_name if account_id else unspecified_label),
            department_id=department_id,
            department_name=departments_by_id.get(department_id) if department_id else None,
            count=count,
        )
        for (account_id, department_id), count in by_account_count.items()
    ]
    categories = _sort_categories(categories, sort)

    return ReportSection(
        total=sum(by_month_count.values()),
        by_account=categories,
        by_month=[MonthlyCount(month=k, count=by_month_count[k]) for k in month_keys],
    )


async def get_training_report(
    hrms_db: AsyncSession,
    kms_db: AsyncSession,
    months: int,
    account_ids: list[int] | None,
    department_ids: list[int] | None,
    status: str | None,
    sort: str | None,
) -> TrainingReportResponse:
    today = datetime.utcnow().date()
    range_start, month_keys = _month_range(months, today)

    # --- Training Programs: grouped/filtered by their own account_id ---
    training_stmt = select(TrainingProgramEntity).where(
        TrainingProgramEntity.start_date >= range_start, TrainingProgramEntity.start_date <= today
    )
    if status:
        training_stmt = training_stmt.where(TrainingProgramEntity.status == status)
    trainings = (await hrms_db.execute(training_stmt)).scalars().all()

    # --- Task Assessments: grouped via their linked Training's account_id (standalone
    # tasks with no training_id are bucketed separately, not excluded) ---
    task_stmt = select(TaskEntity).where(
        TaskEntity.created_at >= datetime.combine(range_start, time.min),
        TaskEntity.created_at <= datetime.combine(today, time.max),
    )
    tasks = (await hrms_db.execute(task_stmt)).scalars().all()
    linked_training_ids = {t.training_id for t in tasks if t.training_id}
    linked_trainings: dict[int, TrainingProgramEntity] = {}
    if linked_training_ids:
        result = await hrms_db.execute(
            select(TrainingProgramEntity).where(TrainingProgramEntity.id.in_(linked_training_ids))
        )
        linked_trainings = {t.id: t for t in result.scalars().all()}

    all_account_ids = {t.account_id for t in trainings if t.account_id}
    all_account_ids |= {lt.account_id for lt in linked_trainings.values() if lt.account_id}
    accounts_by_id = await _account_lookup(kms_db, all_account_ids)
    departments_by_id = await _department_names(kms_db, {a.department_id for a in accounts_by_id.values() if a.department_id})

    if account_ids:
        trainings = [t for t in trainings if t.account_id in account_ids]
    if department_ids:
        trainings = [
            t
            for t in trainings
            if t.account_id
            and accounts_by_id.get(t.account_id)
            and accounts_by_id[t.account_id].department_id in department_ids
        ]

    training_section = _build_section(
        [t.account_id for t in trainings],
        [t.start_date for t in trainings],
        month_keys,
        accounts_by_id,
        departments_by_id,
        UNSPECIFIED_ACCOUNT,
        sort,
    )

    def _task_account_id(task: TaskEntity) -> int | None:
        if not task.training_id:
            return None
        training = linked_trainings.get(task.training_id)
        return training.account_id if training else None

    filtered_tasks = tasks
    if account_ids:
        filtered_tasks = [t for t in filtered_tasks if _task_account_id(t) in account_ids]
    if department_ids:
        filtered_tasks = [
            t
            for t in filtered_tasks
            if _task_account_id(t)
            and accounts_by_id.get(_task_account_id(t))
            and accounts_by_id[_task_account_id(t)].department_id in department_ids
        ]

    task_section = _build_section(
        [_task_account_id(t) for t in filtered_tasks],
        [t.created_at.date() if isinstance(t.created_at, datetime) else t.created_at for t in filtered_tasks],
        month_keys,
        accounts_by_id,
        departments_by_id,
        NOT_LINKED_ACCOUNT,
        sort,
    )

    return TrainingReportResponse(
        range_start=range_start,
        range_end=today,
        months=months,
        training_programs=training_section,
        task_assessments=task_section,
    )


async def get_kms_usage_report(
    hrms_db: AsyncSession,
    kms_db: AsyncSession,
    days: int | None,
    start_date: date | None,
    end_date: date | None,
    account_id: int | None,
) -> KmsUsageReportResponse:
    """Who's actively opening files in the KMS Document Library, and how often -
    sourced from KmsFileViewEntity (app.services.content_service.record_file_view).
    A custom start_date/end_date takes priority over `days`; with neither, defaults to
    the last 30 days (inclusive of today)."""
    today = datetime.utcnow().date()
    if start_date or end_date:
        range_end = end_date or today
        range_start = start_date or (range_end - timedelta(days=29))
    else:
        range_start = today - timedelta(days=(days or 30) - 1)
        range_end = today

    stmt = (
        select(
            KmsFileViewEntity.user_id,
            func.count().label("view_count"),
            func.max(KmsFileViewEntity.viewed_at).label("last_viewed_at"),
        )
        .where(
            KmsFileViewEntity.viewed_at >= datetime.combine(range_start, time.min),
            KmsFileViewEntity.viewed_at <= datetime.combine(range_end, time.max),
        )
        .group_by(KmsFileViewEntity.user_id)
    )
    rows = (await hrms_db.execute(stmt)).all()

    user_ids = {r.user_id for r in rows}
    users_by_id: dict[int, HrmsUserEntity] = {}
    if user_ids:
        result = await hrms_db.execute(select(HrmsUserEntity).where(HrmsUserEntity.id.in_(user_ids)))
        users_by_id = {u.id: u for u in result.scalars().all()}

    account_ids = {u.kms_account_id for u in users_by_id.values() if u.kms_account_id}
    accounts_by_id = await _account_lookup(kms_db, account_ids)

    activity: list[KmsUserActivityRow] = []
    for row in rows:
        user = users_by_id.get(row.user_id)
        if user is None:
            continue  # deleted since the view was logged
        user_account_id = user.kms_account_id
        if account_id is not None and user_account_id != account_id:
            continue
        account = accounts_by_id.get(user_account_id) if user_account_id else None
        activity.append(
            KmsUserActivityRow(
                user_id=user.id,
                user_name=user.name,
                email=user.email,
                account_id=user_account_id,
                account_name=account.account_name if account else UNSPECIFIED_ACCOUNT,
                view_count=row.view_count,
                last_viewed_at=row.last_viewed_at,
            )
        )
    activity.sort(key=lambda a: a.view_count, reverse=True)

    by_account_agg: dict[int | None, dict] = {}
    for row in activity:
        bucket = by_account_agg.setdefault(row.account_id, {"account_name": row.account_name, "user_count": 0, "view_count": 0})
        bucket["user_count"] += 1
        bucket["view_count"] += row.view_count
    by_account = sorted(
        (
            KmsAccountUsageCount(account_id=k, account_name=v["account_name"], user_count=v["user_count"], view_count=v["view_count"])
            for k, v in by_account_agg.items()
        ),
        key=lambda c: c.view_count,
        reverse=True,
    )

    return KmsUsageReportResponse(
        range_start=range_start,
        range_end=range_end,
        total_active_users=len(activity),
        total_views=sum(a.view_count for a in activity),
        by_account=by_account,
        users=activity,
    )
