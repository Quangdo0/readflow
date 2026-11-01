from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)

from app.api.dependencies import (
    get_current_user,
    get_document_service,
)
from app.models.user import User
from app.schemas.document import (
    DocumentCreate,
    DocumentRead,
    DocumentUpdate,
)
from app.services.document import (
    DocumentConflictError,
    DocumentForbiddenError,
    DocumentNotFoundError,
    DocumentService,
)


router = APIRouter(
    prefix="/documents",
    tags=["documents"],
)


@router.post(
    "",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_document(
    data: DocumentCreate,
    current_user: User = Depends(
        get_current_user
    ),
    service: DocumentService = Depends(
        get_document_service
    ),
):
    return await service.create_document(
        data=data,
        actor=current_user,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentRead,
)
async def get_document(
    document_id: int,
    current_user: User = Depends(
        get_current_user
    ),
    service: DocumentService = Depends(
        get_document_service
    ),
):
    try:
        return await service.get_document(
            document_id=document_id,
            actor=current_user,
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=list[DocumentRead],
)
async def list_documents(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    current_user: User = Depends(
        get_current_user
    ),
    service: DocumentService = Depends(
        get_document_service
    ),
):
    return await service.list_documents(
        actor=current_user,
        limit=limit,
        offset=offset,
    )

@router.patch(
    "/{document_id}",
    response_model=DocumentRead,
)
async def update_document(
    document_id: int,
    data: DocumentUpdate,
    current_user: User = Depends(
        get_current_user
    ),
    service: DocumentService = Depends(
        get_document_service
    ),
):
    try:
        return await service.update_document(
            document_id=document_id,
            data=data,
            actor=current_user,
        )

    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except DocumentForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except DocumentConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document(
    document_id: int,
    current_user: User = Depends(
        get_current_user
    ),
    service: DocumentService = Depends(
        get_document_service
    ),
):
    try:
        await service.delete_document(
            document_id=document_id,
            actor=current_user,
        )

    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
