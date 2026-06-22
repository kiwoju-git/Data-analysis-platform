from typing import Annotated

from fastapi import APIRouter, File, Request, UploadFile, status

from app.api.v1.schemas.datasets import DatasetUploadResponse
from app.services.dataset_upload import create_dataset_from_upload

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post(
    "",
    response_model=DatasetUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_dataset(
    request: Request,
    file: Annotated[UploadFile, File(...)],
) -> DatasetUploadResponse:
    return await create_dataset_from_upload(
        upload_file=file,
        settings=request.app.state.settings,
    )
