# JWLCode 前端 API 联调手册

## 1. 联调入口

| 项目 | 本地开发值 |
|---|---|
| 页面地址 | `http://school.localhost:8000` |
| API Base URL | `http://school.localhost:8000` |
| Frappe 方法前缀 | `/api/method/` |
| Frappe 资源前缀 | `/api/resource/` |
| WebSocket | `http://school.localhost:9000` |
| 默认管理员 | `Administrator` / `admin`，仅限本地开发 |

业务 API 的真实地址是 `/api/method/jwlcode.api.v1.<method>`。架构文档中的 `/api/v1/*` 是逻辑路径，不是当前可请求地址。

所有业务成功响应都由 Frappe 包装：

```json
{
  "message": {}
}
```

前端请求层应返回 `response.message`，不要让页面组件重复解包。

## 2. 认证

### 2.1 浏览器前端：Session Cookie

登录：

```http
POST /api/method/login
Content-Type: application/json

{
  "usr": "student@example.com",
  "pwd": "password"
}
```

跨请求携带 Session：

```ts
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://school.localhost:8000";

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const messages = payload._server_messages
      ? JSON.parse(payload._server_messages).map((item: string) => JSON.parse(item).message)
      : [];
    throw new Error(messages[0] ?? payload.exception ?? `HTTP ${response.status}`);
  }
  return payload.message as T;
}
```

退出：

```http
POST /api/method/logout
```

建议前端与 Frappe 通过同一域名反向代理。不同域名部署时需要配置 Frappe `allow_cors`，并正确处理 Cookie 的 SameSite/Secure 属性。

### 2.2 API Key/Secret

仅用于 Postman、后端服务或可信脚本：

```http
Authorization: token API_KEY:API_SECRET
```

不要把 API Secret 放进 Vue、Nuxt、React 构建产物或浏览器环境变量。

## 3. 业务接口总表

| 场景 | HTTP | 实际地址 | 权限 |
|---|---|---|---|
| 当前用户 | GET | `/api/method/jwlcode.api.v1.me` | 登录用户 |
| 课程列表 | GET | `/api/method/jwlcode.api.v1.courses` | 登录用户 |
| 课时详情 | GET | `/api/method/jwlcode.api.v1.lesson` | 课程成员/教师 |
| 题目详情 | GET | `/api/method/jwlcode.api.v1.problem` | 课程成员/教师 |
| 自定义输入运行 | POST | `/api/method/jwlcode.api.v1.create_code_run` | 学生 |
| 正式提交 | POST | `/api/method/jwlcode.api.v1.create_submission` | 学生 |
| 提交结果 | GET | `/api/method/jwlcode.api.v1.submission` | 本人/授课教师/校区管理员 |
| 学生进度 | GET | `/api/method/jwlcode.api.v1.student_progress` | 本人/授课教师/校区管理员 |
| 创建作业 | POST | `/api/method/jwlcode.api.v1.create_assignment` | 授课教师/管理员 |
| 班级分析 | GET | `/api/method/jwlcode.api.v1.class_analytics` | 授课教师/管理员 |
| 人工调分 | POST | `/api/method/jwlcode.api.v1.adjust_score` | 授课教师/管理员 |
| 判题回调 | POST | `/api/method/jwlcode.api.v1.judge_callback` | Judge Service 签名 |

## 4. 接口明细

### 4.1 当前用户

```http
GET /api/method/jwlcode.api.v1.me
```

无参数。响应：

```json
{
  "message": {
    "user": "student@example.com",
    "full_name": "张三",
    "roles": ["JWL Student"],
    "data_scope": {
      "student_id": "student-id",
      "class_ids": ["class-id"]
    }
  }
}
```

教师的 `data_scope` 包含 `teacher_id` 和授课 `class_ids`。

### 4.2 课程列表

```http
GET /api/method/jwlcode.api.v1.courses?start=0&page_length=20
```

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `start` | integer | 否 | 0 | 从零开始的偏移量 |
| `page_length` | integer | 否 | 20 | 1–100 |

```json
{
  "message": {
    "data": [{
      "name": "course-id",
      "title": "C++ 基础",
      "version": 1,
      "status": "Published",
      "description": "...",
      "owner_teacher": "teacher-id",
      "modified": "2026-08-31 08:00:00"
    }],
    "has_more": false
  }
}
```

### 4.3 课时详情

```http
GET /api/method/jwlcode.api.v1.lesson?lesson_id=lesson-id
```

必填查询参数：`lesson_id: string`。

```json
{
  "message": {
    "id": "lesson-id",
    "chapter_id": "chapter-id",
    "course_id": "course-id",
    "title": "变量与输入输出",
    "content": "<p>...</p>",
    "sort_order": 1,
    "status": "Published",
    "progress": {
      "status": "In Progress",
      "percent": 50,
      "modified": "2026-08-31 08:00:00"
    }
  }
}
```

没有学生身份时 `progress` 为 `null`。

### 4.4 题目详情

