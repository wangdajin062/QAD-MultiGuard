"""
api/v1/auth.py - 认证路由 (v4.1 修复版)
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import secrets, hashlib, datetime, hmac as hmac_lib

from core.database import get_db
from core.redis import CacheService
from core.security import sha256, mask_phone, create_tokens, decode_token
from core.config import settings
from models.user import User
from schemas.schemas import SendCodeRequest, LoginRequest, TokenResponse

router = APIRouter()
logger = __import__("logging").getLogger(__name__)


@router.post("/send-code", summary="发送短信验证码 (需要速率限制)")
async def send_code(body: SendCodeRequest, request: Request):
    """
    发送 6 位验证码到用户手机
    
    速率限制: 5次/分钟 (由中间件保证)
    过期时间: 300 秒
    """
    # ✅ 验证手机号格式
    if not body.phone or len(body.phone) < 10:
        raise HTTPException(status_code=400, detail="无效的手机号")
    
    code = str(secrets.randbelow(900000) + 100000)
    phone_hash = sha256(body.phone)
    code_key = f"sms_code:{phone_hash}"
    
    # ✅ 存入 Redis，300秒过期
    try:
        await CacheService.setex(
            code_key, 
            settings.SMS_CODE_EXPIRE_SECONDS, 
            code
        )
    except Exception as e:
        logger.error(f"Redis setex failed: {e}")
        raise HTTPException(
            status_code=503, 
            detail="服务暂时不可用，请稍后重试"
        )
    
    logger.info(f"SMS code sent to {mask_phone(body.phone)}")
    # 实际环境：调用阿里云/腾讯云短信 API
    # await sms_service.send(body.phone, f"验证码: {code}，5分钟内有效")
    
    return {
        "code": 200, 
        "message": f"验证码已发送到 {mask_phone(body.phone)}，请注意查收"
    }


@router.post("/login", response_model=dict, summary="登录 / 注册 (验证码必填)")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    使用手机号 + 验证码登录
    
    返回:
      - access_token:  短期令牌（用于 API 请求）
      - refresh_token: 长期令牌（用于刷新 access_token）
    
    步骤:
    1. ✅ 校验验证码（必须）
    2. 查找或创建用户
    3. 颁发双令牌（access + refresh）
    """
    # ✅ 步骤 1: 校验验证码（防暴力破解）
    phone_hash = sha256(body.phone)
    code_key = f"sms_code:{phone_hash}"
    
    try:
        stored_code = await CacheService.get(code_key)
    except Exception as e:
        logger.error(f"Redis get failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="服务暂时不可用，请稍后重试"
        )
    
    if not stored_code:
        raise HTTPException(
            status_code=400,
            detail="验证码已过期或未发送，请重新获取"
        )
    
    # ✅ 使用 hmac.compare_digest 防时序攻击
    if not hmac_lib.compare_digest(stored_code, body.code):
        raise HTTPException(
            status_code=400,
            detail="验证码错误"
        )
    
    # ✅ 验证码一次性使用，立即删除
    try:
        await CacheService.delete(code_key)
    except Exception as e:
        logger.warning(f"Redis delete failed: {e}")
    
    # ✅ 步骤 2: 查找或创建用户
    try:
        result = await db.execute(select(User).where(User.phone_hash == phone_hash))
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                phone=mask_phone(body.phone), 
                phone_hash=phone_hash,
                nickname="校园守护者"
            )
            db.add(user)
            await db.flush()

        user.last_login_at = datetime.datetime.now(datetime.timezone.utc)
        await db.commit()
        logger.info(f"User login: {user.id}")
        
    except Exception as e:
        await db.rollback()
        logger.exception("Login process failed")
        raise HTTPException(
            status_code=500,
            detail="登录失败，请稍后重试"
        )
    
    # ✅ 步骤 3: 颁发双令牌（access + refresh）
    tokens = create_tokens(user.id, phone_hash)
    return {
        "code": 200,
        "data": {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type": tokens["token_type"],
            "expires_in": tokens["expires_in"],
            "user": {
                "id": user.id,
                "nickname": user.nickname,
                "protection_score": user.protection_score
            }
        }
    }


@router.post("/refresh", summary="刷新 access_token")
async def refresh(request: Request, db: AsyncSession = Depends(get_db)):
    """
    使用 refresh_token 获取新的 access_token
    
    请求体:
    {
        "refresh_token": "eyJhbGc..."
    }
    """
    try:
        body = await request.json()
        refresh_token = body.get("refresh_token")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request format")
    
    if not refresh_token:
        raise HTTPException(status_code=400, detail="refresh_token is required")
    
    # ✅ 解析 refresh_token
    try:
        payload = decode_token(refresh_token, token_type="refresh")
    except HTTPException:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh_token")
    
    uid = payload.get("uid")
    if not uid:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    # ✅ 验证用户存在
    result = await db.execute(select(User).where(User.id == uid, User.status == 1))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found or disabled")
    
    # ✅ 颁发新的 access_token（refresh_token 保持不变）
    tokens = create_tokens(user.id, user.phone_hash)
    
    return {
        "code": 200,
        "data": {
            "access_token": tokens["access_token"],
            "token_type": tokens["token_type"],
            "expires_in": tokens["expires_in"],
        }
    }


@router.post("/logout", summary="登出")
async def logout(request: Request):
    """
    可选：撤销 token（实现黑名单）
    当前简单实现（客户端删除 token）
    """
    return {
        "code": 200,
        "message": "已登出，请删除本地 token"
    }
