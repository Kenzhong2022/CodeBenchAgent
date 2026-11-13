/**
 * @description 测试 GET /api/crud/{table}（通用 CRUD 读取）：表名单与白名单校验
 *   只读脚本，无副作用
 * 运行：node scripts/crud/list.mjs
 */
import { api, check, finish } from "../_lib.mjs";

console.log("GET /api/crud/{table}（通用 CRUD 读取）");

// 白名单表正常读取：返回数组且 created_at 升序
let res = await api("GET", "/api/crud/products");
const rows = res.json ?? [];
check("products 返回 200 数组", res.status === 200 && Array.isArray(rows), `实际 ${res.status}`);
check(
  "按 created_at 升序排列",
  rows.every((r, i) => i === 0 || rows[i - 1].created_at <= r.created_at),
);
check(
  "数值列为 number 类型",
  rows.every((r) => typeof r.price === "number" && typeof r.stock === "number"),
);

res = await api("GET", "/api/crud/accounts");
check("accounts 返回 200 数组", res.status === 200 && Array.isArray(res.json), `实际 ${res.status}`);

// 白名单外 404
res = await api("GET", "/api/crud/nope");
check("未知表返回 404", res.status === 404, `实际 ${res.status}`);
check("错误文案为 未知数据表", res.json?.detail === "未知数据表", JSON.stringify(res.json));

finish("crud/list");