```http
GET /api/method/jwlcode.api.v1.problem?problem_id=problem-id
```

必填查询参数：`problem_id: string`。

```json
{
  "message": {
    "id": "problem-id",
    "lesson_id": "lesson-id",
    "title": "A+B",
    "statement": "<p>...</p>",
    "type": "Programming",
    "version": 1,
    "code_template": "#include <iostream>\n...",
    "max_score": 100,
    "limits": {
      "allowed_languages": "cpp17",
      "time_limit_ms": 1000,
      "memory_limit_kb": 262144,
      "mode": "ACM"
    }
  }
}
```

隐藏测试引用、校验摘要和编译参数不会返回给前端。

### 4.5 自定义输入运行

```http
POST /api/method/jwlcode.api.v1.create_code_run
Content-Type: application/json

{
  "problem_id": "problem-id",
  "language": "cpp17",
  "source_code": "#include <iostream>\nint main() { return 0; }",
  "client_request_id": "01J-RUN-UNIQUE",
  "custom_input": "1 2\n"
}
```

| 参数 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `problem_id` | string | 是 | 已发布且学生可访问 |
| `language` | string | 是 | 必须在 Judge Policy 白名单中 |
| `source_code` | string | 是 | 非空，最大 128 KiB |
| `client_request_id` | string | 是 | 同一学生内幂等，最大 140 字符 |
| `custom_input` | string | 否 | 最大 64 KiB |

响应：

```json
{
  "message": {
    "submission_id": "submission-id",
    "status": "QUEUED",
    "trace_id": "uuid"
  }
}
```

相同 `client_request_id` 重放时返回原提交，并增加 `idempotent_replay: true`。

### 4.6 正式提交

```http
POST /api/method/jwlcode.api.v1.create_submission
Content-Type: application/json

{
  "problem_id": "problem-id",
  "assignment_id": "assignment-id",
  "language": "cpp17",
  "source_code": "#include <iostream>\nint main() { return 0; }",
  "client_request_id": "01J-SUBMIT-UNIQUE"
}
```

`assignment_id` 可省略；提供时会校验作业已发布、当前开放、未过截止时间且学生在目标班级。其余约束和响应同代码试运行。每名学生两次新建提交至少间隔两秒。

### 4.7 查询提交

```http
GET /api/method/jwlcode.api.v1.submission?submission_id=submission-id
```

必填查询参数：`submission_id: string`。

```json
{
  "message": {
    "submission_id": "submission-id",
    "problem_id": "problem-id",
    "type": "Submission",
    "status": "ACCEPTED",
    "status_version": 3,
    "score": 100,
    "time_ms": 42,
    "memory_kb": 8192,
    "compiler_message": null,
    "finished_at": "2026-08-31 08:00:00"
  }
}
```

本人查询时还会返回 `source_code`；类型为 `Run` 时返回 `output`。前端可每 1–2 秒轮询，进入终态后停止。

### 4.8 学生进度

```http
GET /api/method/jwlcode.api.v1.student_progress?student_id=student-id
```

```json
{
  "message": {
    "student_id": "student-id",
    "data": [{
      "lesson": "lesson-id",
      "status": "Completed",
      "percent": 100,
      "modified": "2026-08-31 08:00:00"
    }]
  }
}
```

### 4.9 创建作业

```http
POST /api/method/jwlcode.api.v1.create_assignment
Content-Type: application/json

{
  "title": "第一章作业",
  "academic_class": "class-id",
  "course_id": "course-id",
  "opens_at": "2026-09-01T00:00:00+08:00",
  "due_at": "2026-09-08T23:59:59+08:00",
  "max_score": 100,
  "grading_rule": "Highest score"
}
```

`title`、`academic_class`、`course_id`、`opens_at`、`due_at` 必填。截止时间必须晚于开放时间。新作业状态为 `Draft`，需要教师或管理员在 Frappe Desk 发布。

```json
{
  "message": {
    "assignment_id": "assignment-id",
    "status": "Draft"
  }
}
```

### 4.10 班级分析

```http
GET /api/method/jwlcode.api.v1.class_analytics?academic_class=class-id
```

```json
{
  "message": {
    "class_id": "class-id",
    "student_count": 30,
    "submissions_by_status": [{
      "status": "ACCEPTED",
      "count": 25,
      "average_score": 92.5
    }]
  }
}
```

### 4.11 人工调分

```http
POST /api/method/jwlcode.api.v1.adjust_score
Content-Type: application/json

{
  "submission_id": "submission-id",
  "new_score": 95,
  "reason": "测试数据异常，人工复核"
}
```

`new_score` 必须位于 0 和题目满分之间，`reason` 必填。系统会写入不可覆盖的 JWL Score Adjustment 审计记录。

```json
{
  "message": {
    "submission_id": "submission-id",
    "score_id": "score-id",
    "final_score": 95
  }
}
```

## 5. 判题回调

回调不是浏览器接口，由 Judge Service 调用：

