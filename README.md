# JWLCode · 教学与编程练习平台

JWLCode-frappe 是基于 Frappe Learning 二次开发的教学平台，包含 Frappe 后端应用和 Vue 前端。围绕「课程 → 章节 → 课时」组织教学内容，提供班级管理、测验、作业、证书，以及 C++ / Python 编程练习、ICPC 题包管理和独立判题服务接入。

仓库中的 Python 包和 Bench 应用名为 `lms`，教学页面默认入口为 `/lms`。本仓库不是 Frappe Framework 本身；运行时需要 Frappe、Payments、MariaDB 和 Redis。编程判题还需要单独部署 `JWLCode-judge-service` 及其执行节点。

## 功能与模块

| 模块 | 当前能力 | 主要代码入口 |
| --- | --- | --- |
| 课程与课时 | 课程、章节、文本与编程课时；富文本、Markdown、公式、PDF、音视频及 SCORM 内容；学习进度 | [课程模型](lms/lms/doctype/lms_course/)、[课时模型](lms/lms/doctype/course_lesson/)、[课程页面](frontend/src/pages/Courses/) |
| 班级与课程访问 | 公开 / 非公开课程、班级课程注册同步、讲师仪表盘、课程完成度和编程题通过率 | [课程访问控制](lms/lms/course_access.py)、[注册同步](lms/lms/batch_enrollment_sync.py)、[班级统计](lms/lms/batch_progress.py) |
| 测验与作业 | 题目、测验、作业、提交记录、评分与测验违规记录 | [业务模型](lms/lms/doctype/)、[前端页面](frontend/src/pages/) |
| 编程练习 | C++ / Python 编辑、公开样例运行、正式提交、状态查询、隐藏用例和稳定题号 `P-000001` | [编程题模型](lms/lms/doctype/lms_programming_exercise/)、[判题接口](lms/lms/judge_service.py)、[编程页面](frontend/src/pages/ProgrammingExercises/) |
| 编程编辑器 | Ace 编辑器、主题和字体设置、草稿缓存、快捷键；Python 使用 Black、C++ 使用 clang-format 格式化 | [编辑器组件](frontend/src/components/Controls/CodeEditor.vue)、[格式化接口](lms/lms/programming_editor.py) |
| ICPC 题包 | 单题 / 批量导入、预检、草稿确认、版本发布、题面编辑、隐藏用例替换和批量导出 | [题包模块](lms/lms/problem_package/) |
| 课程迁移 | 课程 ZIP 导入导出，携带章节、课时、测评、附件和完整编程题包；按源 ID 重建引用 | [导入导出入口](lms/lms/course_import_export.py)、[课程包 v2](lms/lms/course_bundle.py) |
| 教学运营 | 学习项目、直播课、证书、徽章、支付、优惠券和统计；直播集成需单独配置 | [业务模型](lms/lms/doctype/)、[支付接口](lms/lms/payments.py) |
| 游戏与联机 | HTML / ZIP 上传、隔离运行、学生开关及课程解锁；通用 Colyseus 房间、匹配、私房与前端 SDK | [游戏模块](lms/lms/game.py)、[运行时](services/game-runtime/)、[联机说明](docs/game-colyseus.md) |
| 社区与扩展 | 讨论、通知、个人资料、职位；可选 Raven 成员规则集成 | [职位模块](lms/job/)、[Raven provider](lms/raven_provider.py) |
| 中文定制 | 中文品牌、简体中文翻译，新安装默认中文并允许手机号登录 | [安装钩子](lms/install.py)、[中文翻译](lms/locale/zh.po) |

手机号登录使用已有用户的手机号，并不代表已接入短信验证码服务。Raven 成员规则依赖额外的集成应用，不随本仓库的默认 Docker 配置安装。

## 架构与职责

```text
浏览器：Vue 教学页面（frontend/）
    │ Frappe API / 会话认证
    ▼
Frappe 应用：课程、权限、题库、提交、成绩与学习进度
    ├── MariaDB：业务数据
    ├── Redis + Worker：后台任务
    └── JWLCode-judge-service：判题请求与结果归一化
            └── Judge0：编译与执行学生代码
```

