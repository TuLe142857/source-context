from fastapi import APIRouter, Depends

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}")
async def get_user(user_id: int):
    return {}


@router.post("", status_code=201)
def create_user():
    return {}


class UserView:
    @router.delete("/{user_id}")
    def remove(self, user_id: int): ...


def list_users():
    return []


router.add_api_route("/", list_users, methods=["GET"])
