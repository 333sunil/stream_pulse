from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from typing import Annotated

from app.core.ldap import authenticate_user_simple

security = HTTPBasic()

def get_current_user_ldap(
    credentials: Annotated[HTTPBasicCredentials, Depends(security)]
):
    # Use the pooled method we discussed
    user = authenticate_user_simple(
        credentials.username, 
        credentials.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid LDAP credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return user
