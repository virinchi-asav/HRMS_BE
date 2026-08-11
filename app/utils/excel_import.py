from io import BytesIO

import openpyxl
from fastapi import UploadFile

from app.core.constants import EXCEL_SHEET_CONTENT_TYPE


def has_excel_format(file: UploadFile) -> bool:
    return file.content_type == EXCEL_SHEET_CONTENT_TYPE


async def read_excel_rows(file: UploadFile) -> list[tuple]:
    """Reads sheet 0, skipping the header row.

    Mirrors the Apache POI convention duplicated across AccountServiceImpl,
    CategoryServiceImpl, DepartmentServiceImpl, SubCategoryServiceImpl and
    UserServiceImpl.importUser: sheet index 0, row index 0 is a header, cells read by
    fixed positional index.
    """
    contents = await file.read()
    workbook = openpyxl.load_workbook(BytesIO(contents), data_only=True)
    worksheet = workbook.worksheets[0]
    return [
        row
        for row in worksheet.iter_rows(min_row=2, values_only=True)
        if any(cell is not None for cell in row)
    ]
