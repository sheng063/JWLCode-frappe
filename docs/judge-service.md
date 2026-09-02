# Judge Service 接入

Frappe Learning 负责题目、课程权限、提交记录、成绩和进度；独立的
`JWLCode-judge-service` 负责 Judge0 请求、轮询和结果归一化。浏览器不直接访问 Judge0。

## 配置

完成 `bench --site <site> migrate` 后，在 Desk 打开 **LMS Judge Settings**：

- Enabled：启用服务端判题。
- Judge Service URL：例如 `http://judge-service:8080`。
- Service API Token：与 Judge Service 的 `JUDGE_SERVICE_TOKEN` 一致。
- Frappe Callback URL：Judge Service 可访问的内部地址，例如
  `http://frappe:8000/api/method/lms.lms.judge_service.judge_callback`。
- Callback Secret：与 Judge Service 的 `CALLBACK_SECRET` 一致。

在 **LMS Programming Exercise** 中选择 `Evaluation Mode = Judge Service`，配置语言、时间和内存限制。
原有 Test Cases 是学生可见样例；隐藏测试数据写入 **LMS Judge Test Case**，该 DocType 不授予学生读取权限。

## 提交流程

1. 学生页面调用 Frappe 创建 `Queued` 提交。
2. Frappe 长队列 Worker 将源码和测试数据发送给 Judge Service。
3. Judge Service 批量提交 Judge0，并持久化 token 与状态。
4. 完成后以 HMAC 签名回调 Frappe；前端轮询同时提供结果查询兜底。
5. Frappe 只使用签名回调或服务间查询结果更新成绩，不接受浏览器传入的 Passed/Failed。

生产环境应将 Frappe Worker、Judge Service 和 Judge0 放在受控内部网络，并确保学生代码执行节点不能访问业务数据库、Redis或 Docker Socket。

