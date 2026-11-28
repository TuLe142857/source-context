import fastapi

router = fastapi.APIRouter()


@router.put(path="/{item_id}")
def update_item(item_id: str): ...
