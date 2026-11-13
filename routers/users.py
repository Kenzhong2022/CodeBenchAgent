import re
from typing import Optional

from fastapi import APIRouter, HTTPException
from postgrest.exceptions import APIError
from pydantic import BaseModel

from db import supabase
from security import hash_password

router = APIRouter(prefix="/api/users", tags=["用户管理"])

# 列表返回列：不暴露 password_hash 等敏感列
SELECT_COLUMNS = "id,name,email,avatar,last_login_at,created_at"

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class UserCreate(BaseModel):
    name: str
    email: str
    # 管理员创建用户时设置初始密码
    password: str
    avatar: Optional[str] = None


class UserUpdate(BaseModel):
    # 全部可选，配合 exclude_unset 做局部更新；password 提供时重置密码
    name: Optional[str] = None
    email: Optional[str] = None
    avatar: Optional[str] = None
    password: Optional[str] = None


def _ensure_email(email: str) -> None:
    if not EMAIL_RE.fullmatch(email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")


def _raise_unique_conflict(e: APIError) -> None:
    """邮箱唯一约束冲突（23505）转 409，其余异常按 500 抛出。"""
    if e.code == "23505":
        raise HTTPException(status_code=409, detail="该邮箱已被占用")
    raise HTTPException(status_code=500, detail=str(e))


@router.get("")
def list_users(
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
):
    """分页获取用户列表：keyword 模糊匹配姓名 / 邮箱，按创建时间倒序。"""
    page = max(1, page)
    page_size = max(1, min(page_size, 100))

    query = supabase.table("accounts").select(SELECT_COLUMNS)
    # 精确计数走 head 请求，不拉数据
    count_query = supabase.table("accounts").select(
        "id", count="exact", head=True
    )
    if keyword:
        pattern = f"%{keyword}%"
        condition = f"name.ilike.{pattern},email.ilike.{pattern}"
        query = query.or_(condition)
        count_query = count_query.or_(condition)

    try:
        total = count_query.execute().count or 0
        res = (
            query.order("created_at", desc=True)
            .range((page - 1) * page_size, page * page_size - 1)
            .execute()
        )
    except APIError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"items": res.data, "total": total, "page": page, "page_size": page_size}


@router.post("")
def create_user(payload: UserCreate):
    """管理员创建用户：写入 name / email / avatar，密码以兼容散列存储。"""
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="用户名不能为空")
    _ensure_email(payload.email)
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="密码长度至少 6 位")

    row = {
        "name": name,
        "email": payload.email,
        "avatar": payload.avatar,
        "password_hash": hash_password(payload.password),
    }
    try:
        res = (
            supabase.table("accounts")
            .insert(row)
            .select(SELECT_COLUMNS)
            .execute()
        )
    except APIError as e:
        _raise_unique_conflict(e)
    if not res.data:
        raise HTTPException(status_code=500, detail="创建用户失败")
    return res.data[0]


@router.patch("/{user_id}")
def update_user(user_id: str, payload: UserUpdate):
    """局部更新用户；password 提供且非空时重置为对应散列。"""
    data = payload.model_dump(exclude_unset=True)
    if "email" in data:
        _ensure_email(data["email"])
    if "name" in data and not str(data["name"]).strip():
        raise HTTPException(status_code=400, detail="用户名不能为空")
    if data.get("password"):
        if len(data["password"]) < 6:
            raise HTTPException(status_code=400, detail="密码长度至少 6 位")
        data["password_hash"] = hash_password(data.pop("password"))
    else:
        data.pop("password", None)
    if not data:
        raise HTTPException(status_code=400, detail="没有可更新的字段")

    try:
        res = (
            supabase.table("accounts")
            .update(data)
            .eq("id", user_id)
            .select(SELECT_COLUMNS)
            .execute()
        )
    except APIError as e:
        _raise_unique_conflict(e)
    if not res.data:
        raise HTTPException(status_code=404, detail="用户不存在")
    return res.data[0]


@router.delete("/{user_id}")
def delete_user(user_id: str):
    try:
        supabase.table("accounts").delete().eq("id", user_id).execute()
    except APIError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"ok": True}
