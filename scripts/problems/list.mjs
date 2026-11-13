/**
 * @description 测试 GET /api/problems（题目列表）：分页参数与 {count, data} 响应结构
 * 运行：node scripts/problems/list.mjs
 */
import { api, check, errorText, finish } from "../_lib.mjs";

console.log("GET /api/problems（题目列表）");

// 默认分页：limit=2 应返回最多 2 条，body 为 {count, data} 结构
let res = await api("GET", "/api/problems?limit=2&offset=0");
check("limit=2 返回 200", res.status === 200, `实际 ${res.status} ${JSON.stringify(res.json)?.slice(0, 120)}`);
check("响应含 count 字段", typeof res.json?.count === "number");
check("data 是数组且不超过 2 条", Array.isArray(res.json?.data) && res.json.data.length <= 2);

// dataset_name 筛选：mbpp 是已知数据集，返回应全部命中该数据集
res = await api("GET", "/api/problems?dataset_name=mbpp&limit=5&offset=0");
const allMatch = (res.json?.data ?? []).every((p) => p.dataset_name === "mbpp");
check("dataset_name=mbpp 筛选生效", res.status === 200 && allMatch, errorText(res, 200) ?? "存在不属于 mbpp 的行");

finish("problems/list");
