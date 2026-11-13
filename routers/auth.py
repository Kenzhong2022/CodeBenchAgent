from datetime import datetime, timezone
import re

from fastapi import APIRouter, Body, HTTPException
from postgrest.exceptions import APIError

from db import supabase
from security import generate_verification_code, hash_password, verify_password
import redis_client as redis
import mailer

router = APIRouter(prefix="/api/auth", tags=["认证"])

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
CODE_RE = re.compile(r"^\d{6}$")

CODE_TTL_SECONDS = 300  # 验证码有效期 5 分钟
RESEND_COOLDOWN_SECONDS = 60  # 重发冷却，防止邮件轰炸


def _utc_now_iso() -> str:
    """与 JS new Date().toISOString() 一致的 UTC ISO 字符串。"""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@router.post("/send-code")
def send_code(payload: dict = Body(...)):
    email = payload.get("email")
    if not isinstance(email, str) or not EMAIL_RE.fullmatch(email):
        raise HTTPException(status_code=400, detail="请输入合法的邮箱地址")

    # 已注册的邮箱不再发码，引导直接登录
    # 注意：此版本 supabase-py 无匹配行时 maybe_single().execute() 返回 None
    existing_res = (
        supabase.table("accounts").select("id").eq("email", email).maybe_single().execute()
    )
    if existing_res and existing_res.data:
        raise HTTPException(status_code=409, detail="该邮箱已注册，请直接登录")

    # 重发冷却：SET NX EX 仅在无冷却键时成功
    cooldown = redis.redis_set(f"cooldown:{email}", "1", ex=RESEND_COOLDOWN_SECONDS, nx=True)
    if cooldown is None:
        raise HTTPException(
            status_code=429, detail=f"发送过于频繁，请 {RESEND_COOLDOWN_SECONDS} 秒后再试"
        )

    code = generate_verification_code()
    redis.redis_set(email, code, ex=CODE_TTL_SECONDS)

    html = f"""
        <div style="max-width:480px;margin:0 auto;font-family:Arial,sans-serif">
          <h2 style="color:#171717">CodeBench 注册验证码</h2>
          <p>您的验证码为（{CODE_TTL_SECONDS // 60} 分钟内有效）：</p>
          <p style="font-size:32px;font-weight:bold;letter-spacing:8px;color:#1677ff">{code}</p>
          <p style="color:#999;font-size:12px">如果这不是您本人的操作，请忽略本邮件。</p>
        </div>
    """
    try:
        mailer.send_html_mail(email, "CodeBench 注册验证码", html)
    except Exception as err:
        # 发送失败立即作废验证码，避免用户反复重试时命中冷却却收不到邮件
        redis.redis_del(email, f"cooldown:{email}")
        raise HTTPException(status_code=502, detail=f"验证码邮件发送失败: {err}")

    return {"ok": True, "ttl": CODE_TTL_SECONDS}


@router.post("/register")
def register(payload: dict = Body(...)):
    name = payload.get("name")
    email = payload.get("email")
    code = payload.get("code")
    password = payload.get("password")

    name = str(name).strip() if name is not None else ""
    if not name:
        raise HTTPException(status_code=400, detail="请输入用户名")
    if not isinstance(email, str) or not EMAIL_RE.fullmatch(email):
        raise HTTPException(status_code=400, detail="请输入合法的邮箱地址")
    if not isinstance(code, str) or not CODE_RE.fullmatch(code):
        raise HTTPException(status_code=400, detail="验证码应为 6 位数字")
    if not password or len(password) < 6:
        raise HTTPException(status_code=400, detail="密码长度至少 6 位")

    stored = redis.redis_get(email)
    if stored is None:
        raise HTTPException(status_code=400, detail="验证码已过期或未发送，请重新获取")

    # 注意：Upstash 可能把纯数字字符串反序列化成 int，比较前统一转字符串
    if str(stored) != code:
        # 不匹配不消费，用户可用同一验证码重试
        raise HTTPException(status_code=400, detail="验证码不匹配")

    # 匹配成功才消费（删除）
    deleted = redis.redis_del(email)
    if deleted != 1:
        raise HTTPException(status_code=400, detail="验证码消费失败，请重新获取")

    existing_res = (
        supabase.table("accounts").select("id").eq("email", email).maybe_single().execute()
    )
    if existing_res and existing_res.data:
        raise HTTPException(status_code=409, detail="该邮箱已注册，请直接登录")

    try:
        res = (
            supabase.table("accounts")
            .insert({"email": email, "name": name, "password_hash": hash_password(password)})
            .select("id, email, name, created_at")
            .execute()
        )
    except APIError as e:
        # 唯一约束冲突（并发注册）等
        if e.code == "23505":
            raise HTTPException(status_code=409, detail="该邮箱已注册，请直接登录")
        raise HTTPException(status_code=500, detail=f"注册失败: {e.message}")

    if not res.data:
        raise HTTPException(status_code=500, detail="注册失败")
    return {"ok": True, "user": res.data[0]}


@router.post("/login")
def login(payload: dict = Body(...)):
    email = payload.get("email")
    password = payload.get("password")

    if not isinstance(email, str) or not EMAIL_RE.fullmatch(email):
        raise HTTPException(status_code=400, detail="请输入合法的邮箱地址")
    if not password:
        raise HTTPException(status_code=400, detail="请输入密码")

    try:
        res = (
            supabase.table("accounts")
            .select("id, email, name, password_hash")
            .eq("email", email)
            .maybe_single()
            .execute()
        )
    except APIError as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {e.message}")

    account = res.data if res else None
    # 用户不存在与密码错误统一提示，避免邮箱枚举
    if not account or not verify_password(password, account["password_hash"]):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")

    supabase.table("accounts").update({"last_login_at": _utc_now_iso()}).eq(
        "id", account["id"]
    ).execute()

    return {
        "ok": True,
        "user": {"id": account["id"], "email": account["email"], "name": account["name"]},
    }
