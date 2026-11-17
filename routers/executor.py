"""Python 代码沙箱执行（基于 OnlineCompiler.io 云端 API）。

执行层完全托管，不依赖本地 Docker；安全隔离由 OnlineCompiler.io
的 gVisor 沙箱保障：每次执行均为全新沙箱、无网络访问、独立资源限额。

需要在 .env 中配置：
  ONLINECOMPILER_API_KEY=<密钥>
可选：
  ONLINECOMPILER_COMPILER=<编译器 ID，默认 python-3.14>

两种工作模式（由请求体是否携带 test_cases 决定）：
- 纯运行模式：直接执行 code，console = 用户代码的全部 stdout
- 评测模式：用 harness 脚本包裹，先执行用户代码、再逐条 exec 测试断言；
  此时用户代码的 stdout/stderr 会被重定向捕获进 console 字段，
  沙箱原始 stdout 只包含 harness 输出的一行 JSON 评测报告。

注意（常见疑问「为什么 console 没有输出」）：
- console 只包含代码**实际执行到**的 print 输出；
- 若用户代码只定义了函数、print 写在函数体内，而测试用例在调用函数时
  就已抛错（如参数不匹配的 TypeError），print 永远不会执行，console 为空；
- 用例判定结果请看 results（逐用例 passed/error），代码级错误看 compile_error。

响应字段说明：
  stdout        控制台输出（评测模式下 = harness 捕获的用户输出）
  stderr        沙箱侧错误输出
  output        stdout + stderr 合流
  exit_code     沙箱进程退出码
  timed_out     是否超过 time_limit 被判定超时
  truncated     输出是否被截断（超 MAX_OUTPUT_LENGTH）
  duration_ms   沙箱执行耗时（毫秒）
  results       逐用例结果 [{passed, error}]（仅评测模式非空）
  console       与 stdout 相同（保留字段名以兼容前端契约）
  compile_error 用户代码 / 用例的代码级错误（如语法错误、harness 异常），无错为 null
"""

import base64
import json
import os
from typing import Optional

from fastapi import APIRouter, Body, HTTPException
from onlinecompiler import OnlineCompiler
from pydantic import BaseModel

router = APIRouter(prefix="/api/execute", tags=["代码执行"])

COMPILER_ID = os.getenv("ONLINECOMPILER_COMPILER", "python-3.14")
# 允许的编译器白名单：Playground 多语言运行与评测共用同一接口，
# 只放行确认存在的编译器 ID，防止任意字符串透传给上游 API。
# 注意：评测模式（test_cases）依赖 Python harness，仅 Python 系编译器支持
ALLOWED_COMPILER_IDS = {
    "python-3.14",
    "python-3.14-pandas2",
    "gcc-15",             # C
    "g++-15",             # C++17
    "g++-15-cpp20",       # C++20
    "openjdk-25",         # Java
    "nodejs-24",          # JavaScript
    "typescript-deno",    # TypeScript
    "go-1.26",
    "rust-1.93",
    "dotnet-csharp-10",
}
MAX_CODE_LENGTH = 64 * 1024      # 代码最大 64KB
MAX_OUTPUT_LENGTH = 64 * 1024    # 输出最大 64KB
DEFAULT_TIME_LIMIT = 10          # 秒

_client: Optional[OnlineCompiler] = None


def _get_client() -> OnlineCompiler:
    """惰性初始化 OnlineCompiler 客户端。"""
    global _client
    if _client is None:
        api_key = os.getenv("ONLINECOMPILER_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=503,
                detail="ONLINECOMPILER_API_KEY 未配置，请确认 .env 已设置且服务由项目根目录启动",
            )
        _client = OnlineCompiler(api_key=api_key)
    return _client


def _truncate(text: str) -> tuple[str, bool]:
    if len(text) > MAX_OUTPUT_LENGTH:
        return text[:MAX_OUTPUT_LENGTH], True
    return text, False


class ExecuteRequest(BaseModel):
    code: str
    stdin: str = ""
    compiler_id: str = ""           # 编译器 ID（留空用默认 Python）；须在白名单内
    test_cases: list[str] = []      # 测试用例断言列表（非空时启用评测模式，仅 Python）
    test_imports: list[str] = []    # 用例依赖的导入语句（仅评测模式生效）


def _build_harness(code: str, cases: list[str], imports: list[str]) -> str:
    """构造逐用例执行脚本（评测模式核心）。

    执行顺序：
      1. 逐条 exec 测试依赖导入（test_imports）
      2. exec 用户代码 —— 若此处抛错（如语法错误），整轮判定记入 compile_error，
         不再继续执行任何用例
      3. 依次 exec 每条测试断言 —— 单条失败只记入该用例的 error，不影响后续用例

    输出捕获语义：
      用户代码与用例的 stdout/stderr 全部被 contextlib 重定向进 _console，
      即 console = 「代码实际执行到的 print 内容」；函数体内未被执行的 print
      不会出现在 console 里。沙箱真实 stdout 只有最后一行 JSON 报告。

    注入方式：用户代码 / 用例 / 导入经 base64(JSON) 编码后内嵌进脚本源码，
    避免引号与反斜杠转义问题（用例里常见嵌套字符串如 assert f("a") == "a"）。
    """
    payload = json.dumps(
        {"code": code, "cases": cases, "imports": imports},
        ensure_ascii=False,
    )
    encoded = base64.b64encode(payload.encode("utf-8")).decode("ascii")
    return f'''
import base64, io, json, contextlib, traceback

_payload = json.loads(base64.b64decode("{encoded}"))
_results = []
_console = io.StringIO()
_compile_error = None
_g = {{}}
with contextlib.redirect_stdout(_console), contextlib.redirect_stderr(_console):
    try:
        for _imp in _payload["imports"]:
            exec(_imp, _g)
        exec(_payload["code"], _g)
        for _case in _payload["cases"]:
            try:
                exec(_case, _g)
                _results.append({{"passed": True, "error": None}})
            except Exception as _exc:
                _results.append({{
                    "passed": False,
                    "error": "".join(traceback.format_exception_only(type(_exc), _exc)).strip(),
                }})
    except Exception as _exc:
        _compile_error = "".join(
            traceback.format_exception(type(_exc), _exc, _exc.__traceback__)
        ).strip()

print(json.dumps({{"results": _results, "console": _console.getvalue(), "compile_error": _compile_error}}))
'''


