/**
 * @description 测试 PATCH /api/submissions?id=（更新提交记录）：局部更新与缺参校验
 *   测试记录会在结束时删除，不留脏数据
 * 运行：node scripts/submissions/update.mjs
 */
import { api, check, errorText, finish } from "../_lib.mjs";

console.log("PATCH /api/submissions?id=（更新提交记录）");

const ACCOUNT_ID = "00000000-0000-0000-0000-000000000000";

// 准备一条 WA 记录
let res = await api("POST", "/api/submissions", {
  problem_id: 1,
  account_id: ACCOUNT_ID,
  status: "WA",
  pass: false,
});
const id = res.json?.id;
check("前置：测试记录创建成功", res.status === 200 && id != null, errorText(res, 200));

// 缺少 id
res = await api("PATCH", "/api/submissions", { status: "AC" });
check("缺少 id 返回 400", res.status === 400 && res.json?.detail === "缺少 id", JSON.stringify(res.json));

// 空 body
res = await api("PATCH", `/api/submissions?id=${id}`, {});
check("无可更新字段返回 400", res.status === 400 && res.json?.detail === "没有可更新的字段", JSON.stringify(res.json));

// 局部更新：WA -> AC，pass 翻转
res = await api("PATCH", `/api/submissions?id=${id}`, { status: "AC", pass: true });
check("更新返回 200", res.status === 200, errorText(res, 200) ?? JSON.stringify(res.json));
check("status/pass 已更新", res.json?.status === "AC" && res.json?.pass === true);
check("未传的 error_reason 保持原值", res.json?.error_reason === null);

// 清理测试记录
await api("DELETE", `/api/submissions?id=${id}`);

finish("submissions/update");
