/**
 * @description 测试脚本共享工具：所有接口测试脚本都从这里导入，保证输出格式与退出码一致
 *
 * 使用方式（任意测试脚本内）：
 *   import { api, check, finish, randomId } from "../_lib.mjs";
 *
 * 环境变量：
 *   CODEBENCH_API_URL  Python 服务端地址，默认 http://127.0.0.1:8000
 *                      （也可指向前端代理 http://localhost:3000 或线上地址做穿透测试）
 */

export const BASE = process.env.CODEBENCH_API_URL ?? "http://127.0.0.1:8000";

// 全局失败计数，finish() 据此决定退出码
let failed = 0;

// 请求耗时记录：{ method, path, status, ms }，finish() 时输出耗时表
const timings = [];

/**
 * @description 获取本次进程内记录的全部请求耗时（毫秒），按耗时降序
 */
export function getTimings() {
  return [...timings].sort((a, b) => b.ms - a.ms);
}

/**
 * @description 调用接口并返回解析结果
 * @param method HTTP 方法
 * @param path 路径（以 / 开头）
 * @param body 请求体对象（GET/DELETE 时省略）
 * @returns { status, json }：status 为 HTTP 状态码，json 为解析后的响应体（解析失败为 null）
 */
export async function api(method, path, body) {
  let res, json;
  const t0 = performance.now();
  try {
    res = await fetch(`${BASE}${path}`, {
      method,
      headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    json = await res.json().catch(() => null);
  } catch {
    // 服务未启动 / 网络不可达：返回 status 0，让 check() 走 FAIL 分支而不是抛异常崩溃
    timings.push({ method, path, status: 0, ms: performance.now() - t0 });
    return { status: 0, json: null };
  }
  timings.push({ method, path, status: res.status, ms: performance.now() - t0 });
  return { status: res.status, json };
}

/**
 * @description 断言单条检查项：通过打印 PASS，失败打印 FAIL 并计入失败数
 * @param label 检查项名称（会展示在输出里）
 * @param ok 布尔断言结果
 * @param detail 失败时附带的上下文（响应体等）
 */
export function check(label, ok, detail = "") {
  if (ok) {
    console.log(`  [PASS] ${label}`);
  } else {
    failed += 1;
    console.log(`  [FAIL] ${label}${detail ? ` -> ${detail}` : ""}`);
  }
}

/**
 * @description 校验响应是否为前端统一错误结构并返回错误文案
 * @param res api() 的返回值
 * @param expectStatus 期望的 HTTP 状态码
 * @returns 错误信息字符串；结构不符时返回 undefined（让 check 判空失败）
 */
export function errorText(res, expectStatus) {
  if (res.status !== expectStatus) return undefined;
  return res.json?.error ?? res.json?.detail;
}

/**
 * @description 生成不易撞车的测试 id（crud 表主键由客户端提供）
 * @param prefix 前缀，如 "t-"；随机段固定 8 位 hex，保证输出可读
 */
export function randomId(prefix = "t-") {
  return `${prefix}${crypto.randomUUID().replace(/-/g, "").slice(0, 8)}`;
}

/**
 * @description 脚本收尾：打印结果汇总并以失败数作为进程退出码（0 全过 / 1 有失败）
 * @param name 脚本名称（展示用）
 */
export function finish(name) {
  // 请求耗时表：帮助定位慢接口（含 Supabase 云端查询的往返时间）
  const rows = getTimings();
  if (rows.length > 0) {
    console.log("\n  请求耗时：");
    for (const t of rows) {
      console.log(`    ${t.ms.toFixed(0).padStart(5)}ms  ${t.status}  ${t.method} ${t.path}`);
    }
  }
  if (failed === 0) {
    console.log(`\n${name}: 全部通过 (${BASE})`);
  } else {
    console.log(`\n${name}: ${failed} 项失败 (${BASE})`);
    process.exit(1);
  }
}
