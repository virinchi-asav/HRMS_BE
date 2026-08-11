from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.hrms.core.constants import ADMIN_ONLY
from app.hrms.core.deps import get_hrms_db, require_role
from app.hrms.schemas.client import ClientResponse, ClientUpsertRequest
from app.hrms.services import client_service
from app.utils.pagination import page_result_to_dict

router = APIRouter(prefix="/api/hrms/clients", tags=["hrms-clients"], dependencies=[Depends(require_role(*ADMIN_ONLY))])


@router.get("")
async def list_clients(page: int = 0, size: int = 10, search: str | None = None, db: AsyncSession = Depends(get_hrms_db)):
    result = await client_service.list_clients(db, page, size, search)
    return page_result_to_dict(result, lambda c: ClientResponse.model_validate(c).model_dump())


@router.post("", response_model=ClientResponse)
async def create_client(payload: ClientUpsertRequest, db: AsyncSession = Depends(get_hrms_db)):
    return await client_service.create_client(db, payload)


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(client_id: int, db: AsyncSession = Depends(get_hrms_db)):
    entity = await client_service.get_client(db, client_id)
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return entity


@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(client_id: int, payload: ClientUpsertRequest, db: AsyncSession = Depends(get_hrms_db)):
    entity = await client_service.update_client(db, client_id, payload)
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return entity


@router.delete("/{client_id}")
async def delete_client(client_id: int, db: AsyncSession = Depends(get_hrms_db)):
    ok = await client_service.delete_client(db, client_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return {"message": "Client deleted"}


@router.post("/{client_id}/restore")
async def restore_client(client_id: int, db: AsyncSession = Depends(get_hrms_db)):
    ok = await client_service.restore_client(db, client_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return {"message": "Client restored"}