@router.post("")
def execute_code(payload: ExecuteRequest):
    """运行前端提交的 Python 代码。

    请求体：
      {"code": "print('Hello')", "stdin": "可选的标准输入",
       "test_cases": ["assert ..."], "test_imports": ["import ..."]}

    test_cases 非空时启用评测模式（练习页「运行 / 提交评测」均走此模式）：
    沙箱内用 harness 逐用例执行断言，返回 results / console / compile_error；
    纯运行模式（无 test_cases）只执行代码，console 即用户代码的全部 stdout。

    返回字段含义见模块 docstring。
    """
    code = payload.code
    stdin_data = payload.stdin

    # 输入校验：空代码与超长代码直接拒绝，不消耗沙箱调用额度
    if not code.strip():
        raise HTTPException(status_code=400, detail="code 必须是非空字符串")
    if len(code) > MAX_CODE_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"代码长度超过 {MAX_CODE_LENGTH // 1024}KB 上限",
        )

    # 编译器白名单校验：留空走默认 Python；白名单外的 ID 一律拒绝
    compiler_id = payload.compiler_id.strip() or COMPILER_ID
    if compiler_id not in ALLOWED_COMPILER_IDS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的编译器：{compiler_id}，可选：{'、'.join(sorted(ALLOWED_COMPILER_IDS))}",
        )

    # 评测模式的 harness 是 Python 脚本，其它语言只支持纯运行
    if payload.test_cases and not compiler_id.startswith("python"):
        raise HTTPException(
            status_code=400,
            detail="评测模式（test_cases）仅支持 Python，其它语言请使用纯运行模式",
        )

    client = _get_client()

    # 评测模式：用 harness 包裹用户代码，沙箱内逐用例执行并输出 JSON 报告；
    # 纯运行模式：原样执行用户代码
    test_mode = bool(payload.test_cases)
    run_code = _build_harness(code, payload.test_cases, payload.test_imports) if test_mode else code

    try:
        result = client.run(
            compiler_id,
            run_code,
            input=stdin_data,
            time_limit=DEFAULT_TIME_LIMIT,
        )
    except Exception as e:
        # 网络/认证/限流等客户端侧错误
        raise HTTPException(status_code=502, detail=f"OnlineCompiler.io 调用失败: {e}")

    # OnlineCompiler.io 返回字段映射：
    # output = 沙箱进程的 stdout，error = 沙箱侧 stderr
    stdout_raw = result.get("output", "")
    stderr_raw = result.get("error", "")
    exit_code = result.get("exit_code", -1)
    time_sec = result.get("time", "0")

    # 超时判定：OnlineCompiler 只返回耗时，用「耗时 >= time_limit」近似判定。
    # 必须在解析评测报告之前完成——超时的执行拿不到报告，需要走独立的提示分支
    timed_out = False
    try:
        if float(time_sec) >= DEFAULT_TIME_LIMIT:
            timed_out = True
    except (ValueError, TypeError):
        pass

    # 评测模式：harness 的 stdout 是一行 JSON 报告，解析出逐用例结果；
    # console 改取报告里的用户输出（而非沙箱原始 stdout，后者只含 JSON）
    results: list[dict] = []
    console = stdout_raw
    compile_error: Optional[str] = None
    if test_mode:
        if timed_out:
            # 执行被强杀，harness 没机会输出 JSON：明确告知超时而非笼统报异常
            results = []
            console = stdout_raw
            compile_error = (
                f"执行超时（超过 {DEFAULT_TIME_LIMIT} 秒已终止），"
                "请检查是否存在死循环、等待输入或其他长时间运行的操作"
            )
        else:
            try:
                report = json.loads(stdout_raw.strip())
                results = report.get("results", [])
                console = report.get("console", "")
                compile_error = report.get("compile_error")
            except json.JSONDecodeError:
                # 非超时的 harness 异常：附上 stderr 摘要帮助定位
                results = []
                console = ""
                excerpt = stderr_raw.strip()[:500]
                compile_error = excerpt or "沙箱执行异常，未返回评测报告"

    stdout, truncated_out = _truncate(console)
    stderr, truncated_err = _truncate(stderr_raw)
    truncated = truncated_out or truncated_err

    # 纯运行模式超时：把超时提示写进 stderr，让前端控制台能看到明确反馈
    if timed_out and not test_mode:
        stderr = f"[执行超时：超过 {DEFAULT_TIME_LIMIT} 秒已终止，请检查是否存在死循环]\n" + stderr

    duration_ms = int(float(time_sec) * 1000) if time_sec else 0

    return {
        # stdout / console 同值：console 为前端契约保留字段
        "stdout": stdout,
        "stderr": stderr,
        "output": stdout + stderr,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "truncated": truncated,
        "duration_ms": duration_ms,
        "results": results,
        "console": stdout,
        "compile_error": compile_error,
    }
