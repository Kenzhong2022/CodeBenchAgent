/**
 * @description 测试 POST /api/auth/login（登录）：入参校验、防邮箱枚举的统一 401
 *   默认只测失败分支；设置 LOGIN_EMAIL/LOGIN_PASSWORD 后追加真实账号的成功路径断言
 * 运行：node scripts/auth/login.mjs
 *   成功路径：$env:LOGIN_EMAIL="you@example.com"; $env:LOGIN_PASSWORD="***"; node scripts/auth/login.mjs
 */
import { api, check, errorText, finish } from "../_lib.mjs";

console.log("POST /api/auth/login（登录）");

// 入参校验分支
let res = await api("POST", "/api/auth/login", { email: "bad", password: "x" });
check("非法邮箱返回 400", res.status === 400 && res.json?.detail === "请输入合法的邮箱地址", JSON.stringify(res.json));

res = await api("POST", "/api/auth/login", { email: "a@b.com" });
check("缺少密码返回 400", res.status === 400 && res.json?.detail === "请输入密码", JSON.stringify(res.json));

// 用户不存在与密码错误统一提示，避免邮箱枚举
res = await api("POST", "/api/auth/login", { email: "nobody@test.com", password: "wrongpass" });
check("账号不存在返回 401", res.status === 401, `实际 ${res.status}`);
check("统一文案：邮箱或密码错误", res.json?.detail === "邮箱或密码错误", JSON.stringify(res.json));

// 可选：真实账号成功路径（会更新 last_login_at）
const email = process.env.LOGIN_EMAIL;
const password = process.env.LOGIN_PASSWORD;
if (email && password) {
  res = await api("POST", "/api/auth/login", { email, password });
  check(
    "登录成功返回 200 且含 user 三字段",
    res.status === 200 &&
      res.json?.ok === true &&
      typeof res.json?.user?.id === "string" &&
      res.json?.user?.email === email &&
      typeof res.json?.user?.name === "string",
    errorText(res, 200) ?? JSON.stringify(res.json),
  );

  // 密码错误同样 401（与不存在账号同文案）
  const wrong = await api("POST", "/api/auth/login", { email, password: "definitely-wrong" });
  check("密码错误返回 401", wrong.status === 401 && wrong.json?.detail === "邮箱或密码错误", JSON.stringify(wrong.json));
} else {
  console.log("  [SKIP] 未设置 LOGIN_EMAIL/LOGIN_PASSWORD，跳过成功路径");
}

finish("auth/login");
