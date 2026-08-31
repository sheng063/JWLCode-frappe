# JWLCode Frappe API

前端完整联调说明见 [FRONTEND_API.md](FRONTEND_API.md)。机器可读接口定义见 [openapi.json](openapi.json)，Postman 导入文件见 [JWLCode.postman_collection.json](JWLCode.postman_collection.json)。

## 安装

本仓库是 Frappe app，需要放入已有 bench：

```bash
bench get-app /path/to/JWLCode-frappe
bench --site your-site install-app jwlcode
bench --site your-site migrate
```

支持 Python 3.11+，Frappe 由 bench 统一安装和管理。安装后会创建 JWL Student、JWL Teacher、JWL Campus Manager、JWL Content Manager 和 JWL Judge Service 角色。

校区管理员的数据范围使用 Frappe 原生 User Permission 配置：Allow 选择 `JWL Campus`，For Value 选择允许管理的校区。

## Judge Service 配置

在站点 `site_config.json` 中配置：

```json
{
  "jwlcode_judge_service_url": "http://judge-service:8080/",
  "jwlcode_judge_service_token": "replace-with-service-token",
  "jwlcode_judge_callback_secret": "replace-with-callback-secret"
}
```

密钥应由部署系统注入，不要提交到仓库。Web 请求只创建 Submission 并快速返回，后台 short queue 负责调用 `POST /internal/v1/judge-requests`。

## 接口地址

本实现遵循 Frappe 官方白名单方法路由，不重复实现一套 HTTP 路由器。设计文档中的友好路径与实际方法对应如下：

| 设计路径 | 方法 | Frappe 实际路径 |
|---|---|---|
| `GET /api/v1/me` | GET | `/api/method/jwlcode.api.v1.me` |
| `GET /api/v1/courses` | GET | `/api/method/jwlcode.api.v1.courses` |
| `GET /api/v1/lessons/{id}` | GET | `/api/method/jwlcode.api.v1.lesson?lesson_id={id}` |
| `GET /api/v1/problems/{id}` | GET | `/api/method/jwlcode.api.v1.problem?problem_id={id}` |
| `POST /api/v1/code-runs` | POST | `/api/method/jwlcode.api.v1.create_code_run` |
| `POST /api/v1/submissions` | POST | `/api/method/jwlcode.api.v1.create_submission` |
| `GET /api/v1/submissions/{id}` | GET | `/api/method/jwlcode.api.v1.submission?submission_id={id}` |
| `GET /api/v1/students/{id}/progress` | GET | `/api/method/jwlcode.api.v1.student_progress?student_id={id}` |
| `POST /api/v1/assignments` | POST | `/api/method/jwlcode.api.v1.create_assignment` |
| `GET /api/v1/classes/{id}/analytics` | GET | `/api/method/jwlcode.api.v1.class_analytics?academic_class={id}` |
| 人工调分 | POST | `/api/method/jwlcode.api.v1.adjust_score` |
| Judge 回调 | POST | `/api/method/jwlcode.api.v1.judge_callback` |

响应由 Frappe 包装在 `message` 字段中。登录可使用 Frappe Session、API Key/Secret 或 OAuth。

## 正式提交

```http
POST /api/method/jwlcode.api.v1.create_submission
Content-Type: application/json

{
  "problem_id": "problem-id",
  "assignment_id": "assignment-id",
  "language": "cpp17",
  "source_code": "#include <iostream>\nint main() { return 0; }",
  "client_request_id": "01JCLIENTULID"
}
```

成功时快速返回：

```json
{
  "message": {
    "submission_id": "submission-id",
    "status": "QUEUED",
    "trace_id": "9bd65f29-..."
  }
}
```

同一学生重复使用 `client_request_id` 时返回原 Submission，不会重复评测。源码上限 128 KiB，自定义输入上限 64 KiB，允许语言来自题目关联的 JWL Judge Policy。

## 回调签名

Judge Service 对原始 JSON 请求体签名：

```text
hex_hmac_sha256(callback_secret, timestamp + "." + raw_request_body)
```

请求头：

- `X-JWL-Timestamp`: Unix 秒时间戳。
- `X-JWL-Signature`: 十六进制摘要，可带 `sha256=` 前缀。

回调还必须包含单调递增的 `status_version`。相同 `event_id` 会幂等成功，旧版本会被忽略，终态不能被后续状态覆盖。正式提交进入终态时，Submission、Score、回调事件以及 ACCEPTED 对应的 Progress 在同一请求事务中更新。

## Frappe 原生能力复用

Campus、Student、Teacher、Academic Class、Enrollment、Course、Chapter、Lesson、Problem、Judge Policy 等后台管理使用 Frappe Desk；API 客户端如确需通用 CRUD，可使用 `/api/resource/JWL%20Course` 等原生资源接口。敏感 DocType 同时应用角色权限和班级/校区查询条件。

## 验证

```bash
python -m unittest discover -s jwlcode/tests -v
python -m compileall -q jwlcode
```

完整的数据库与权限集成测试需要在安装了此 app 的 Frappe 测试站点中运行。
