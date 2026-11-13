from typing import Optional

from fastapi import APIRouter, Body, HTTPException
from postgrest.exceptions import APIError

from db import supabase

router = APIRouter(prefix="/api/submissions", tags=["提交记录"])

# 提交记录独立 API：account_id 逻辑关联 accounts.id（不建物理外键）；
# id / created_at 由数据库维护，不接受写入

# 沙箱评测结果状态：AC(通过) / WA(答案错误) / CE(编译错误) / RE(运行错误) / TLE(超时)
STATUS_VALUES = {"AC", "WA", "CE", "RE", "TLE"}
# 必填字段：与表结构 NOT NULL 约束一致
REQUIRED_FIELDS = ["problem_id", "account_id", "status"]


def sanitize_submission(body: Optional[dict]) -> tuple[Optional[dict], Optional[str]]:
    """校验并转换请求体，只保留白名单列；返回 (行数据, 错误信息)。"""
    if not isinstance(body, dict):
        return None, "请求数据不合法"
    row: dict = {}

    if "problem_id" in body:
        try:
            problem_id = int(body["problem_id"])
        except (TypeError, ValueError):
            return None, "problem_id 必须是正整数"
        # 前端 Number() 语义：小数会被判非法
        if problem_id <= 0 or (isinstance(body["problem_id"], float) and body["problem_id"] != problem_id):
            return None, "problem_id 必须是正整数"
        row["problem_id"] = problem_id

    if "account_id" in body:
        # accounts.id 是 UUID 字符串，与 problem_id（自增整数）不同，只做非空校验
        account_id = str(body["account_id"]).strip()
        if not account_id:
            return None, "account_id 不能为空"
        row["account_id"] = account_id

    if "status" in body:
        status = str(body["status"]).upper()
        if status not in STATUS_VALUES:
            return None, "状态必须为 AC / WA / CE / RE / TLE"
        row["status"] = status

    if "pass" in body:
        # 浏览器端测试集跑完后的总体通过结果（布尔）
        if not isinstance(body["pass"], bool):
            return None, "pass 必须是布尔值"
        row["pass"] = body["pass"]

    if "error_reason" in body:
        # 未通过时的失败原因：编译错误或首个失败用例的报错
        row["error_reason"] = str(body["error_reason"])

    if "agent_report" in body:
        row["agent_report"] = str(body["agent_report"])

    return row, None


@router.get("")
def list_submissions():
    try:
        res = supabase.table("submissions").select("*").order("created_at", desc=False).execute()
    except APIError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return res.data


@router.post("")
def create_submission(payload: dict = Body(...)):
    row, error = sanitize_submission(payload)
    if error or row is None:
        raise HTTPException(status_code=400, detail=error or "请求数据不合法")
    missing = [f for f in REQUIRED_FIELDS if f not in row]
    if missing:
        raise HTTPException(status_code=400, detail=f"缺少必填字段：{'、'.join(missing)}")
    try:
        res = supabase.table("submissions").insert(row).execute()
    except APIError as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not res.data:
        raise HTTPException(status_code=500, detail="创建失败")
    return res.data[0]


@router.patch("")
def update_submission(payload: dict = Body(...), id: Optional[str] = None):
    if not id:
        raise HTTPException(status_code=400, detail="缺少 id")
    row, error = sanitize_submission(payload)
    if error or row is None:
        raise HTTPException(status_code=400, detail=error or "请求数据不合法")
    if not row:
        raise HTTPException(status_code=400, detail="没有可更新的字段")
    try:
        res = supabase.table("submissions").update(row).eq("id", id).execute()
    except APIError as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not res.data:
        raise HTTPException(status_code=404, detail="记录不存在")
    return res.data[0]


@router.delete("")
def delete_submission(id: Optional[str] = None):
    if not id:
        raise HTTPException(status_code=400, detail="缺少 id")
    try:
        supabase.table("submissions").delete().eq("id", id).execute()
    except APIError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"ok": True}
