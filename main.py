from fastapi import FastAPI
from dotenv import load_dotenv

from routers import auth, crud, problems, submissions, users

load_dotenv()
app = FastAPI(title="CodeBenchAgent", version="0.1.0")

# 路由注册顺序说明：problems 内部 /count 定义在 /{problem_id} 之前，
# 其余 router 前缀互不冲突，注册顺序不影响匹配
app.include_router(problems.router)
app.include_router(submissions.router)
app.include_router(crud.router)
app.include_router(auth.router)
app.include_router(users.router)


# ========== 基础接口 ==========
# ping测试接口
@app.get("/ping")
def ping():
    return {"msg": "pong", "status": "ok"}


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service_name": "CodeBenchAgent",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
