from typing import Optional

from fastapi import HTTPException
from postgrest.exceptions import APIError

from db import supabase
from models import ProblemCreate, ProblemUpdate

from fastapi import APIRouter

router = APIRouter(prefix="/api/problems", tags=["题库"])


# 新增题目
@router.post("")
def create_problem(problem: ProblemCreate):
    data = problem.model_dump()
    res = supabase.table("problems").insert(data).execute()
    if not res.data:
        raise HTTPException(status_code=400, detail="创建题目失败")
    return {"ok": True, "data": res.data[0]}


# 获取题目列表，支持按数据集筛选
@router.get("")
def list_problems(dataset_name: Optional[str] = None, limit: int = 20, offset: int = 0):
    query = supabase.table("problems").select("*")
    if dataset_name:
        query = query.eq("dataset_name", dataset_name)
    res = query.range(offset, offset+limit-1).execute()
    return {"count": len(res.data), "data": res.data}


# 题库总数（head 计数，供统计卡片使用）
# 注意：必须定义在 /{problem_id} 之前，否则 "count" 会被路径参数吞掉
@router.get("/count")
def count_problems():
    try:
        res = supabase.table("problems").select("id", count="exact").execute()
    except APIError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"count": res.count or 0}


# 游标分页获取题目列表（keyset 分页：WHERE id > cursor ORDER BY id，避免深分页性能问题与数据漂移）
@router.get("/cursor")
def list_problems_by_cursor(
    cursor: Optional[int] = None,
    limit: int = 20,
    dataset_name: Optional[str] = None,
):
    limit = max(1, min(limit, 100))
    query = supabase.table("problems").select(
        "id, dataset_name, subset, title, difficulty, created_at"
    )
    if cursor is not None:
        query = query.gt("id", cursor)
    if dataset_name:
        query = query.eq("dataset_name", dataset_name)
    # 多取一条用于判断是否还有下一页
    res = query.order("id", desc=False).limit(limit + 1).execute()
    has_more = len(res.data) > limit
    items = res.data[:limit]
    return {
        "items": items,
        "has_more": has_more,
        "next_cursor": items[-1]["id"] if has_more else None,
    }


# 获取单个题目
@router.get("/{problem_id}")
def get_problem(problem_id: int):
    res = supabase.table("problems").select("*").eq("id", problem_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="题目不存在")
    return res.data[0]


# 更新题目（局部更新，只写入传入的字段）
@router.put("/{problem_id}")
def update_problem(problem_id: int, problem: ProblemUpdate):
    data = problem.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="没有可更新的字段")
    res = supabase.table("problems").update(data).eq("id", problem_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="题目不存在")
    return {"ok": True, "data": res.data[0]}


# 删除题目
@router.delete("/{problem_id}")
def delete_problem(problem_id: int):
    res = supabase.table("problems").delete().eq("id", problem_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="题目不存在")
    return {"ok": True, "msg": "已删除"}
