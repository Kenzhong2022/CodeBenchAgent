# scripts/ — 接口测试脚本

对本项目（CodeBenchAgent FastAPI）的全部 API 做**可直接运行的自动化测试**。目录结构与 `routers/` 的业务分层一一对应：**看到文件夹名就知道测的是哪一组接口，看到文件名就知道测的是哪个接口**。

脚本用 Node 原生 `fetch` 编写（需 Node ≥ 18），无任何第三方依赖。所有写操作脚本（crud/submissions 的 create/update/remove）**结束时会自动清理自己创建的测试数据**，不会留下脏数据；默认都只测无副作用的分支，涉及真实发邮件、写库的成功路径需要显式设置环境变量才会执行。

## 目录结构

```
scripts/
├── README.md              # 本文件
├── _lib.mjs               # 共享工具：api() 请求封装、check() 断言、finish() 退出码
├── import_mbpp.py         # （已有）MBPP 数据集导入脚本，与接口测试无关
├── problems/              # 题库接口（routers/problems.py）
│   ├── list.mjs           # GET /api/problems          列表分页与 {count, data} 结构、dataset_name 筛选
│   ├── detail.mjs         # GET /api/problems?id=      单条命中与 404 分支
│   ├── count.mjs          # GET /api/problems/count    精确计数（含路由顺序回归检查）
│   └── cursor.mjs         # GET /api/problems/cursor   游标翻页与 next_cursor 传导
├── crud/                  # 通用 CRUD 接口（routers/crud.py）
│   ├── list.mjs           # GET    /api/crud/{table}   白名单表读取、升序、未知表 404
│   ├── create.mjs         # POST   /api/crud/{table}   新增、数值列转换、白名单外字段过滤
│   ├── update.mjs         # PATCH  /api/crud/{table}   局部更新、缺 id / 不存在行
│   └── remove.mjs         # DELETE /api/crud/{table}   删除生效、缺 id 400
├── submissions/           # 提交记录接口（routers/submissions.py）
│   ├── list.mjs           # GET    /api/submissions            列表升序、状态枚举合法性
│   ├── create.mjs         # POST   /api/submissions            必填/枚举/类型校验、状态大写化
│   ├── update.mjs         # PATCH  /api/submissions?id=        局部更新、缺 id / 空 body
│   └── remove.mjs         # DELETE /api/submissions?id=        删除生效、缺 id 400
└── auth/                  # 认证接口（routers/auth.py）
    ├── send-code.mjs      # POST /api/auth/send-code   邮箱校验；可选真实发码 + 60 秒冷却 429
    ├── register.mjs       # POST /api/auth/register    入参校验、无验证码分支；可选成功路径 + 验证码一次性消费
    └── login.mjs          # POST /api/auth/login       入参校验、统一 401 防枚举；可选真实账号成功路径
```

## 前置条件

1. Python 服务已启动（脚本默认打 `http://127.0.0.1:8000`）：
   ```powershell
   .venv\Scripts\python.exe main.py
   ```
2. Node ≥ 18（用到原生 fetch）。
3. Windows 终端如中文乱码，先执行 `chcp 65001`。

## 全部命令

在仓库根目录（`CodeBenchAgent/`）执行。每条命令独立可跑，**失败时进程退出码为 1**，方便接 CI。

### 题库 problems（只读，无副作用）

| 命令 | 测的是什么 |
| --- | --- |
| `node scripts/problems/list.mjs` | 题目列表：limit/offset 分页、`{count, data}` 响应结构、`dataset_name` 筛选 |
| `node scripts/problems/detail.mjs` | 题目详情：`?id=1` 命中返回完整对象；不存在的 id 返回 404「题目不存在」 |
| `node scripts/problems/count.mjs` | 题库总数：`/count` 返回正数，且与列表接口交叉验证（422 说明被 `/{problem_id}` 路由吞掉，是注册顺序回归） |
| `node scripts/problems/cursor.mjs` | 游标分页：首页结构、`next_cursor` 翻页后 id 严格递增无重复 |

### 通用 CRUD crud（写操作自动清理）

| 命令 | 测的是什么 |
| --- | --- |
| `node scripts/crud/list.mjs` | 白名单表读取（products/accounts）：数组、created_at 升序、数值列类型；未知表 404「未知数据表」 |
| `node scripts/crud/create.mjs` | 新增：字符串数值转 number、整数值转 int、白名单外字段被过滤、非法数值 400、未知表 404 |
| `node scripts/crud/update.mjs` | 更新：只更新传入字段（stock 不受影响）、缺 id 400、不存在的行 404 |
| `node scripts/crud/remove.mjs` | 删除：`{ok:true}`、删除后列表查无此行、缺 id 400 |

### 提交记录 submissions（写操作自动清理）

| 命令 | 测的是什么 |
| --- | --- |
| `node scripts/submissions/list.mjs` | 列表：升序、status 全部为 AC/WA/CE/RE/TLE 枚举值 |
| `node scripts/submissions/create.mjs` | 创建：必填字段缺失文案、problem_id 小数 / account_id 空白 / 非法 status / pass 非布尔各 400 分支、status 小写传入被大写化 |
| `node scripts/submissions/update.mjs` | 更新：缺 id 400、空 body 400「没有可更新的字段」、WA→AC 局部更新 |
| `node scripts/submissions/remove.mjs` | 删除：`{ok:true}`、删除后查无此条、缺 id 400 |

### 认证 auth（默认无副作用，成功路径需环境变量）

| 命令 | 测的是什么 |
| --- | --- |
| `node scripts/auth/send-code.mjs` | 发码：非法/缺失邮箱 400。加 `$env:SEND_CODE_EMAIL="你的邮箱"` 后追加：真实收码 200（ttl=300）、60 秒内重发 429 |
| `node scripts/auth/register.mjs` | 注册：空用户名/非法邮箱/非 6 位验证码/弱密码各 400、无验证码 400。加 `$env:REGISTER_EMAIL` + `$env:REGISTER_CODE`（先真实发码后从邮箱取得）后追加：注册成功、验证码一次性消费重放失败 |
| `node scripts/auth/login.mjs` | 登录：非法邮箱/缺密码 400、账号不存在与密码错误统一 401「邮箱或密码错误」（防枚举）。加 `$env:LOGIN_EMAIL` + `$env:LOGIN_PASSWORD` 后追加：真实登录成功、密码错误 401 |

### 一键跑全部

```powershell
node scripts/problems/list.mjs; node scripts/problems/detail.mjs; node scripts/problems/count.mjs; node scripts/problems/cursor.mjs; node scripts/crud/list.mjs; node scripts/crud/create.mjs; node scripts/crud/update.mjs; node scripts/crud/remove.mjs; node scripts/submissions/list.mjs; node scripts/submissions/create.mjs; node scripts/submissions/update.mjs; node scripts/submissions/remove.mjs; node scripts/auth/send-code.mjs; node scripts/auth/register.mjs; node scripts/auth/login.mjs
```

## 指向其他环境

所有脚本都读 `CODEBENCH_API_URL` 环境变量，默认 `http://127.0.0.1:8000`。可以指向前端代理或线上地址做穿透测试：

```powershell
$env:CODEBENCH_API_URL="http://localhost:3000"   # 经 Next.js 转发层测（错误结构为 {error}）
$env:CODEBENCH_API_URL="https://codebenchagent.vercel.app"   # 测线上部署
```

注意：Python 端错误结构是 `{detail}`，前端转发层会转成 `{error}`。脚本的断言同时兼容两种结构，因此同一套脚本可直接用于三层验证（本地 Python / 本地前端代理 / 线上）。
