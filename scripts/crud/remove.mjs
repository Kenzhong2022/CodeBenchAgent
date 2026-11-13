/**
 * @description 测试 DELETE /api/crud/{table}（通用 CRUD 删除）：删除生效与缺参校验
 *   测试行会在结束时删除，不留脏数据
 * 运行：node scripts/crud/remove.mjs
 */
import { api, check, finish, randomId } from "../_lib.mjs";

console.log("DELETE /api/crud/{table}（通用 CRUD 删除）");

// 准备一行测试数据
const id = randomId("t-");
await api("POST", "/api/crud/products", { id, name: "待删除", price: 1, stock: 1 });

// 缺少 id 参数
let res = await api("DELETE", "/api/crud/products");
check("缺少 id 返回 400", res.status === 400 && res.json?.detail === "缺少 id", JSON.stringify(res.json));

// 正常删除
res = await api("DELETE", `/api/crud/products?id=${id}`);
check("删除返回 {ok:true}", res.status === 200 && res.json?.ok === true, JSON.stringify(res.json));

// 删除生效：列表里不应再有该行
const list = await api("GET", "/api/crud/products");
check("删除后列表无此行", !(list.json ?? []).some((r) => r.id === id));

finish("crud/remove");
