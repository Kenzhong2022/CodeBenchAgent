/**
 * @description 测试 GET /api/submissions（提交记录列表）：只读脚本，无副作用
 * 运行：node scripts/submissions/list.mjs
 */
import { api, check, finish } from "../_lib.mjs";

console.log("GET /api/submissions（提交记录列表）");

const res = await api("GET", "/api/submissions");
const rows = res.json ?? [];
check("返回 200 数组", res.status === 200 && Array.isArray(rows), `实际 ${res.status}`);
check(
  "按 created_at 升序排列",
  rows.every((r, i) => i === 0 || rows[i - 1].created_at <= r.created_at),
);
check(
  "status 都是合法枚举值",
  rows.every((r) => ["AC", "WA", "CE", "RE", "TLE"].includes(r.status)),
);

finish("submissions/list");
