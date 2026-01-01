from fastapi import APIRouter , Depends , HTTPException , status  , Cookie , Response
from UAA.schemas import UserCreateSchema
from sqlalchemy.ext.asyncio import AsyncSession
from dependencies.db import get_session_dep
from UAA.repository import UserRepository
from UAA.services import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=dict)
async def sign_up(user_in: UserCreateSchema , db_session : AsyncSession = Depends(get_session_dep)):
    repo = UserRepository(db_session)
    service = UserService(repo , db_session)

    try:
        user = await service.sign_up_user(user_in)
        return {"id" : user.id , "email" : user.email , "username" : user.username}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST , detail=str(e))


@router.post("/signin", response_model=dict)
async def sign_in(email : str , password : str , db_session : AsyncSession = Depends(get_session_dep)):
    repo = UserRepository(db_session)
    service = UserService(repo , db_session)

    try:
        user = await service.sign_in_user(email , password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED , detail=str(e))
    
    token = await service.issue_tokens(user)
    access = token["access"]
    refresh = token["refresh"]

    Response.set_cookie(key="refresh_token", value=refresh["token"], httponly=True, secure=False, samesite="lax", max_age=(refresh["exp"] - int(datetime.utcnow().timestamp())))
    return {"access_token": access["token"], "token_type": "bearer", "expires_in": access["exp"]}