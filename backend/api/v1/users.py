"""
api/v1/users.py - 用户信息路由
"""
import random
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.fraud import FraudPhone, FraudCase, UserDevice, FraudAlert
from schemas.schemas import UserStatsResponse, DeviceRegisterRequest, FraudAlertResponse

router = APIRouter()

DAILY_TIPS = [
    {"title": "验证码是最后一道锁", "content": "任何索要短信验证码的都是诈骗！银行、公安、客服都不会索要你的验证码。", "emoji": "🔐"},
    {"title": "安全账户不存在", "content": "公检法机关没有所谓的「安全账户」，凡是通过电话要求转账到「安全账户」的，一律是诈骗。", "emoji": "🏦"},
    {"title": "陌生链接不要点", "content": "收到含链接的短信，不管内容多紧急，先用官方渠道核实。钓鱼网站会伪装成真实网页。", "emoji": "🔗"},
    {"title": "刷单返利是陷阱", "content": "所有「足不出户、日赚千元」的兼职刷单都是诈骗。前期小额返利只是为了引诱你投入更多。", "emoji": "⚠️"},
    {"title": "网恋对象要警惕", "content": "杀猪盘诈骗流程：网上认识→培养感情→诱导投资/赌博→无法提现→拉黑消失。", "emoji": "💔"},
    {"title": "校园贷注销是骗局", "content": "声称帮你注销校园贷账户的客服电话都是诈骗。个人征信无法通过转账来修复。", "emoji": "🎓"},
    {"title": "真假班主任要分清", "content": "骗子混入班级群冒充老师收费。涉及转账务必通过电话或当面与老师确认。", "emoji": "🏫"},
    {"title": "机票退改签要官方", "content": "收到航班取消短信不要回拨短信里的电话。通过航空公司官网或官方App确认。", "emoji": "✈️"},
    {"title": "投资理财走正道", "content": "宣称「保本高收益」的投资平台都是诈骗。理财请选择银行或持牌金融机构。", "emoji": "📈"},
    {"title": "个人信息保护好", "content": "不要将身份证号、银行卡号、密码等敏感信息告诉他人或在不明网站上填写。", "emoji": "🛡️"},
    {"title": "快递理赔要核实", "content": "冒充电商客服以「商品质量问题」「快递丢失」为由主动理赔的，务必通过官方渠道核实。", "emoji": "📦"},
    {"title": "遇到诈骗及时报警", "content": "如果不慎被骗，第一时间拨打110报警并联系银行冻结账户，保留转账记录和聊天截图。", "emoji": "🚨"},
]


@router.get("/stats", summary="用户防护统计")
async def user_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    score = current_user.protection_score
    level = (
        "防骗专家 🏆" if score >= 80
        else "优秀守卫者 ⭐⭐⭐" if score >= 50
        else "安全学员 ⭐⭐" if score >= 20
        else "新手防护 ⭐"
    )
    return {
        "code": 200,
        "data": UserStatsResponse(
            blocked_calls=current_user.blocked_calls,
            alerted_sms=current_user.alerted_sms,
            total_reports=current_user.total_reports,
            cases_read=current_user.cases_read,
            protection_score=score,
            protection_level=level,
        ).model_dump()
    }


@router.post("/device", summary="注册设备（用于推送通知）")
async def register_device(
    body: DeviceRegisterRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(UserDevice).where(UserDevice.user_id == current_user.id, UserDevice.device_id == body.device_id)
    )
    device = result.scalar_one_or_none()
    if device:
        device.fcm_token = body.fcm_token
        device.app_version = body.app_version
        device.is_active = True
    else:
        db.add(UserDevice(
            user_id=current_user.id,
            device_id=body.device_id,
            platform=body.platform,
            fcm_token=body.fcm_token,
            app_version=body.app_version,
            os_version=body.os_version,
        ))
    return {"code": 200, "data": {"message": "设备注册成功"}}


@router.get("/home", summary="首页聚合数据")
async def home_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    phone_count = (await db.execute(
        select(func.count()).select_from(FraudPhone).where(FraudPhone.is_active == True)
    )).scalar()
    case_count = (await db.execute(
        select(func.count()).select_from(FraudCase).where(FraudCase.status == "published")
    )).scalar()

    # 用户防护统计
    score = current_user.protection_score
    level = (
        "防骗专家 🏆" if score >= 80
        else "优秀守卫者 ⭐⭐⭐" if score >= 50
        else "安全学员 ⭐⭐" if score >= 20
        else "新手防护 ⭐"
    )
    stats = {
        "protection_score": score,
        "blocked_calls": current_user.blocked_calls,
        "alerted_sms": current_user.alerted_sms,
        "total_reports": current_user.total_reports,
        "cases_read": current_user.cases_read,
        "protection_level": level,
    }

    # 最新预警（最近3条）
    alerts_result = await db.execute(
        select(FraudAlert).where(FraudAlert.status == "published")
            .order_by(FraudAlert.published_at.desc()).limit(3)
    )
    latest_alerts = [
        FraudAlertResponse.model_validate(a).model_dump()
        for a in alerts_result.scalars().all()
    ]

    # 今日提示（随机）
    today_tip = random.choice(DAILY_TIPS)

    return {"code": 200, "data": {
        "blocked_today":      current_user.blocked_calls,
        "alerted_sms":        current_user.alerted_sms,
        "total_protected":    current_user.blocked_calls,
        "fraud_phone_count":  phone_count,
        "case_count":         case_count,
        "stats":              stats,
        "latest_alerts":      latest_alerts,
        "today_tip":          today_tip,
    }}
