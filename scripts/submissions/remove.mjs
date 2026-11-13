/**
 * @description 测试 DELETE /api/submissions?id=（删除提交记录）
 *   测试记录会在结束时删除，不留脏数据
 * 运行：node scripts/submissions/remove.mjs
 */
import { api, check, finish } from "../_lib.mjs";

console.log("DELETE /api/submissions?id=（删除提交记录）");

const ACCOUNT_ID = "00000000-0000-0000-0000-000000000000";

// 准备一条测试记录
let res = await api("POST", "/api/submissions", { problem_id: 1, account_id: ACCOUNT_ID, status: "CE" });
const id = res.json?.id;
check("前置：测试记录创建成功", res.status === 200 && id != null, JSON.stringify(res.json));

// 缺少 id
res = await api("DELETE", "/api/submissions");
check("缺少 id 返回 400", res.status === 400 && res.json?.detail === "缺少 id", JSON.stringify(res.json));

// 正常删除
res = await api("DELETE", `/api/submissions?id=${id}`);
check("删除返回 {ok:true}", res.status === 200 && res.json?.ok === true, JSON.stringify(res.json));

// 删除生效：列表里不应再有该条
const list = await api("GET", "/api/submissions");
check("删除后列表无此条", !(list.json ?? []).some((r) => r.id === id));

finish("submissions/remove");
