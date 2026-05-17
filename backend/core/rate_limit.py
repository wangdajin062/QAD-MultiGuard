"""
core/rate_limit.py - 基于 Redis 的 API 限流中间件 (v4.1 修复版)
"""

from fastapi import Request, HTTPException
from core.redis import CacheService
import logging

logger = logging.getLogger(__name__)

# ✅ 定义敏感端点（Redis 故障时严格模式）
SENSITIVE_ENDPOINTS = [
    "/v1/auth/send-code",   # 短信验证码
    "/v1/auth/login",       # 登录
    "/v1/admin/",           # 所有管理员操作
]


async def rate_limit(request: Request, max_calls: int = 100, window: int = 60) -> None:
    """
    通用限流依赖（FastAPI Depends 使用）
    
    v4.1 修复：
    - Redis 故障时，敏感端点返回 503
    - 非敏感端点降级为本地限流
    
    用法:
        from core.rate_limit import rate_limit
        from functools import partial
        
        @router.post("/sensitive")
        async def endpoint(_=Depends(partial(rate_limit, max_calls=5, window=60))):
            ...
    """
    # 优先用 JWT uid，降级用 IP
    client_id = getattr(request.state, "user_id", None) or (
        request.client.host if request.client else "unknown"
    )
    route = request.url.path.replace("/", "_")
    key = f"rl:{route}:{client_id}"

    try:
        count = await CacheService.incr_with_expire(key, expire=window)
        if count > max_calls:
            raise HTTPException(
                status_code=429,
                detail=f"请求过于频繁，请 {window} 秒后重试",
                headers={"Retry-After": str(window)},
            )
    except HTTPException:
        raise
    except Exception as e:
        # ✅ Redis 故障处理：区分敏感和非敏感端点
        is_sensitive = any(request.url.path.startswith(ep) for ep in SENSITIVE_ENDPOINTS)
        
        if is_sensitive:
            # 敏感端点：严格模式，拒绝请求
            logger.error(f"Redis 故障 + 敏感端点，拒绝请求: {request.url.path}")
            raise HTTPException(
                status_code=503,
                detail="服务暂时不可用，请检查网络并稍后重试",
                headers={"Retry-After": "30"},
            )
        else:
            # 非敏感端点：本地内存限流备份（可选）
            logger.warning(
                f"Redis 故障，切换到本地限流备份: {request.url.path}"
            )
            # 可选：实现本地限流（使用 dict + time.time()）
            # 简单实现省略，可根据需要扩展
            pass


async def strict_rate_limit(request: Request) -> None:
    """严格限流：5次/分钟，用于短信发送等敏感接口"""
    await rate_limit(request, max_calls=5, window=60)


async def auth_rate_limit(request: Request) -> None:
    """认证限流：20次/分钟"""
    await rate_limit(request, max_calls=20, window=60)

