/**
 * @description 测试 POST /api/auth/send-code（发送注册验证码）
 *   默认只测无副作用的校验分支；设置 SEND_CODE_EMAIL 环境变量后会真实发一封邮件
 *   并验证 60 秒重发冷却（连续第二次请求应 429）
 * 运行：node scripts/auth/send-code.mjs
 *   真实发码：$env:SEND_CODE_EMAIL="you@example.com"; node scripts/auth/send-code.mjs
 */
import { api, check, errorText, finish } from "../_lib.mjs";

console.log("POST /api/auth/send-code（发送注册验证码）");

// 校验分支（无副作用）
let res = await api("POST", "/api/auth/send-code", { email: "bad" });
check("非法邮箱返回 400", res.status === 400 && res.json?.detail === "请输入合法的邮箱地址", JSON.stringify(res.json));

res = await api("POST", "/api/auth/send-code", {});
check("缺少 email 返回 400", res.status === 400, JSON.stringify(res.json));

// 可选：真实发码（会发邮件 + 写入 Redis 冷却键）
const email = process.env.SEND_CODE_EMAIL;
if (email) {
  res = await api("POST", "/api/auth/send-code", { email });
  check("真实发码返回 200 且 ttl=300", res.status === 200 && res.json?.ttl === 300, errorText(res, 200) ?? JSON.stringify(res.json));

  res = await api("POST", "/api/auth/send-code", { email });
  check(
    "60 秒内重发返回 429",
    res.status === 429 && res.json?.detail === "发送过于频繁，请 60 秒后再试",
    JSON.stringify(res.json),
  );
} else {
  console.log("  [SKIP] 未设置 SEND_CODE_EMAIL，跳过真实发码与冷却断言");
}

finish("auth/send-code");
