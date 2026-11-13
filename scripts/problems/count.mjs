/**
 * @description 测试 GET /api/problems/count（题库精确计数）：统计卡片使用
 *   该路由必须注册在 /{problem_id} 之前，否则 "count" 会被当作路径参数吞掉（表现为 422）
 * 运行：node scripts/problems/count.mjs
 */
import { api, check, finish } from "../_lib.mjs";

console.log("GET /api/problems/count（题库总数）");

const res = await api("GET", "/api/problems/count");
check("返回 200", res.status === 200, `实际 ${res.status}（422 说明被 /{problem_id} 路由吞掉）`);
check("count 是正数", typeof res.json?.count === "number" && res.json.count > 0, JSON.stringify(res.json));

// 与列表接口交叉验证：count 应不小于任一页的返回条数
const list = await api("GET", "/api/problems?limit=2&offset=0");
check(
  "count >= 列表单页条数",
  res.json?.count >= (list.json?.data?.length ?? 0),
  `count=${res.json?.count}`,
);

finish("problems/count");
