/**
 * @description 测试 GET /api/problems/{id}（题目单条查询）：命中与 404 分支
 *   注意：`?id=` 查询参数形式是前端转发层（app/api/problems/route.ts）的约定，
 *   前端会把它转成路径形式转发到 Python 端，因此这里直接测路径形式
 * 运行：node scripts/problems/detail.mjs
 */
import { api, check, finish } from "../_lib.mjs";

console.log("GET /api/problems/{id}（题目详情）");

// 命中：id=1 应返回完整题目对象
let res = await api("GET", "/api/problems/1");
check("id=1 返回 200", res.status === 200, `实际 ${res.status}`);
check(
  "返回对象含 id/prompt/test_cases",
  res.json?.id === 1 && typeof res.json?.prompt === "string" && Array.isArray(res.json?.test_cases),
);

// 未命中：不存在的 id 应 404 且 detail 为"题目不存在"
res = await api("GET", "/api/problems/99999999");
check("不存在的 id 返回 404", res.status === 404, `实际 ${res.status}`);
check("错误文案为 题目不存在", res.json?.detail === "题目不存在", JSON.stringify(res.json));

finish("problems/detail");
