"""Upstash Redis REST 客户端：通过 HTTP 调用（免装 redis 库），返回值结构与 @upstash/redis 一致。"""
import os
from typing import Any, Optional
from urllib.parse import quote

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("UPSTASH_REDIS_REST_URL", "")
TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")


def _enc(segment: str) -> str:
    """REST 路径段编码：key/value 可能含 @ + : 等字符（如邮箱作 key）。"""
    return quote(segment, safe="")


def _request(path: str, params: Optional[dict] = None) -> Any:
    if not BASE_URL or not TOKEN:
        raise RuntimeError("未配置 UPSTASH_REDIS_REST_URL / UPSTASH_REDIS_REST_TOKEN")
    res = httpx.get(
        f"{BASE_URL}{path}",
        params=params,
        headers={"Authorization": f"Bearer {TOKEN}"},
        timeout=10,
    )
    res.raise_for_status()
    return res.json().get("result")


def redis_get(key: str) -> Any:
    """GET key；不存在返回 None。注意 Upstash 可能把纯数字反序列化成 int，比较前需转 str。"""
    return _request(f"/get/{_enc(key)}")


def redis_set(key: str, value: str, ex: Optional[int] = None, nx: bool = False) -> Any:
    """SET key value [EX seconds] [NX]；nx=True 且键已存在时返回 None（即失败）。"""
    params: dict = {}
    if ex is not None:
        params["ex"] = ex
    if nx:
        # Upstash REST 要求 NX 为裸参数（nx= 空值即可），nx=true 会报 syntax error
        params["nx"] = ""
    return _request(f"/set/{_enc(key)}/{_enc(value)}", params)


def redis_del(*keys: str) -> int:
    """DEL key...，返回删除的键数量。"""
    return int(_request("/del/" + "/".join(_enc(k) for k in keys)) or 0)