浏览器通过 Frappe 发起运行和提交，不直接访问 Judge0。正式提交先创建 `Queued` 记录，事务提交后由 `short` 队列分发给判题服务；结果通过 HMAC 签名回调写回，服务间查询提供兜底。题包异步预检使用 `long` 队列，因此两类队列都需要可用的 Worker。

## 仓库结构

```text
JWLCode-frappe/
├── lms/
│   ├── hooks.py                 # 生命周期、权限、路由、定时任务和扩展钩子
│   ├── install.py               # 安装初始化、角色及中文默认设置
│   ├── lms/
│   │   ├── api.py               # 教学业务 API
│   │   ├── doctype/             # 数据模型及控制器
│   │   ├── problem_package/     # 题包解析、导入、编辑、导出及权限
│   │   ├── judge_service.py     # 判题服务适配与回调
│   │   ├── course_bundle.py     # 课程包 v2 与事务导入
│   │   └── course_import_export.py
│   ├── job/                    # 职位模块
│   ├── patches/                # 数据迁移补丁
│   ├── locale/                 # gettext 翻译
│   ├── public/                 # 静态资源及前端构建输出
│   ├── www/                    # 网站入口
│   └── tests/                  # 后端回归、权限及安全测试
├── frontend/
│   ├── src/pages/              # 页面
│   ├── src/components/         # 教学、编辑器及管理组件
│   ├── src/utils/              # 内容处理、状态、偏好及公共逻辑
│   ├── src/tests/              # Vitest 测试
│   └── vite.config.js          # 开发代理与构建配置
├── frappe-ui/                  # Frappe UI 子模块
├── docker/                     # 本地 Compose、初始化及更新脚本
├── scripts/                    # 中文词条检查与 QA 工具
├── cypress/                    # 浏览器端到端测试
└── docs/                       # 功能、协议与验收文档
```

## 技术栈与环境

| 层次 | 仓库配置 |
| --- | --- |
| 后端 | Python、Frappe Framework、Payments；Python 包声明 `>=3.10` |
| 框架依赖 | `frappe >=14.0.0,<=17.0.0-dev`；`payments >=0.0.1,<1.0.0` |
| 前端 | Vue 3、TypeScript、Vite 5、Frappe UI、Tailwind CSS、Pinia |
| 内容与代码编辑 | Editor.js、Ace、KaTeX、PDF.js、Black、clang-format |
| 本地数据服务 | MariaDB 10.11、Redis 7（Compose 配置） |
| Node.js | 根目录要求 `>=22`，现有 CI 使用 Node.js 24；依赖通过 Yarn 安装 |
| 测试 | Frappe 测试运行器、Vitest、Cypress |

以上框架范围是 [pyproject.toml](pyproject.toml) 的依赖声明，不表示所有版本组合均经过验证。实际 Python / Node.js 环境还需满足所选 Frappe 分支的要求；本地 Docker 默认使用 Frappe 和 Payments 的 `develop` 分支。

## Release 下载与使用

