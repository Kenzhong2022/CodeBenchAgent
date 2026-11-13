from typing import Optional

from fastapi import APIRouter, Body, HTTPException
from postgrest.exceptions import APIError

from db import supabase

router = APIRouter(prefix="/api/crud", tags=["通用CRUD"])

# 允许访问的表及其列；题库（problems）与提交记录（submissions）有独立路由
CRUD_TABLES = {
    "roles": ["id", "name", "description"],
    # accounts：用户账号表；只暴露展示字段，密码等敏感列不进白名单
    "accounts": ["id", "name", "email", "avatar"],
    "products": ["id", "name", "price", "stock"],
}
# 数值列：其余列统一按字符串处理
CRUD_NUMBER_COLUMNS = {"price", "stock"}


def sanitize_crud(table: str, body: Optional[dict]) -> Optional[dict]:
    """只保留白名单列并按列类型转换，非法输入返回 None。"""
    if not isinstance(body, dict):
        return None
    row: dict = {}
    for column in CRUD_TABLES[table]:
        value = body.get(column)
        if value is None:
            continue
        if column in CRUD_NUMBER_COLUMNS:
            try:
                num = float(value)
            except (TypeError, ValueError):
                return None
            # 布尔值（bool 是 int 子类）与非有限数一律拒绝
            if isinstance(value, bool) or num != num or num in (float("inf"), float("-inf")):
                return None
            # 整数值转 int：Postgres integer 列不接受 "3.0" 这类小数形式
            row[column] = int(num) if num.is_integer() else num
        else:
            row[column] = str(value)
    return row


@router.get("/{table}")
def crud_list(table: str):
    if table not in CRUD_TABLES:
        raise HTTPException(status_code=404, detail="未知数据表")
    try:
        res = supabase.table(table).select("*").order("created_at", desc=False).execute()
    except APIError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return res.data


@router.post("/{table}")
def crud_create(table: str, payload: dict = Body(...)):
    if table not in CRUD_TABLES:
        raise HTTPException(status_code=404, detail="未知数据表")
    row = sanitize_crud(table, payload)
    if row is None:
        raise HTTPException(status_code=400, detail="请求数据不合法")
    try:
        res = supabase.table(table).insert(row).execute()
    except APIError as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not res.data:
        raise HTTPException(status_code=500, detail="创建失败")
    return res.data[0]


@router.patch("/{table}")
def crud_update(table: str, payload: dict = Body(...)):
    if table not in CRUD_TABLES:
        raise HTTPException(status_code=404, detail="未知数据表")
    row = sanitize_crud(table, payload)
    row_id = payload.get("id") if isinstance(payload, dict) else None
    if row is None or not isinstance(row_id, str):
        raise HTTPException(status_code=400, detail="请求数据不合法")
    try:
        res = supabase.table(table).update(row).eq("id", row_id).execute()
    except APIError as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not res.data:
        raise HTTPException(status_code=404, detail="记录不存在")
    return res.data[0]


@router.delete("/{table}")
def crud_delete(table: str, id: Optional[str] = None):
    if table not in CRUD_TABLES:
        raise HTTPException(status_code=404, detail="未知数据表")
    if not id:
        raise HTTPException(status_code=400, detail="缺少 id")
    try:
        supabase.table(table).delete().eq("id", id).execute()
    except APIError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"ok": True}
