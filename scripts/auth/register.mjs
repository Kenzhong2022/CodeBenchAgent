/**
 * @description 测试 POST /api/auth/register（注册）：入参校验与验证码分支
 *   默认只测无副作用的校验分支（不写数据库）；完整注册流程需先真实发码、
 *   再从邮箱拿到验证码后通过 REGISTER_EMAIL/REGISTER_CODE/REGISTER_PASSWORD 走成功路径
 * 运行：node scripts/auth/register.mjs
 *   成功路径：$env:REGISTER_EMAIL="..."; $env:REGISTER_CODE="123456"; node scripts/auth/register.mjs
 */
import { api, check, finish } from "../_lib.mjs";

console.log("POST /api/auth/register（注册）");

// 入参校验分支（无副作用）
let res = await api("POST", "/api/auth/register", { name: "", email: "a@b.com", code: "123456", password: "123456" });
check("空用户名返回 400", res.status === 400 && res.json?.detail === "请输入用户名", JSON.stringify(res.json));

res = await api("POST", "/api/auth/register", { name: "t", email: "bad", code: "123456", password: "123456" });
check("非法邮箱返回 400", res.status === 400 && res.json?.detail === "请输入合法的邮箱地址", JSON.stringify(res.json));

res = await api("POST", "/api/auth/register", { name: "t", email: "a@b.com", code: "12ab56", password: "123456" });
check("验证码非 6 位数字返回 400", res.status === 400 && res.json?.detail === "验证码应为 6 位数字", JSON.stringify(res.json));

res = await api("POST", "/api/auth/register", { name: "t", email: "a@b.com", code: "123456", password: "123" });
check("密码不足 6 位返回 400", res.status === 400 && res.json?.detail === "密码长度至少 6 位", JSON.stringify(res.json));

// Redis 中无此邮箱验证码：用随机 +别名邮箱保证从未发过码
const unknownEmail = `noreg-${crypto.randomUUID().slice(0, 8)}@test.com`;
res = await api("POST", "/api/auth/register", { name: "t", email: unknownEmail, code: "123456", password: "123456" });
check(
  "无验证码返回 400（不消费不落库）",
  res.status === 400 && res.json?.detail === "验证码已过期或未发送，请重新获取",
  JSON.stringify(res.json),
);

// 可选：成功路径（需要真实验证码，注册成功会真实写入 accounts 表）
const email = process.env.REGISTER_EMAIL;
const code = process.env.REGISTER_CODE;
if (email && code) {
  res = await api("POST", "/api/auth/register", {
    name: process.env.REGISTER_NAME ?? "脚本测试",
    email,
    code,
    password: process.env.REGISTER_PASSWORD ?? "test123456",
  });
  check(
    "注册成功返回 200 且含 user",
    res.status === 200 && res.json?.ok === true && typeof res.json?.user?.id === "string",
    JSON.stringify(res.json),
  );

  // 同一验证码已被消费，重复注册应失败
  const again = await api("POST", "/api/auth/register", { name: "t", email, code, password: "123456" });
  check("验证码一次性消费，重放返回 400", again.status === 400, JSON.stringify(again.json));
} else {
  console.log("  [SKIP] 未设置 REGISTER_EMAIL/REGISTER_CODE，跳过成功路径");
}

finish("auth/register");
