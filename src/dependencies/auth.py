from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordBearer
from infrastructure.database import get_session
from UAA.utils import decode_token
from UAA.repository import UserRepository
from fastapi import HTTPException , status
from jose import jwt




oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(token : str = Depends(oauth2_scheme) , 
                           session: AsyncSession = Depends(get_session)):
    
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        repo = UserRepository(session)
        user = await repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.401_UNAUTHORIZED 
                                , detail="Invalid user credentials.")
        return user

    except jwt.JWTError:
        raise HTTPException(status_code=status.401_UNAUTHORIZED 
                            , detail="Could not validate token credentials.")