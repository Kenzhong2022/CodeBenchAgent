from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from db import supabase
from models import ProblemCreate, ProblemUpdate
from typing import List, Optional

load_dotenv()
app = FastAPI(title="CodeBenchAgent", version="0.1.0")

# ping测试接口
@app.get("/ping")
def ping():
    return {"msg": "pong", "status": "ok"}

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service_name": "CodeBenchAgent"
    }

# ========== 题库CRUD接口 ==========
# 新增题目
@app.post("/api/problems")
def create_problem(problem: ProblemCreate):
    data = problem.model_dump()
    res = supabase.table("problems").insert(data).execute()
    if not res.data:
        raise HTTPException(status_code=400, detail="创建题目失败")
    return {"ok": True, "data": res.data[0]}

# 获取题目列表，支持按数据集筛选
@app.get("/api/problems")
def list_problems(dataset_name: Optional[str] = None, limit: int = 20, offset: int = 0):
    query = supabase.table("problems").select("*")
    if dataset_name:
        query = query.eq("dataset_name", dataset_name)
    res = query.range(offset, offset+limit-1).execute()
    return {"count": len(res.data), "data": res.data}

# 游标分页获取题目列表（keyset 分页：WHERE id > cursor ORDER BY id，避免深分页性能问题与数据漂移）
@app.get("/api/problems/cursor")
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
@app.get("/api/problems/{problem_id}")
def get_problem(problem_id: int):
    res = supabase.table("problems").select("*").eq("id", problem_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="题目不存在")
    return res.data[0]

# 更新题目（局部更新，只写入传入的字段）
@app.put("/api/problems/{problem_id}")
def update_problem(problem_id: int, problem: ProblemUpdate):
    data = problem.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="没有可更新的字段")
    res = supabase.table("problems").update(data).eq("id", problem_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="题目不存在")
    return {"ok": True, "data": res.data[0]}

# 删除题目
@app.delete("/api/problems/{problem_id}")
def delete_problem(problem_id: int):
    res = supabase.table("problems").delete().eq("id", problem_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="题目不存在")
    return {"ok": True, "msg": "已删除"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
