"""
core/security.py - JWT 鉴权 & 密码工具 (v4.1 刷新令牌版)
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.config import settings
from core.database import get_db
from models.user import User

bearer_scheme = HTTPBearer()


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def mask_phone(phone: str) -> str:
    """手机号脱敏：138****1234"""
    if len(phone) == 11:
        return phone[:3] + "****" + phone[7:]
    return phone[:3] + "***" + phone[-3:]


def create_tokens(uid: int, phone_hash: str) -> dict:
    """
    ✅ v4.1: 同时生成 access_token (短期) + refresh_token (长期)
    
    access_token:  用于 API 请求，1-7 天过期
    refresh_token: 用于刷新 access_token，7-30 天过期
    """
    now = datetime.now(timezone.utc)
    
    access_expire = now + timedelta(days=settings.JWT_EXPIRE_DAYS)
    access_token = jwt.encode(
        {
            "uid": uid,
            "phone_hash": phone_hash,
            "type": "access",
            "exp": access_expire,
            "iat": now,
        },
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    refresh_expire = now + timedelta(days=settings.JWT_REFRESH_EXPIRE_DAYS)
    refresh_token = jwt.encode(
        {
            "uid": uid,
            "type": "refresh",
            "exp": refresh_expire,
            "iat": now,
        },
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": int(settings.JWT_EXPIRE_DAYS * 86400),
    }


def create_access_token(uid: int, phone_hash: str) -> str:
    """向后兼容：仅返回 access_token"""
    tokens = create_tokens(uid, phone_hash)
    return tokens["access_token"]


def decode_token(token: str, token_type: str = "access") -> dict:
    """
    解析 JWT Token
    
    token_type: 'access' 或 'refresh'
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        # ✅ 验证 token 类型
        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type, expected {token_type}"
            )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token 无效或已过期"
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """从 access_token 获取当前用户"""
    payload = decode_token(credentials.credentials, token_type="access")
    uid = payload.get("uid")
    if not uid:
        raise HTTPException(status_code=401, detail="Token 解析失败")
    result = await db.execute(select(User).where(User.id == uid, User.status == 1))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在或已被禁用")
    return user

