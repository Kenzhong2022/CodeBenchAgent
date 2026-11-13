/**
 * @description 测试 GET /api/problems/cursor（游标分页）：keyset 翻页与 next_cursor 传导
 * 运行：node scripts/problems/cursor.mjs
 */
import { api, check, finish } from "../_lib.mjs";

console.log("GET /api/problems/cursor（游标分页）");

// 第一页：limit=2
const page1 = await api("GET", "/api/problems/cursor?limit=2");
check("首页返回 200", page1.status === 200, `实际 ${page1.status}`);
check(
  "响应含 items/has_more/next_cursor",
  Array.isArray(page1.json?.items) &&
    typeof page1.json?.has_more === "boolean" &&
    (page1.json?.next_cursor === null || typeof page1.json?.next_cursor === "number"),
);
check("items 不超过 limit", page1.json.items.length <= 2);

if (page1.json?.has_more && page1.json?.next_cursor != null) {
  // 第二页：用首页的 next_cursor 翻页，id 应严格递增且无重复
  const page2 = await api("GET", `/api/problems/cursor?limit=2&cursor=${page1.json.next_cursor}`);
  const ids1 = page1.json.items.map((p) => p.id);
  const ids2 = page2.json?.items?.map((p) => p.id) ?? [];
  check("带 cursor 翻页返回 200", page2.status === 200, `实际 ${page2.status}`);
  check("第二页无重复且 id 递增", ids2.every((id) => id > Math.max(...ids1)), JSON.stringify({ ids1, ids2 }));
} else {
  console.log("  [SKIP] 数据不足一页，跳过翻页断言");
}

finish("problems/cursor");
