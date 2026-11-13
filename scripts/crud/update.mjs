/**
 * @description 测试 PATCH /api/crud/{table}（通用 CRUD 更新）：局部更新与参数校验
 *   测试行会在结束时删除，不留脏数据
 * 运行：node scripts/crud/update.mjs
 */
import { api, check, errorText, finish, randomId } from "../_lib.mjs";

console.log("PATCH /api/crud/{table}（通用 CRUD 更新）");

// 准备一行测试数据
const id = randomId("t-");
await api("POST", "/api/crud/products", { id, name: "更新前", price: 1, stock: 1 });

// 局部更新：只传 name 和 price，stock 不应被改动
let res = await api("PATCH", "/api/crud/products", { id, name: "更新后", price: 99 });
check("更新返回 200", res.status === 200, errorText(res, 200) ?? JSON.stringify(res.json));
check("name/price 已更新", res.json?.name === "更新后" && res.json?.price === 99);
check("未传的 stock 保持原值", res.json?.stock === 1);

// 校验分支
res = await api("PATCH", "/api/crud/products", { name: "缺 id" });
check("缺少 id 返回 400", res.status === 400, JSON.stringify(res.json));

res = await api("PATCH", "/api/crud/products", { id: randomId("none-"), name: "x" });
check("不存在的行返回 404", res.status === 404, JSON.stringify(res.json));

// 清理测试行
await api("DELETE", `/api/crud/products?id=${id}`);

finish("crud/update");
