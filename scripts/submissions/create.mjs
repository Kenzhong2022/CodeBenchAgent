/**
 * @description 测试 POST /api/submissions（创建提交记录）：必填校验、枚举校验与状态大写化
 *   测试记录会在结束时删除，不留脏数据
 * 运行：node scripts/submissions/create.mjs
 */
import { api, check, errorText, finish } from "../_lib.mjs";

console.log("POST /api/submissions（创建提交记录）");

// account_id 与 accounts.id 只做逻辑关联（无物理外键），用占位 UUID 即可插入
const ACCOUNT_ID = "00000000-0000-0000-0000-000000000000";

// 必填字段缺失
let res = await api("POST", "/api/submissions", { problem_id: 1 });
check("缺少必填字段返回 400", res.status === 400, JSON.stringify(res.json));
check(
  "错误文案列出缺失字段",
  typeof res.json?.detail === "string" && res.json.detail.includes("account_id") && res.json.detail.includes("status"),
  JSON.stringify(res.json),
);

// 各字段校验分支
res = await api("POST", "/api/submissions", { problem_id: 1.5, account_id: ACCOUNT_ID, status: "AC" });
check("problem_id 小数返回 400", res.status === 400 && res.json?.detail === "problem_id 必须是正整数", JSON.stringify(res.json));

res = await api("POST", "/api/submissions", { problem_id: 1, account_id: "  ", status: "AC" });
check("account_id 空白返回 400", res.status === 400 && res.json?.detail === "account_id 不能为空", JSON.stringify(res.json));

res = await api("POST", "/api/submissions", { problem_id: 1, account_id: ACCOUNT_ID, status: "XX" });
check("非法状态返回 400", res.status === 400 && res.json?.detail === "状态必须为 AC / WA / CE / RE / TLE", JSON.stringify(res.json));

res = await api("POST", "/api/submissions", { problem_id: 1, account_id: ACCOUNT_ID, status: "AC", pass: "yes" });
check("pass 非布尔返回 400", res.status === 400 && res.json?.detail === "pass 必须是布尔值", JSON.stringify(res.json));

// 正常创建：status 小写传入应被大写化
res = await api("POST", "/api/submissions", {
  problem_id: 1,
  account_id: ACCOUNT_ID,
  status: "wa",
  pass: false,
  error_reason: "测试脚本生成的失败记录",
});
check("创建返回 200", res.status === 200, errorText(res, 200) ?? JSON.stringify(res.json));
check("status 被大写化为 WA", res.json?.status === "WA");
check("返回的行含 id 与 created_at", typeof res.json?.id === "number" && typeof res.json?.created_at === "string");

// 清理测试记录
const createdId = res.json?.id;
if (createdId != null) await api("DELETE", `/api/submissions?id=${createdId}`);

finish("submissions/create");