当前发行版为 **v2026.10.17**，从 [GitHub Releases](https://github.com/sheng063/JWLCode-frappe/releases/latest) 下载 `JWLCode-frappe-v2026.10.17.tar.gz`（Linux / macOS）或同名 `.zip`（Windows），以及 `SHA256SUMS`。请选择命名为 `JWLCode-frappe-*` 的附件；`assets-main` 是滚动静态资源包，GitHub 自动提供的 Source code 则是完整仓库快照，均不等同于本节的精简发行包。

源码包保留后端、前端源码及静态资源、游戏与 SDK、部署脚本、文档和许可证；排除 Git 历史、依赖目录、Frappe UI 子模块、题库转换工作数据、Cypress 和 QA 日志截图。需要这些开发材料时，请克隆 `main` 分支。包内 `RELEASE.json` 记录发行版本和对应提交；日期发行号与上游 `lms.__version__` 分开管理。

### 下载、校验与解压

```bash
VERSION=v2026.10.17
BASE="https://github.com/sheng063/JWLCode-frappe/releases/download/$VERSION"
curl -fLO "$BASE/JWLCode-frappe-$VERSION.tar.gz"
curl -fLO "$BASE/SHA256SUMS"

# Linux：仅校验本次下载的 tar.gz
grep " JWLCode-frappe-$VERSION.tar.gz$" SHA256SUMS | sha256sum -c -
# macOS：将上一行的 sha256sum 换为 shasum -a 256

tar -xzf "JWLCode-frappe-$VERSION.tar.gz"
cd "JWLCode-frappe-$VERSION"
```

Windows 可用 PowerShell 的 `Get-FileHash .\JWLCode-frappe-v2026.10.17.zip -Algorithm SHA256` 与校验文件中的同名条目比对，再解压 ZIP；后续 Docker 命令在 WSL2 中执行。

### 从源码包首次启动

准备 Docker Compose 和 Git。发行包不带 `.git`；Bench 的本地应用导入需要 Git 仓库，因此先在解压目录初始化一次：

```bash
git init -b main
git add .
git -c user.name='Release Installer' -c user.email='release@localhost' \
  -c core.hooksPath=/dev/null commit -m '初始化 JWLCode 发行包'

cp docker/.env.example docker/.env
# 根据需要编辑 docker/.env 中的站点、端口和初始密码
docker compose -f docker/docker-compose.yml up -d
docker compose -f docker/docker-compose.yml logs -f frappe
```

初始化完成后访问 `http://school.localhost:8000/lms`，本地默认管理员为 `Administrator` / `admin`。发行包包含源码，不含预构建前端、数据库或依赖；首次启动仍需联网获取 Frappe、Payments、Python / Yarn 依赖并构建前端，无需初始化 Frappe UI 子模块。Compose 的用途与配置限制见下方“本地启动”。

### 升级已有 Docker 站点

先在原部署目录备份站点，并另行保存原 `docker/.env`：

```bash
docker compose -f docker/docker-compose.yml exec -T frappe \
  runuser -u frappe -- bash -lc \
  'cd /home/frappe/bench-data/frappe-bench && /home/frappe/.local/bin/bench --site school.localhost backup --with-files'
```

将生成的备份从 Bench Volume 复制到独立备份位置并确认可用。使用自定义站点时替换上述站点名。

将新版发行包解压至新目录，复制原 `docker/.env`，确保继续使用相同 Compose 项目名（默认 `jwl-learning`）和原数据库 / Bench Volume。停止旧目录的 Compose（`down`，不加 `--volumes`），在新目录执行 `bash docker/redeploy.sh`；自定义站点需使用 `SITE_NAME=your-site.localhost bash docker/redeploy.sh`。脚本会同步应用、重建前端并执行数据库迁移；包本身不含课程、用户、上传文件和数据库备份。已有 Bench 的更新请继续使用 Bench 的应用维护流程。

### 自行制作相同发行包

在 Git 仓库根目录执行（只需 Python 3 和 Git）：

```bash
python3 tools/build-release.py --version v2026.10.17 --ref HEAD
```

产物位于忽略提交的 `release-dist/`：tar.gz、zip 和 SHA256SUMS。打包读取指定提交，未提交修改不会进入包内。推送 `v20*` 日期标签后，[源码发布工作流](.github/workflows/source-release.yml) 会自动制作并上传 GitHub Release；发布说明需先保存到 `docs/releases/<标签>.md`。

## 本地启动

### Docker Compose

准备 Docker、Docker Compose 和 Git。在当前仓库根目录执行：

```bash
# 初始化 Frappe UI 子模块
git submodule update --init --recursive

# 首次配置时复制；已有 .env 时直接编辑
cp docker/.env.example docker/.env

docker compose -f docker/docker-compose.yml up -d
docker compose -f docker/docker-compose.yml logs -f frappe
```

初始化脚本会创建 Bench、获取 Frappe / Payments、导入本仓库源码，创建站点并安装应用。首次启动需要联网下载依赖；数据库和 Bench 保存在 Docker Volume 中。

默认访问地址：

- 教学平台：`http://school.localhost:8000/lms`
- Frappe 后台：`http://school.localhost:8000/app`
- 本地管理员：`Administrator` / `admin`

若 `school.localhost` 无法解析，在本机 hosts 中添加 `127.0.0.1 school.localhost`。使用自定义域名时，应与 `SITE_NAME` 一致。

| 环境变量 | 默认值 | 用途 |
| --- | --- | --- |
| `SITE_NAME` | `school.localhost` | Frappe 站点名 |
| `HTTP_PORT` | `8000` | 宿主机 HTTP 端口 |
| `SOCKETIO_PORT` | `9000` | 宿主机 Socket.IO 端口 |
| `DB_ROOT_PASSWORD` | `123` | 初始化数据库密码 |
| `ADMIN_PASSWORD` | `admin` | 新站点管理员密码 |
| `FRAPPE_BRANCH` / `PAYMENTS_BRANCH` | `develop` | 初始化使用的上游分支 |

修改初始化密码变量不会重置已有站点账号。当前脚本将站点 `host_name` 写为 `http://<SITE_NAME>:8000`；更改外部端口或域名后，也需核对站点 URL 和回调配置。

此 Compose 使用 `bench start` 和开发模式，用于本地开发与验收。生产部署需要另外配置正式凭据、HTTPS / 反向代理、生产进程管理、备份和判题执行节点隔离；默认 Compose 不包含 Judge Service 或 Judge0。

### 更新容器中的代码

本地仓库只读挂载到 `/workspace/lms`，运行代码位于容器内 `/home/frappe/bench-data/frappe-bench/apps/lms`。修改宿主机文件或重启容器不会自动更新已安装副本。在首次初始化完成后，从仓库根目录执行：

```bash
bash docker/redeploy.sh

# 自定义站点时显式指定，须与已创建的站点一致
SITE_NAME=your-site.localhost bash docker/redeploy.sh
```

脚本同步源码、安装 Python / 前端依赖、构建前端、编译翻译、执行迁移、清理缓存并重启 Frappe。它会更新运行中的本地站点。

停止服务并保留数据：

```bash
docker compose -f docker/docker-compose.yml down
```

更多操作见 [Docker 运行说明](docker-installation.md)。

### 已有 Bench 环境

在已配置好 MariaDB、Redis 和匹配运行时的 Bench 根目录执行。将路径替换为自己的本地仓库：

```bash
bench get-app payments
bench get-app lms /absolute/path/to/JWLCode-frappe
bench new-site school.localhost
bench --site school.localhost install-app payments
bench --site school.localhost install-app lms
bench use school.localhost
bench --site school.localhost set-config developer_mode 1
bench build --app lms
bench start
```

只需安装一次应用；已有站点不要重复执行 `new-site`。前端热更新开发可在另一个终端进入 Bench 中的 `apps/lms`：

```bash
cd apps/lms
yarn install
yarn dev
```

访问 Vite 输出的地址，并使用能够匹配 Frappe 站点的主机名。前端依赖运行中的后端；单独启动 Vite 不会提供课程数据或登录服务。开发配置优先加载本地 `frappe-ui/vite` 插件，失败时回退到 npm 包；生产构建使用 npm 包。

## 配置编程判题

先独立部署 `JWLCode-judge-service` 和 Judge0，并保证 Frappe 与判题服务双向可达。在 Frappe 后台打开 **LMS Judge Settings**：

| 字段 | 配置说明 |
| --- | --- |
| Enabled | 启用判题服务 |
| Judge Service URL | 判题服务地址，例如 `http://judge-service:8080`，须在实际网络中可解析 |
| Service API Token | 与判题服务的 `JUDGE_SERVICE_TOKEN` 一致 |
| Frappe Callback URL | 判题服务可达的 Frappe 地址，路径为 `/api/method/lms.lms.judge_service.judge_callback` |
| Callback Secret | 与判题服务的 `CALLBACK_SECRET` 一致，用于验签 |
| Request Timeout (seconds) | 请求超时配置，默认 15 秒；运行样例接口另有较长等待时间 |

在编程题中选择 `Evaluation Mode = Judge Service`，配置公开样例、隐藏用例及资源限制。当前服务端支持 C++ 和 Python；题目语言是默认编辑语言，同一道题允许使用两种语言提交。时间限制以 C++ 为基准，Python 使用两倍时间，内存限制不变。

公开样例运行不创建或覆盖正式提交；页面正式提交创建新的提交记录。隐藏测试数据通过服务端权限保护，成绩以服务端判题结果为准。

启用 ICPC 题包时，在 Bench 根目录执行：

```bash
bench --site school.localhost set-config enable_icpc_problem_packages 1
bench --site school.localhost clear-cache
```

同时需要判题服务开启相应 ICPC 能力。发布时会查询服务能力，核对协议、比较方式及输入、输出、内存容量；只打开站点开关不足以完成题包发布。

当前支持 legacy ICPC 的受限标准输入输出题型，不执行包内参考解或输入校验器，不支持自定义输出校验器及交互题。单题 ZIP / KPP 上限为 20 MiB，解压总量上限为 128 MiB；站点上传限制也会生效。完整配置和限制见下方专题文档。

## 游戏与通用联机

教师可在游戏库上传 HTML / ZIP 游戏，设置学生访问与课程 / 课时解锁规则。静态游戏随 LMS 运行；联机游戏另需部署固定的通用 Runtime。该服务负责房间、匹配、名单和消息中继，游戏规则由客户端维护。

在已运行的本地 Docker 站点上，准备 Node.js 22+ / npm 后执行：

```bash
npm --prefix services/game-runtime ci
python3 tools/deploy-universal-runtime.py --port 2572
```

部署脚本会构建并启动 Runtime / Nginx，写入站点联机配置；默认仅绑定本机。后续上传新游戏无需重建运行时。游戏制作、版本发布和权限边界见 [通用联机部署](docs/game-colyseus.md) 与 [前端 SDK](docs/game-multiplayer-sdk.md)。

## 开发与验证

前端命令在 `frontend/` 中运行：

```bash
yarn install --frozen-lockfile
yarn test
yarn build
```

构建产物写入 `lms/public/frontend/`，HTML 入口复制到 `lms/www/_lms.html`。Vitest 配置为 [frontend/vitest.config.ts](frontend/vitest.config.ts)，用例位于 `frontend/src/tests/`。现有专题验收文档记录过 Vite 5 / Vitest 4 的依赖兼容问题；若测试在加载配置阶段失败，应先核对实际安装版本，不能把启动失败当作业务用例失败。

后端测试需要已安装 `lms` 的独立测试站点。在 Bench 根目录执行：

```bash
bench --site test.localhost set-config allow_tests true
bench --site test.localhost run-tests --app lms

# 按模块执行，例如课程包回归
bench --site test.localhost run-tests --module lms.tests.test_course_bundle
```

根目录的 `yarn test-local` 启动 Cypress 交互测试。默认目标是 `http://pertest:8000`，使用其他测试站点时可通过 `CYPRESS_BASE_URL` 覆盖，并准备用例要求的用户及数据。CI 配置见 [.github/workflows/](.github/workflows/)。

## 专题文档

| 主题 | 文档 |
| --- | --- |
| 游戏上传与联机 | [游戏模块](docs/game.md)、[通用联机服务](docs/game-colyseus.md)、[前端 SDK](docs/game-multiplayer-sdk.md) |
| 中文设置与翻译 | [中文本地化](docs/LOCALIZATION_ZH_CN.md) |
| 课程权限和班级同步 | [课程可见性、班级注册与讲师仪表盘](docs/course-visibility-and-batch-enrollment.md) |
| 课程备份与迁移格式 | [课程 ZIP 格式 v2](docs/course-bundle-format.md) |
| 判题对接 | [Judge Service 接入](docs/judge-service.md)、[Apple Silicon 判题说明](docs/judge0-apple-silicon.md) |
| 编程编辑器 | [编辑器功能](docs/programming-editor.md)、[题目编辑与隐藏用例](docs/programming-exercise-editor.md) |
| 编程题号与容量 | [题号与 ICPC 导入](docs/programming-exercise-numbers-and-import.md) |
| ICPC 实现与边界 | [题包实现说明](docs/icpc-problem-package-implementation.md) |
| 批量迁移题库 | [单题与批量导入](docs/icpc-bulk-import.md)、[批量导出](docs/icpc-bulk-export.md) |

专题文档中的验收日期、题目数量及本地节点状态是对应时间的记录，不代表当前部署状态。运行行为以代码和实际配置为准，例如当前正式判题分发队列为 `short`。

## 上游与许可证

本项目基于 Frappe Learning；导入时的上游分支和提交记录见 [UPSTREAM.md](UPSTREAM.md)。该文件保留早期中文发行层说明，当前仓库还包含本文列出的教学与编程功能扩展。

项目遵循 **AGPL-3.0-or-later**，完整许可证见 [license.txt](license.txt)。
