# Docker Compose 运行说明

此配置用于本地开发和验收，运行当前仓库中的汉化版 Frappe Learning，不会重新下载官方 LMS 覆盖本地修改。Bench、站点和数据库均使用 Docker Volume 持久化。公开部署时应改用生产级 WSGI、反向代理和正式密码。

## 启动

首次克隆时包含 `frappe-ui` 子模块：

```bash
git clone --branch learning-cn --recurse-submodules \
  git@github.com:sheng063/JWLCode-frappe.git
cd JWLCode-frappe/docker
docker compose up -d
```

首次初始化需要下载 Frappe、Payments 和前端依赖，通常需要数分钟。查看进度：

```bash
docker compose logs -f frappe
```

容器健康后访问：

- 教学平台：http://school.localhost:8000/lms
- Frappe 后台：http://school.localhost:8000/app

默认管理员账号为 `Administrator`，密码为 `admin`。默认密码仅用于本机开发，公开部署前必须修改。

## 自定义配置

复制示例环境变量后修改：

```bash
cp .env.example .env
```

可配置站点域名、端口、数据库密码、管理员密码和 Frappe 分支。`.env` 已被 Git 忽略，不要提交真实密码。

## 常用命令

查看状态：

```bash
docker compose ps
```

查看初始化日志：

```bash
docker compose logs -f frappe
```

创建演示课程：

```bash
docker compose exec frappe runuser -u frappe -- bash -lc \
  "cd /home/frappe/bench-data/frappe-bench && /home/frappe/.local/bin/bench --site school.localhost execute lms.demo.demo_data.create_demo_data"
```

停止服务但保留数据：

```bash
docker compose down
```

完全清空本套教学平台的数据并重新初始化：

```bash
docker compose down --volumes
docker compose up -d
```

`down --volumes` 会永久删除本 Compose 项目的 MariaDB 和 Bench 数据，只应在确认需要重置时使用。