- Frappe 站点配置项 `jwlcode_judge_callback_secret` 必须与 Judge Service 使用的密钥完全一致；未配置时回调会被拒绝。
- 浏览器前端不得调用 Judge Service 的 `/internal/v1/*` 接口，也不得持有回调密钥。
- 当前导出的 OpenAPI 只描述已经实现并可访问的 Frappe 接口；Judge Service 内部接口属于后端间契约，不作为前端接口导出。

```http
POST /api/method/jwlcode.api.v1.judge_callback
Content-Type: application/json
X-JWL-Timestamp: 1788134400
X-JWL-Signature: sha256=<hex-hmac>

{
  "event_id": "event-20001",
  "judge_request_id": "judge-10086",
  "submission_id": "submission-id",
  "status": "ACCEPTED",
  "status_version": 3,
  "score": 100,
  "time_ms": 42,
  "memory_kb": 8192,
  "compiler_message": null,
  "output": null,
  "finished_at": "2026-08-31T08:00:00Z"
}
```

必填字段：`event_id`、`judge_request_id`、`submission_id`、`status`、`status_version`。

签名原文必须使用收到的原始请求体字节，不能解析 JSON 后重新序列化：

```text
signature = hex(HMAC-SHA256(
  callback_secret,
  utf8(timestamp + ".") + raw_request_body
))
```

Node.js 示例：

```ts
import crypto from "node:crypto";

const rawBody = JSON.stringify(payload);
const timestamp = Math.floor(Date.now() / 1000).toString();
const signature = crypto
  .createHmac("sha256", process.env.JWLCODE_CALLBACK_SECRET!)
  .update(`${timestamp}.`)
  .update(rawBody)
  .digest("hex");

await fetch(`${FRAPPE_BASE}/api/method/jwlcode.api.v1.judge_callback`, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-JWL-Timestamp": timestamp,
    "X-JWL-Signature": `sha256=${signature}`,
  },
  body: rawBody,
});
```

时间戳允许偏差为五分钟。相同 `event_id` 返回：

```json
{"message": {"accepted": true, "duplicate": true}}
```

旧的 `status_version` 返回 `stale: true`。状态版本必须单调递增，合法状态迁移为：

```text
QUEUED -> COMPILING -> RUNNING -> ACCEPTED
                              -> WRONG_ANSWER
                              -> TIME_LIMIT_EXCEEDED
                              -> MEMORY_LIMIT_EXCEEDED
                              -> RUNTIME_ERROR
         -> COMPILE_ERROR
         -> SYSTEM_ERROR
         -> CANCELED
```

`QUEUED -> RUNNING` 也允许。终态不能被覆盖。正式提交进入终态时同步更新 Score；`ACCEPTED` 时将对应 Lesson Progress 更新为 100%。

## 6. 错误处理

常见状态：

| HTTP | 含义 |
|---|---|
| 401 / 403 | 未登录或没有数据范围权限 |
| 404 | DocType 或业务对象不存在 |
| 417 | Frappe 业务校验失败，具体消息在 `_server_messages` |
| 429 | 反向代理或部署层限流 |
| 500 | 未处理异常或服务配置问题 |

典型错误体：

```json
{
  "exception": "frappe.exceptions.ValidationError: ...",
  "exc_type": "ValidationError",
  "_server_messages": "[\"{\\\"message\\\":\\\"Language is not allowed for this problem\\\"}\"]"
}
```

页面只展示清洗后的 `message`，不要直接输出完整 `exception` 或堆栈。

## 7. 前端轮询建议

提交成功后保存 `submission_id`，每 1–2 秒查询提交状态。以下为终态：

```ts
export const TERMINAL_STATUSES = new Set([
  "ACCEPTED",
  "WRONG_ANSWER",
  "TIME_LIMIT_EXCEEDED",
  "MEMORY_LIMIT_EXCEEDED",
  "RUNTIME_ERROR",
  "COMPILE_ERROR",
  "SYSTEM_ERROR",
  "CANCELED",
]);
```

页面卸载、浏览器切到后台或进入终态时停止轮询。网络错误使用指数退避，不要用新的 `client_request_id` 自动重建提交。

## 8. Frappe 原生 CRUD

后台主数据优先使用 Frappe Desk。确需调用时，原生格式为：

```http
GET /api/resource/JWL%20Course
GET /api/resource/JWL%20Course/{name}
POST /api/resource/JWL%20Course
PUT /api/resource/JWL%20Course/{name}
DELETE /api/resource/JWL%20Course/{name}
```

可用 DocType 包括 Campus、Student、Teacher、Academic Class、Enrollment、Teaching Assignment、Course、Chapter、Lesson、Problem、Judge Policy、Assignment、Progress、Submission、Score 和 Score Adjustment。原生接口仍会执行角色和数据范围权限，前端不能依赖隐藏按钮代替服务端授权。

## 9. 可导入文件

- `docs/openapi.json`：OpenAPI 3.1，可导入 Swagger UI、Apifox、YApi 等。
- `docs/JWLCode.postman_collection.json`：Postman Collection 2.1。
