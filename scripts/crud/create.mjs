/**
 * @description 测试 POST /api/crud/{table}（通用 CRUD 新增）：白名单列过滤、数值列转换与非法输入拦截
 *   测试行会在结束时删除，不留脏数据
 * 运行：node scripts/crud/create.mjs
 */
import { api, check, errorText, finish, randomId } from "../_lib.mjs";

console.log("POST /api/crud/{table}（通用 CRUD 新增）");

// 正常新增：price 传字符串 "12.5"、stock 传字符串 "3"，服务端应转成数值且整数值转 int
const id = randomId("t-");
let res = await api("POST", "/api/crud/products", { id, name: "测试商品", price: "12.5", stock: "3" });
check("新增返回 200", res.status === 200, errorText(res, 200) ?? JSON.stringify(res.json));
check("返回创建后的行（含 id）", res.json?.id === id);
check("字符串数值被转为 number", res.json?.price === 12.5 && res.json?.stock === 3);

// 白名单外字段应被过滤：desc 不在 products 白名单里
const leak = await api("GET", "/api/crud/products");
const row = (leak.json ?? []).find((r) => r.id === id);
check("白名单外字段（desc）被过滤", row !== undefined && !("desc" in row));

// 非法输入
res = await api("POST", "/api/crud/products", { name: "x", price: "abc" });
check("数值列传非数字返回 400", res.status === 400 && res.json?.detail === "请求数据不合法", JSON.stringify(res.json));

res = await api("POST", "/api/crud/nope", { name: "x" });
check("未知表返回 404", res.status === 404 && res.json?.detail === "未知数据表", JSON.stringify(res.json));

// 清理测试行
await api("DELETE", `/api/crud/products?id=${id}`);

finish("crud/create");
