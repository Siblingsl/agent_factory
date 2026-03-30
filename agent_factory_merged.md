# Agent Factory — 智能体工厂完整技术方案

> 技术框架：LangGraph 0.2+ | 角色来源：agency-agents（147角色 · 12部门）| 讨论范式：MiroFish启发 | LLM：Claude claude-opus-4-5
manus
---

## 0. 强制程序阻断基线（未通过即停止开发）

本节是本项目的**最高优先级约束**。任何实现、重构、优化、扩展都必须先满足本节；不满足时必须立即停止向下开发、停止交付，仅允许修复阻断项。

### 0.1 阻断原则（Hard Gate）

任意一条命中即 `BLOCKED`：

1. 产物中出现占位实现：`TODO`、`placeholder`、仅回显输入、伪调用。
2. README/Manifest 声明的能力在代码中没有真实实现路径（声明-实现不一致）。
3. 依赖安装失败、入口启动失败、运行时异常未处理。
4. 契约测试未通过（`invoke`、`manifest`、输入输出结构、超时/错误处理）。
5. 领域最小功能测试未通过（例如天气智能体未真实调用天气数据源）。
6. 沙箱验证失败或跳过验证且无人工批准记录。
7. 缺少交付证据（安装日志、测试报告、关键调用日志）。

### 0.2 交付判定（唯一放行条件）

只有以下条件全部为真时，才允许进入后续阶段或标记 `validation_passed=true`：

- `placeholder_scan == pass`
- `declaration_implementation_consistency == pass`
- `dependency_install == pass`
- `smoke_test == pass`
- `contract_tests == pass`
- `domain_tests == pass`
- `sandbox_verification == pass`
- `evidence_bundle_complete == true`

否则统一输出：

- `status: blocked`
- `validation_passed: false`
- `block_reasons: [...]`
- `next_action: fix_blockers_only`

### 0.3 Fallback 限制（防止“垃圾可运行壳”）

允许的 fallback：

- JSON 结构修复
- 同模型重试
- 备用模型重试

禁止的 fallback：

- 生成“通用聊天壳”冒充领域智能体
- 用模板代码绕过测试门禁
- 将失败标记为成功交付

### 0.4 执行指令（必须内置到流程）

主流程必须内置如下阻断逻辑：

```text
if any_hard_gate_failed:
    stop_pipeline()
    emit_block_report()
    forbid_delivery()
else:
    allow_next_stage_or_delivery()
```

### 0.5 有效性边界（必须明确）

引入程序阻断红线后，系统仍可能生成低质量代码，但这些代码必须被门禁拦截并标记为失败任务，**不得交付为可用智能体**。

必须遵循以下判定语义：

1. `生成失败` 是允许事件：表示门禁正常工作，不计为交付成功。
2. `垃圾交付` 是禁止事件：一旦出现，视为流程设计缺陷，必须优先修复门禁。
3. `无证据成功` 视为失败：若缺少安装日志/测试报告/运行证据，不得标记为通过。

### 0.6 自动化执行要求（CI 强制阻断）

本节红线不得仅存在于文档，必须落地为自动化检查并接入 CI/CD。至少包含：

1. 占位实现扫描（`TODO`、`placeholder`、回显模板、伪调用）。
2. 依赖安装与入口启动检查（按目标语言分别执行）。
3. 契约测试（`invoke`、`manifest`、错误处理、超时）。
4. 领域最小功能测试（每个智能体类型必须有可执行样例）。
5. 声明-实现一致性检查（README/Manifest 与代码路径一致）。
6. 沙箱验证与证据归档检查。

CI 放行规则必须是：

```text
if any_gate_failed:
    pipeline_status = "failed"
    release = "blocked"
else:
    pipeline_status = "passed"
    release = "allowed"
```

### 0.7 质量目标（用于验收）

为避免“看起来有门禁但仍持续漏检”，上线前必须满足以下目标：

1. 垃圾交付率 = 0（门禁开启后按发布批次统计）。
2. 门禁漏检率 < 1%（通过回归任务集抽检）。
3. 关键领域任务可用率达到约定阈值（例如天气类 > 95%）。

### 0.8 文档-代码一致性防漂移条款（强制）

本项目禁止出现“文档描述一套、代码实现另一套”的漂移。文档与代码必须保持同版本语义一致。

#### 0.8.1 漂移定义（命中即违规）

任一项成立即判定 `doc_code_drift = true`：

1. 文档声明为“必须实现/必须支持”的能力，在代码中不存在或不可执行。
2. 代码新增/修改了外部可见行为（接口、流程、目录模板、契约、门禁规则），但文档未同步更新。
3. 文档中的运行方式、配置项、文件结构与当前仓库实际行为不一致。

#### 0.8.2 合并前强制规则（PR Gate）

每个 PR 必须满足：

1. 若改动影响行为或契约，必须在**同一个 PR**更新对应文档章节。
2. PR 描述必须包含 `Doc Impact` 小节，明确：`none` / `updated` / `blocked`。
3. `Doc Impact != updated` 且检测到行为变化时，PR 直接阻断。
4. 任何“后补文档”的承诺默认无效，不允许先合代码再补文档。

#### 0.8.3 发布前强制规则（Release Gate）

发布前必须执行一致性检查并产出证据：

1. 接口与流程检查：文档列出的入口、阶段、中断点、返回字段与代码一致。
2. 目录模板检查：文档要求的必备文件在产物中存在且可用。
3. 运行说明检查：README 命令、环境变量、依赖管理与实际执行一致。
4. 契约检查：文档声明的 Runtime Contract 方法全部可执行通过。

若任一检查失败：

- `release = blocked`
- `doc_code_drift = true`
- 仅允许修复一致性问题，不允许继续开发新功能。

#### 0.8.4 例外机制（严格时限）

仅允许在紧急修复场景申请临时例外，且必须满足：

1. 记录 `drift_exception_id`、责任人、影响范围、回补截止时间。
2. 回补时限不超过 2 个工作日。
3. 超期未回补自动阻断后续发布。

### 0.9 功能完成度标注与自测强制条款（1%-100%）

本项目所有“功能项”在开发阶段必须显示完成度，并在功能标题处标注百分比；每完成一个功能必须立即执行自测并记录结果。

#### 0.9.1 标题标注格式（强制）

功能标题统一格式：

```text
### <功能名称> [完成度: XX%]
```

规则：

1. `XX` 取值范围必须为 `1-100` 的整数。
2. 未开始功能统一标注为 `0%`（仅允许在功能规划阶段出现）。
3. 进入开发阶段后，功能标题不得缺失完成度标注。
4. 历史章节未标注完成度，视为违规并阻断合并。

#### 0.9.2 完成度示例（参考口径）

1. `1%`：已建功能骨架，尚不可运行。
2. `30%`：核心路径已编码，未通过完整自测。
3. `60%`：主功能可运行，边界条件未覆盖完整。
4. `80%`：功能与异常分支基本完成，存在少量待验证项。
5. `100%`：通过全部自测与门禁，证据完整，可进入发布评审。

#### 0.9.3 每功能必测（自测）规则

每个功能从任意低状态推进到更高完成度时，必须执行一次对应自测并记录：

1. 自测命令（或测试脚本）；
2. 测试时间；
3. 测试结果（pass/fail）；
4. 失败原因与修复动作（如失败）；
5. 证据位置（日志路径/报告路径）。

禁止行为：

1. 只改百分比，不做自测。
2. 自测失败仍将完成度标注为 `100%`。
3. 无证据标注“已完成”。

#### 0.9.4 阻断条件（PR/Release 同时生效）

任一条件成立即阻断：

1. 功能标题缺少 `[完成度: XX%]`。
2. 完成度提升但无对应自测记录。
3. 自测为 fail 但完成度被标为 `100%`。
4. 完成度与实际状态不一致（抽检不通过）。

阻断输出：

```text
status = "blocked"
reason = "progress_or_selftest_violation"
action = "fix_and_retest"
```

#### 0.9.5 自测记录模板（必须落库/落文件）

```yaml
feature_id: F-XXX
feature_title: "<功能名称>"
progress: 1-100
self_test:
  command: "<测试命令>"
  executed_at: "YYYY-MM-DD HH:mm:ss"
  result: "pass|fail"
  report_path: "<日志或报告路径>"
  notes: "<失败原因/修复说明>"
```

### 0.10 项目创建后的首步限制操作（CI Gate Bootstrap，强制）

本条款用于确保团队在“开始写业务代码之前”先完成阻断机制落地。  
**未完成本节前，禁止进入功能开发。**

#### 0.10.1 执行时机（必须）

在仓库初始化后立即执行，顺序固定如下：

1. 创建项目仓库（或初始化本地仓库）；
2. 立即落地 CI Gate 基础设施（本节）；
3. 验证 Gate 在 PR 上可阻断；
4. Gate 验证通过后，才允许开始业务开发。

#### 0.10.2 必备文件（必须存在）

以下文件缺一不可：

1. `agent_factory/ci/run_gates.py`
2. `.github/workflows/ci-gate.yml`
3. `.github/pull_request_template.md`

#### 0.10.3 Gate 最小检查项（必须启用）

`run_gates.py` 至少执行以下检查：

1. 占位代码扫描（`TODO`、`placeholder`、仅回显输入等）。
2. 交付必备文件检查（按语言检查入口、依赖清单、README、配置）。
3. 声明-实现一致性检查（README/Manifest 声明能力必须有代码实现路径）。
4. 自测记录检查（完成度提升必须附带自测证据）。
5. 文档影响检查（PR 必须填写 `Doc Impact`，行为变化必须 `updated`）。

任一项失败必须 `exit(1)`，并输出失败原因。

#### 0.10.4 CI 工作流要求（必须阻断合并）

`ci-gate.yml` 必须在以下事件触发：

1. `pull_request`
2. `push` 到主分支

并强制执行：

1. 安装项目依赖；
2. 运行 `python agent_factory/ci/run_gates.py --strict`；
3. 将任务状态回传为必需检查项（Required Status Check）。

#### 0.10.5 分支保护要求（必须）

仓库分支保护策略必须开启：

1. 主分支禁止直接 push；
2. 必须通过 `ci-gate` 才允许 merge；
3. 至少 1 名 reviewer 审核通过；
4. Gate 失败时禁止管理员绕过（紧急例外走 0.8.4）。

#### 0.10.6 通过判定（项目可启动条件）

仅当以下全部满足，项目才算“可启动开发”：

1. 首个测试 PR 能触发 `ci-gate`；
2. 人为制造一个违规（例如加 `TODO`）可被 Gate 阻断；
3. 修复违规后 Gate 可恢复通过；
4. 分支保护已生效且不可绕过。

否则状态应标记为：

```text
project_status = "bootstrap_blocked"
next_action = "finish_ci_gate_bootstrap"
```

---

## 目录

1. [项目定位与核心理念](#1-项目定位与核心理念)
2. [系统整体架构](#2-系统整体架构)
   - [2.3 目标智能体语言选择](#23-目标智能体语言选择)
3. [角色注册表设计——完整12部门147角色](#3-角色注册表设计)
4. [智能角色选择算法](#4-智能角色选择算法)
5. [主控调度智能体（含反馈闭环）](#5-主控调度智能体)
6. [多轮讨论阶段（并行异步 DiscussionGraph）](#6-多轮讨论阶段)
7. [协作开发阶段](#7-协作开发阶段)
8. [沙箱策略（全层次设计）](#8-沙箱策略)
9. [成本控制与可观测性](#9-成本控制与可观测性)
10. [人机协作检查点](#10-人机协作检查点)
11. [LangGraph技术实现](#11-langgraph技术实现)
12. [智能体工具基础引擎（带调度智能）](#12-智能体工具基础引擎)
13. [交付系统（Runtime Contract）](#13-交付系统)
    - [13.6 语言感知打包器（LanguageAwarePackager）](#136-语言感知打包器)
14. [工程目录结构](#14-工程目录结构)
15. [推荐开发流程与注意事项](#15-推荐开发流程与注意事项)
16. [MVP最小可行实现方案](#16-mvp最小可行实现方案)
17. [核心模块代码实现建议（完整实现参考）](#17-核心模块代码实现建议完整实现参考)

---

## 1. 项目定位与核心理念

### 1.1 项目定义

Agent Factory 是一个**元智能体系统（Meta-Agent System）**，唯一职责是根据用户自然语言需求，自动组织 147 个专业角色中的最优子集，经过结构化讨论和分工协作，最终输出一个**可独立部署、功能完备的目标智能体**。

agency-agents 仓库包含 **147 个角色横跨 12 个部门**，并持续通过社区贡献增长。注册表设计必须具备**动态加载**和**版本跟踪**能力，通过 git submodule 自动同步新角色。

### 1.2 五大核心原则

**原则一：角色即节点（Role-as-Node）**  
147 个角色对应 LangGraph 图中的专业化节点，通过其 Markdown 系统提示词实例化，携带独立的专业知识、工作流程和交付物规范。

**原则二：讨论优于直接执行（Deliberation Before Execution）**  
借鉴 MiroFish 的群体智能范式：3～6 个被选角色先进行多轮结构化讨论，个体独立记忆 + 立场演化 + 仲裁收敛，输出技术规格书后再进入执行。

**原则三：沙箱即基础设施（Sandbox as Infrastructure）**  
四层沙箱分级强制执行：讨论隔离（进程级）→ 代码执行（容器级）→ 测试运行（容器级+网络模拟）→ 交付验证（VM级）。

**原则四：工具调度前置（ToolSelector-Driven Tool Engine）**  
出厂智能体预装 Skill、MCP 连接池、内置工具三层适配器；所有工具调用入口统一为 `ToolSelector`。Agent 不直接按工具名调用，必须先通过 `ToolSelector` 形成可解释的执行计划（含 Fallback 链），再由 `FallbackAwareToolExecutor` 执行。

**原则五：动态注册表 + 成本感知（Dynamic Registry + Cost Awareness）**  
注册表支持热更新，每次生产任务启动前先进行**成本与时间预估**，提供 Fast/Standard/Thorough 三种质量档位供用户选择。

**原则六：语言灵活性（Language Flexibility）**  
生成的目标智能体支持 **Python** 和 **Node.js** 两种运行时，由用户在需求输入阶段自主选择（或由 IntakeAgent 从需求描述中自动推断后经用户确认）。无论选择哪种语言，工厂都保证：自动生成对应的依赖清单（`requirements.txt` / `package.json`）、在沙箱内完成依赖安装验证、Dockerfile 使用正确的基础镜像、README 提供语言对应的快速上手命令。

---

## 2. 系统整体架构

### 2.1 架构分层

```
┌─────────────────────────────────────────────────────────────────┐
│                          用户交互层                              │
│   自然语言输入 + 语言偏好(Python/Node.js) →                      │
│   Web UI / CLI / API / WebSocket实时推送                        │
└───────────────────────────────┬─────────────────────────────────┘
                                │
          ┌─────────────────────▼─────────────────────┐
          │  [检查点1] 需求确认 + 语言选择 (人机协作)    │
          └─────────────────────┬─────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│                    解析与调度层                                   │
│  IntakeAgent → DomainRouter → MasterDispatcherV3                │
│                     ↕ 双向查询 ↕                                 │
│         AgentRegistry (147角色 · 动态加载 · git-sync)           │
│         AgentTemplateCache (常见类型缓存)                        │
│         CostEstimator (任务前成本预估)                           │
└──────────────┬──────────────────────────────────┬──────────────┘
               │                                  │
┌──────────────▼──────────┐          ┌────────────▼──────────────┐
│  阶段一：讨论层 (沙箱A)  │          │   [可选] Fast模式:跳过     │
│  DiscussionGraph v3     │          │   直接进入开发阶段         │
│  3～6角色 · N轮 · 仲裁   │          └───────────────────────────┘
│  → 输出 TechSpec        │
└──────────────┬──────────┘
               │
    ┌──────────▼──────────────────┐
    │ [检查点2] 技术规格书审查     │
    │ (人机协作，可编辑/拒绝)      │
    └──────────┬──────────────────┘
               │
┌──────────────▼──────────────────────────────────────────────────┐
│                    阶段二：执行层 (沙箱B+C)                       │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐ │
│  │  并行开发节点集群  │  │  测试节点集群     │  │ MCP Builder  │ │
│  │  (按领域分流)     │  │  (5类测试并行)   │  │  (工具配置)   │ │
│  └──────────────────┘  └──────────────────┘  └───────────────┘ │
│                                                                  │
│  Quality Gate → [失败] → 分类修复路由 (最多3次重试)              │
│  Quality Gate → [通过] → 打包                                    │
└──────────────────────────────────────┬──────────────────────────┘
                                       │
                           ┌───────────▼────────────────┐
                           │  [检查点3] 交付预览          │
                           │  (人机协作，最终确认)        │
                           └───────────┬────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────┐
│                   打包 & 交付层 (沙箱D验证)                       │
│   PackagingNode → DeliveryNode → ValidationSandbox              │
│   输出：独立智能体包 + 教程 + MCP配置 + 验证报告                 │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 执行档位

| 档位 | 适用场景 | 流程 | 预估耗时 | 预估费用 |
|------|---------|------|---------|---------|
| **Fast** | 简单工具代理、单功能bot | 跳过讨论 → 直接开发 → 基础测试 | 5-15分钟 | 低 |
| **Standard** | 中等复杂度、多工具代理 | 2-3轮讨论 → 开发 → 完整测试 | 30-60分钟 | 中 |
| **Thorough** | 复杂系统、领域专用代理 | 4-6轮讨论+仲裁 → 并行开发 → 全测试套件 | 2-4小时 | 高 |

### 2.3 目标智能体语言选择

用户在发起任务时可指定生成的目标智能体使用 **Python** 还是 **Node.js** 作为运行时。这一选择贯穿开发、测试、打包、交付的全流程。

#### 2.3.1 语言选择策略

| 策略 | 说明 |
|------|------|
| **用户显式指定** | 请求中含 `"language": "python"` 或 `"language": "nodejs"` 字段，直接采用 |
| **自动推断** | IntakeAgent 从需求描述中提取语言信号（关键词：`TypeScript/JavaScript/npm/express` → Node.js；`pip/pandas/langchain/flask` → Python），推断结果在检查点1展示给用户确认 |
| **无法推断时** | 检查点1强制要求用户选择，不提供默认值，避免生成错误运行时的代码 |

#### 2.3.2 两种语言的差异矩阵

| 维度 | Python | Node.js |
|------|--------|---------|
| **依赖清单** | `requirements.txt`（pip） | `package.json` + `package-lock.json`（npm/yarn） |
| **依赖安装命令** | `pip install -r requirements.txt` | `npm install` |
| **主入口文件** | `agent.py` | `agent.js` / `agent.ts` |
| **LLM SDK** | `langchain-anthropic` / `anthropic` | `@anthropic-ai/sdk` / `langchain` |
| **Docker基础镜像** | `python:3.12-slim` | `node:20-slim` |
| **异步模型** | `asyncio` + `async/await` | `Promise` + `async/await` |
| **运行命令** | `python agent.py` | `node agent.js` / `tsx agent.ts` |
| **测试框架** | `pytest` | `jest` / `vitest` |
| **环境变量** | `python-dotenv` | `dotenv` |

#### 2.3.3 语言感知的代码生成

开发角色节点在收到 TechSpec 时，同时接收 `target_language` 字段，所有代码生成提示词包含语言约束：

```python
LANGUAGE_CODEGEN_ADDON = {
    "python": """
## 语言约束
- 使用 Python 3.12+，async/await + asyncio
- 依赖管理：requirements.txt（固定版本号，例如 anthropic==0.40.0）
- LLM调用：优先使用 langchain-anthropic 或 anthropic SDK
- 代码风格：类型注解 + dataclass，遵循 PEP 8
- 测试框架：pytest + pytest-asyncio
""",
    "nodejs": """
## 语言约束
- 使用 Node.js 20+ LTS，TypeScript优先（tsconfig.json需生成）
- 依赖管理：package.json（锁定版本，包含 dependencies 和 devDependencies）
- LLM调用：优先使用 @anthropic-ai/sdk 或 langchain
- 代码风格：ESModule（import/export），接口用 interface 定义
- 测试框架：jest 或 vitest
- 运行脚本：package.json scripts 必须包含 start、test、build
"""
}
```

---

## 3. 角色注册表设计——完整12部门147角色

> **数据来源说明**：以下角色清单综合自 agency-agents 官方 README、DeepWiki文档、社区文章等多个公开来源，与仓库实际文件结构一致。仓库持续更新，以实际 git clone 内容为准，注册表加载器负责动态发现所有 `.md` 文件。

### 3.1 目录结构（12个部门文件夹）

```
agency-agents/
├── engineering/          # ~21个角色
├── design/               # 8个角色
├── marketing/            # ~14个角色
├── paid-media/           # 独立付费媒体子部门（合并入Marketing统计）
├── sales/                # 8个角色
├── product/              # 5个角色
├── project-management/   # 6个角色
├── testing/              # 8个角色
├── support/              # 6个角色
├── spatial-computing/    # 6个角色
├── specialized/          # 30+个角色
├── game-development/     # 20+个角色
└── academic/             # 5个角色
```

---

### 3.2 部门一：Engineering（工程部）～21个角色

| 角色名（英文） | 角色名（中文） | 讨论 | 开发 | 测试 | 交付 | 工厂特殊说明 |
|-------------|-------------|:---:|:---:|:---:|:---:|------------|
| Frontend Developer | 前端开发者 | | ✅ | | | |
| Backend Architect | 后端架构师 | ✅ | ✅ | | | **必选讨论角色** |
| Mobile App Builder | 移动应用构建者 | | ✅ | | | 仅当目标代理需移动端 |
| AI Engineer | AI工程师 | ✅ | ✅ | | | **必选讨论角色** |
| DevOps Automator | DevOps自动化工程师 | | ✅ | | ✅ | |
| Rapid Prototyper | 快速原型工程师 | | ✅ | | | Fast档位优选 |
| Senior Developer | 高级开发者 | ✅ | ✅ | | | **全档位必选讨论** |
| Security Engineer | 安全工程师 | ✅ | | ✅ | | 安全相关必选 |
| Autonomous Optimization Architect | 自主优化架构师 | ✅ | | | | |
| Embedded Firmware Engineer | 嵌入式固件工程师 | | ✅ | | | IoT代理专用 |
| Incident Response Commander | 事件响应指挥官 | ✅ | | | | 高可用性需求 |
| Solidity Smart Contract Engineer | Solidity智能合约工程师 | | ✅ | | | Web3代理专用 |
| Technical Writer | 技术文档撰写者 | | | | ✅ | 文档生成必选 |
| Threat Detection Engineer | 威胁检测工程师 | ✅ | | ✅ | | |
| Code Reviewer | 代码审查者 | | | ✅ | | 测试阶段补充 |
| Database Optimizer | 数据库优化师 | ✅ | ✅ | | | 数据密集型代理 |
| Git Workflow Master | Git工作流专家 | | | | ✅ | 交付版本管理 |
| Software Architect | 软件架构师 | ✅ | | | | 复杂系统讨论 |
| Site Reliability Engineer | 站点可靠性工程师 | | | ✅ | | |
| AI Data Remediation Engineer | AI数据修复工程师 | | ✅ | | | RAG代理专用 |
| Data Engineer | 数据工程师 | | ✅ | | | 数据管道代理 |

### 3.3 部门二：Design（设计部）8个角色

| 角色名（英文） | 角色名（中文） | 讨论 | 开发 | 测试 | 交付 |
|-------------|-------------|:---:|:---:|:---:|:---:|
| UI Designer | UI设计师 | ✅ | ✅ | | |
| UX Researcher | 用户体验研究员 | ✅ | | | |
| UX Architect | 用户体验架构师 | ✅ | | | |
| Brand Guardian | 品牌守护者 | ✅ | | | ✅ |
| Visual Storyteller | 视觉叙事师 | | ✅ | | ✅ |
| Whimsy Injector | 趣味注入者 | | ✅ | | |
| Image Prompt Engineer | 图像提示词工程师 | | ✅ | | |
| Inclusive Visuals Specialist | 无障碍视觉专家 | | | ✅ | |

### 3.4 部门三：Marketing（市场部）～14个角色

| 角色名（英文） | 角色名（中文） | 讨论 | 开发 | 测试 | 交付 |
|-------------|-------------|:---:|:---:|:---:|:---:|
| Growth Hacker | 增长黑客 | ✅ | | | |
| Content Creator | 内容创作者 | | | | ✅ |
| Twitter Engager | 推特互动专家 | | | | ✅ |
| TikTok Strategist | TikTok策略师 | | | | ✅ |
| Instagram Curator | Instagram策划师 | | | | ✅ |
| Reddit Community Builder | Reddit社区建设者 | | | | ✅ |
| App Store Optimizer | 应用商店优化师 | | | | ✅ |
| Social Media Strategist | 社交媒体策略师 | ✅ | | | |
| LinkedIn Content Creator | 领英内容创作者 | | | | ✅ |
| SEO Specialist | SEO专家 | ✅ | | | ✅ |
| Podcast Strategist | 播客策略师 | | | | ✅ |
| Book Co-Author | 共同作者 | | | | ✅ |
| AI Citation Strategist | AI引用策略师 | | | | ✅ |
| Cross-Border E-Commerce Specialist | 跨境电商专家 | | | | ✅ |

### 3.5 部门四：Sales（销售部）8个角色

| 角色名（英文） | 角色名（中文） | 讨论 | 开发 | 测试 | 交付 |
|-------------|-------------|:---:|:---:|:---:|:---:|
| Outbound Strategist | 外向销售策略师 | ✅ | | | |
| Discovery Coach | 发现教练 | ✅ | | | |
| Deal Strategist | 交易策略师 | ✅ | | | |
| Sales Engineer | 销售工程师 | ✅ | | | |
| Proposal Strategist | 提案策略师 | | | | ✅ |
| Pipeline Analyst | 管道分析师 | | | | ✅ |
| Account Strategist | 客户策略师 | | | | ✅ |
| Sales Coach | 销售教练 | | | | ✅ |

> 工厂应用场景：当目标智能体是"销售辅助代理"或"CRM集成代理"时，Sales部门角色参与需求讨论阶段，提供真实业务场景约束。

### 3.6 部门五：Product（产品部）5个角色

| 角色名（英文） | 角色名（中文） | 讨论 | 开发 | 测试 | 交付 |
|-------------|-------------|:---:|:---:|:---:|:---:|
| Sprint Prioritizer | 冲刺优先级规划师 | ✅ | | | |
| Trend Researcher | 趋势研究员 | ✅ | | | |
| Feedback Synthesizer | 反馈综合师 | ✅ | | | ✅ |
| Behavioral Nudge Engine | 行为引导引擎 | ✅ | | | |
| Product Manager | 产品经理 | ✅ | | | |

### 3.7 部门六：Project Management（项目管理部）6个角色

| 角色名（英文） | 角色名（中文） | 讨论 | 开发 | 测试 | 交付 |
|-------------|-------------|:---:|:---:|:---:|:---:|
| Studio Producer | 工作室制作人 | ✅ | | | ✅ |
| Project Shepherd | 项目牧羊人 | ✅ | ✅ | ✅ | ✅ |
| Studio Operations Manager | 工作室运营经理 | | | | ✅ |
| Experiment Tracker | 实验追踪者 | | | ✅ | |
| Senior Project Manager | 高级项目经理 | ✅ | | | ✅ |
| Jira Workflow Steward | Jira工作流管家 | | | | ✅ |

### 3.8 部门七：Testing（测试部）8个角色

| 角色名（英文） | 角色名（中文） | 讨论 | 开发 | 测试 | 交付 |
|-------------|-------------|:---:|:---:|:---:|:---:|
| Evidence Collector | 证据收集者 | | | ✅ | |
| Reality Checker | 现实检验者 | | | ✅ | ✅ |
| Test Results Analyzer | 测试结果分析师 | | | ✅ | |
| Performance Benchmarker | 性能基准测试者 | | | ✅ | |
| API Tester | API测试者 | | | ✅ | |
| Tool Evaluator | 工具评估者 | ✅ | | ✅ | |
| Workflow Optimizer | 工作流优化师 | ✅ | | | |
| Accessibility Auditor | 无障碍审计者 | | | ✅ | |

> **重要修正**：Reality Checker 在工厂中扮演 Quality Gatekeeper 角色，负责最终放行决策。

### 3.9 部门八：Support（支持部）6个角色

| 角色名（英文） | 角色名（中文） | 讨论 | 开发 | 测试 | 交付 |
|-------------|-------------|:---:|:---:|:---:|:---:|
| Support Responder | 支持响应者 | ✅ | | | ✅ |
| Analytics Reporter | 分析报告员 | | | | ✅ |
| Legal Compliance | 法律合规专员 | ✅ | | | |
| Customer Success Manager | 客户成功经理 | ✅ | | | ✅ |
| Finance Analyst | 财务分析师 | ✅ | | | |
| Executive Reporter | 执行汇报者 | | | | ✅ |

### 3.10 部门九：Spatial Computing（空间计算部）6个角色

| 角色名（英文） | 角色名（中文） | 讨论 | 开发 | 测试 | 交付 |
|-------------|-------------|:---:|:---:|:---:|:---:|
| XR Interface Architect | XR界面架构师 | ✅ | ✅ | | |
| visionOS Engineer | visionOS工程师 | | ✅ | | |
| Metal Developer | Metal图形开发者 | | ✅ | | |
| WebXR Specialist | WebXR专家 | | ✅ | | |
| Spatial UX Designer | 空间UX设计师 | ✅ | | | |
| AR Content Strategist | AR内容策略师 | ✅ | | | ✅ |

> 工厂应用场景：当目标智能体服务于 Vision Pro、AR/VR 平台时，DomainRouter 自动引入此部门角色。

### 3.11 部门十：Specialized（专业化部）30+个角色

> 这是仓库中最大且最复杂的部门，包含多个子系统类别。

| 角色名（英文） | 角色名（中文） | 讨论 | 开发 | 测试 | 交付 | 重要性 |
|-------------|-------------|:---:|:---:|:---:|:---:|-------|
| **MCP Builder** | **MCP服务器构建者** | | ✅ | | | ⭐⭐⭐ 工厂核心角色 |
| Agentic Identity Architect | 智能体身份架构师 | ✅ | | | | ⭐⭐ 每次必选讨论 |
| Blockchain Auditor | 区块链审计者 | | | ✅ | | Web3专用 |
| Compliance Auditor | 合规审计者 | ✅ | | ✅ | | |
| ZK Steward | 零知识存储管理者 | | ✅ | | | |
| Automation Governance | 自动化治理专家 | ✅ | | | | |
| AI Data Remediation | AI数据修复专家 | | ✅ | | | RAG/向量DB代理 |
| Chinese Marketing Stack | 中文市场专家 | | | | ✅ | 中国市场代理 |
| Content Production System | 内容生产系统专家 | | ✅ | | | |
| Enterprise Integration Specialist | 企业集成专家(飞书/Lark) | | ✅ | | | 企业代理 |
| Identity & Trust Architect | 身份信任架构师 | ✅ | | | | |
| Reality Checker (Specialized) | 专业级现实检验者 | | | ✅ | ✅ | |
| ... (社区贡献角色，动态加载) | ... | — | — | — | — | 按能力标签自动分类 |

### 3.12 部门十一：Game Development（游戏开发部）20+个角色

| 角色名（英文） | 角色名（中文） | 讨论 | 开发 | 测试 | 交付 |
|-------------|-------------|:---:|:---:|:---:|:---:|
| Unity Architect | Unity架构师 | ✅ | ✅ | | |
| Unreal Systems Designer | 虚幻引擎系统设计师 | ✅ | ✅ | | |
| Godot Scripter | Godot脚本开发者 | | ✅ | | |
| Roblox Developer | Roblox开发者 | | ✅ | | |
| Blender Addon Engineer | Blender插件工程师 | | ✅ | | |
| Game Designer | 游戏设计师 | ✅ | | | |
| Narrative Designer | 叙事设计师 | ✅ | | | ✅ |
| Level Designer | 关卡设计师 | | ✅ | | |
| Game QA Tester | 游戏QA测试者 | | | ✅ | |
| Shader Engineer | 着色器工程师 | | ✅ | | |
| Audio Engineer | 音频工程师 | | ✅ | | |
| Mobile Game Developer | 移动游戏开发者 | | ✅ | | |
| Multiplayer Systems Engineer | 多人游戏系统工程师 | | ✅ | | |
| Economy Designer | 经济系统设计师 | ✅ | | | |
| UI/UX for Games | 游戏UI/UX设计师 | | ✅ | | |
| AI NPC Programmer | AI NPC编程者 | | ✅ | | |
| Performance Optimizer (Games) | 游戏性能优化师 | | | ✅ | |
| Localization Engineer | 本地化工程师 | | | | ✅ |
| Analytics (Games) | 游戏数据分析师 | | | | ✅ |
| Community Manager (Games) | 游戏社区经理 | | | | ✅ |

> 工厂应用场景：当目标智能体服务于游戏开发领域（AI NPC、游戏测试代理、剧情生成代理），DomainRouter 优先引入此部门。

### 3.13 部门十二：Academic（学术部）5个角色

| 角色名（英文） | 角色名（中文） | 讨论 | 开发 | 测试 | 交付 |
|-------------|-------------|:---:|:---:|:---:|:---:|
| Anthropologist | 人类学家 | ✅ | | | |
| Historian | 历史学家 | ✅ | | | |
| Psychologist | 心理学家 | ✅ | | | |
| Narratologist | 叙事学家 | ✅ | | | ✅ |
| Epistemologist | 认识论学家 | ✅ | | | |

> 工厂应用场景：当目标智能体需要文化理解、叙事能力或学术推理（如教育代理、研究辅助代理），Academic 角色参与讨论，提供深度人文视角。

### 3.14 动态注册表加载器（v2.0核心升级）

```python
# agent_factory/registry/loader.py

import subprocess
from pathlib import Path
from typing import Dict, List, Optional
import frontmatter
import yaml

# 12个部门目录（含paid-media，统计时归入marketing）
DIVISION_DIRS = [
    "engineering", "design", "marketing", "paid-media",
    "sales", "product", "project-management", "testing",
    "support", "spatial-computing", "specialized",
    "game-development", "academic"
]

# 默认部门归属（paid-media → marketing统计）
DIR_TO_DIVISION = {
    "engineering": Division.ENGINEERING,
    "design": Division.DESIGN,
    "marketing": Division.MARKETING,
    "paid-media": Division.MARKETING,  # 归入市场部统计
    "sales": Division.SALES,
    "product": Division.PRODUCT,
    "project-management": Division.PROJECT_MANAGEMENT,
    "testing": Division.TESTING,
    "support": Division.SUPPORT,
    "spatial-computing": Division.SPATIAL_COMPUTING,
    "specialized": Division.SPECIALIZED,
    "game-development": Division.GAME_DEVELOPMENT,
    "academic": Division.ACADEMIC,
}

# 必须参与讨论的角色（强制规则）
MANDATORY_DISCUSSION_ROLES = {
    "senior-developer",           # 架构把关
    "ai-engineer",                # AI技术选型
    "sprint-prioritizer",         # 需求拆解
    "agentic-identity-architect", # 智能体身份设计（Specialized部门）
}

# MCP Builder：当目标代理需要外部工具时强制参与开发阶段
MANDATORY_WHEN_TOOLS_NEEDED = {"mcp-builder"}

class AgentRegistry:
    """
    动态注册表核心功能：
    1. 从 git submodule 动态加载所有角色（不依赖硬编码列表）
    2. 支持后台定期 git-sync，新角色自动注册
    3. 从 frontmatter + body 自动推断能力标签和适用阶段
    4. 为社区贡献的新角色提供合理的默认分类
    """

    def __init__(self, repo_path: Path, auto_sync: bool = False):
        self.repo_path = repo_path
        self._agents: Dict[str, AgentMeta] = {}
        self._version_hash: str = ""
        self._load_all()
        if auto_sync:
            self._start_background_sync()

    def _load_all(self):
        """扫描所有12个部门目录，动态发现角色"""
        self._agents.clear()
        for division_dir in DIVISION_DIRS:
            division_path = self.repo_path / division_dir
            if not division_path.exists():
                continue
            division = DIR_TO_DIVISION[division_dir]
            for md_file in division_path.rglob("*.md"):
                if md_file.name.startswith("_") or md_file.name == "README.md":
                    continue
                meta = self._parse_agent_file(md_file, division)
                if meta:
                    self._agents[meta.slug] = meta

        # 记录当前版本哈希
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.repo_path, capture_output=True, text=True
        )
        self._version_hash = result.stdout.strip()

    def _parse_agent_file(self, path: Path, division: Division) -> Optional[AgentMeta]:
        """
        从 Markdown 文件解析角色元数据。
        能力标签和适用阶段通过 body 关键词分析自动推断，
        可通过可选的 factory_config.yaml 覆盖。
        """
        try:
            post = frontmatter.load(path)
        except Exception:
            return None

        slug = path.stem  # 文件名即 slug
        fm = post.metadata
        body = post.content

        # 从 body 自动推断能力标签
        capability = self._infer_capability(body, slug, division)
        # 推断工厂阶段（可被 factory_config.yaml 覆盖）
        phases = self._infer_phases(slug, division, capability)
        
        return AgentMeta(
            slug=slug,
            name=fm.get("name", slug.replace("-", " ").title()),
            description=fm.get("description", ""),
            color=fm.get("color", "gray"),
            emoji=fm.get("emoji", "🤖"),
            vibe=fm.get("vibe", ""),
            division=division,
            services=fm.get("services", []),
            system_prompt=body,
            capability=capability,
            factory_phases=phases,
            is_mandatory_discussion=(slug in MANDATORY_DISCUSSION_ROLES),
            is_mandatory_when_tools=(slug in MANDATORY_WHEN_TOOLS_NEEDED),
        )

    def sync_from_remote(self):
        """拉取最新角色（后台定期调用，不影响运行中任务）"""
        subprocess.run(["git", "pull", "origin", "main"], cwd=self.repo_path)
        old_count = len(self._agents)
        self._load_all()
        new_count = len(self._agents)
        if new_count > old_count:
            logger.info(f"AgentRegistry 更新：新增 {new_count - old_count} 个角色")
```

---

## 4. 智能角色选择算法

### 4.1 三层选择机制

面对 147 个角色，单纯的关键词匹配远远不够。系统采用三层递进的选择机制：

**第一层：DomainRouter（领域路由）**  
在主调度前进行领域预判，识别任务的一级领域（游戏/XR/Web3/企业/通用等），预先锁定对应部门的角色池，大幅缩小搜索空间。

```python
class DomainRouter:
    """
    根据 AgentSpec 的领域特征，预先筛选相关部门。
    输出：缩小后的候选角色池（通常从147降到20-30个）
    """
    
    DOMAIN_SIGNALS = {
        "game": [Division.GAME_DEVELOPMENT, Division.SPECIALIZED],
        "xr": [Division.SPATIAL_COMPUTING, Division.ENGINEERING],
        "web3": [Division.ENGINEERING, Division.SPECIALIZED],  # Solidity等
        "enterprise": [Division.SUPPORT, Division.SPECIALIZED, Division.ENGINEERING],
        "mobile": [Division.ENGINEERING, Division.DESIGN],
        "data": [Division.ENGINEERING, Division.SPECIALIZED],
        "marketing": [Division.MARKETING, Division.SALES, Division.PRODUCT],
        "general": "all",  # 不做限制
    }
    
    def route(self, spec: AgentSpec) -> List[Division]:
        """返回与任务相关的部门列表"""
        detected_domain = self._detect_domain(spec)
        divisions = self.DOMAIN_SIGNALS.get(detected_domain, "all")
        # 核心部门（工程/产品/项目管理/测试）始终包含
        core_divisions = [Division.ENGINEERING, Division.PRODUCT,
                          Division.PROJECT_MANAGEMENT, Division.TESTING]
        if divisions == "all":
            return list(Division)
        return list(set(divisions + core_divisions))
```

**第二层：语义向量匹配**  
对缩小后的候选角色集，计算 `AgentSpec` 需求向量与每个角色 `capability.domains` 向量的余弦相似度，排序得分。

**第三层：平衡性校验 + 强制规则**  
确保选出的讨论团队满足：
- 技术视角：至少1个工程角色（Senior Developer 强制）
- 产品视角：至少1个产品/项目管理角色（Sprint Prioritizer 强制）  
- AI视角：当目标是AI代理时强制含 AI Engineer
- 身份视角：Agentic Identity Architect 永远参与（为目标代理设计身份）
- 安全视角：Security Engineer 可选，含敏感数据时强制

### 4.2 讨论团队规模控制

| 档位 | 讨论团队规模 | 讨论轮次 |
|------|------------|---------|
| Fast | 0（跳过） | 0 |
| Standard | 3～4人 | 2～3轮 |
| Thorough | 5～6人 | 4～6轮 |

> 超过6人的讨论在实验中证明会导致观点碎片化和收敛困难，不建议超过此上限。

---

## 5. 主控调度智能体（含反馈闭环）

### 5.0 问题本质

传统调度器是**无状态的决策器**：

```
每次任务 → 规则 + LLM → 决策
                ↑
         不存在历史信息
```

这意味着：某个角色组合在过去 20 次任务里成功率 30%，调度器对此一无所知；某个组合成本是另一个的 3 倍，调度器照样选它；Quality Gate 失败是哪个角色的问题，调度器不追溯。

修复目标：**让调度器在每次生产任务完成后学习，下次做更好的决策。**

> **替换声明**：`MasterDispatcherV2` 在 v2.1 中仅作为兼容基类保留；生产态默认调度器为 `MasterDispatcherV3`。

---

### 5.1 反馈数据模型

```python
# agent_factory/dispatcher/feedback_store.py

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime
import hashlib, json

@dataclass
class DispatchOutcome:
    """
    单次生产任务完成后写入的反馈记录。
    这是反馈闭环的原始数据单元。
    """
    # ── 身份标识
    session_id: str
    timestamp: datetime

    # ── 输入特征（用于相似任务检索）
    domain: str
    agent_type: str
    spec_embedding: List[float]          # 768维需求向量，用于相似度检索

    # ── 调度决策（被评估的对象）
    discussion_team: List[str]
    dev_team_assignments: Dict[str, List[str]]
    execution_mode: str
    combination_hash: str                # sha256(sorted(discussion_team))[:16]

    # ── 结果指标（反馈信号）
    overall_success: bool
    quality_score: float                 # 0~1，由 Reality Checker 评分
    test_coverage: float
    quality_gate_attempts: int

    # ── 成本指标
    actual_token_usage: int
    actual_duration_minutes: float
    estimated_token_usage: int

    # ── 失败分析
    failure_types: List[str]
    failure_roles: List[str]
    discussion_convergence_rounds: int

    # ── 用户满意度（可选）
    user_rating: Optional[int] = None
    user_feedback_text: Optional[str] = None

    @classmethod
    def compute_combination_hash(cls, slugs: List[str]) -> str:
        """角色组合的确定性指纹，顺序无关"""
        return hashlib.sha256(
            json.dumps(sorted(slugs)).encode()
        ).hexdigest()[:16]


class DispatchOutcomeStore:
    """
    持久化存储所有生产任务的反馈记录。
    使用 PostgreSQL + pgvector 支持语义相似度检索。
    """

    CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS dispatch_outcomes (
        id              SERIAL PRIMARY KEY,
        session_id      TEXT NOT NULL,
        timestamp       TIMESTAMPTZ DEFAULT NOW(),
        domain          TEXT,
        agent_type      TEXT,
        spec_embedding  vector(768),
        combination_hash TEXT,
        discussion_team JSONB,
        dev_team        JSONB,
        execution_mode  TEXT,
        overall_success BOOLEAN,
        quality_score   FLOAT,
        test_coverage   FLOAT,
        gate_attempts   INT,
        actual_tokens   INT,
        actual_minutes  FLOAT,
        failure_types   JSONB,
        failure_roles   JSONB,
        convergence_rounds INT,
        user_rating     INT,
        user_feedback   TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_spec_embedding
        ON dispatch_outcomes USING hnsw (spec_embedding vector_cosine_ops);
    CREATE INDEX IF NOT EXISTS idx_combination_hash
        ON dispatch_outcomes (combination_hash);
    """

    async def write(self, outcome: DispatchOutcome):
        """任务完成时异步写入（不阻塞主流程）"""
        ...

    async def query_similar_tasks(
        self,
        spec_embedding: List[float],
        top_k: int = 20,
        min_similarity: float = 0.75
    ) -> List[DispatchOutcome]:
        """根据需求向量检索历史相似任务"""
        sql = """
        SELECT *, 1 - (spec_embedding <=> $1::vector) AS similarity
        FROM dispatch_outcomes
        WHERE 1 - (spec_embedding <=> $1::vector) > $2
        ORDER BY similarity DESC
        LIMIT $3
        """
        return await self.db.fetch(sql, spec_embedding, min_similarity, top_k)

    async def get_combination_stats(
        self, combination_hash: str
    ) -> Optional["CombinationStats"]:
        """获取某个角色组合的历史统计"""
        sql = """
        SELECT
            combination_hash,
            COUNT(*)                        AS sample_count,
            AVG(quality_score)              AS avg_quality,
            AVG(overall_success::int)       AS success_rate,
            AVG(actual_tokens)              AS avg_tokens,
            AVG(actual_minutes)             AS avg_minutes,
            AVG(gate_attempts)              AS avg_gate_attempts
        FROM dispatch_outcomes
        WHERE combination_hash = $1
        GROUP BY combination_hash
        """
        row = await self.db.fetchrow(sql, combination_hash)
        return CombinationStats(**row) if row else None
```

---

### 5.2 反馈感知的评分器

```python
# agent_factory/dispatcher/feedback_scorer.py

class FeedbackAwareScorer:
    """
    在原有语义相似度得分基础上，叠加历史反馈信号。
    最终得分 = 语义相似度(40%) × 历史因子(40%) × 成本效率(20%)
    """

    def __init__(self, outcome_store: DispatchOutcomeStore):
        self.store = outcome_store

    async def score_candidate_team(
        self,
        candidate_slugs: List[str],
        current_spec_embedding: List[float],
        semantic_score: float,
    ) -> "ScoredTeam":

        combination_hash = DispatchOutcome.compute_combination_hash(candidate_slugs)
        combo_stats = await self.store.get_combination_stats(combination_hash)

        similar_tasks = await self.store.query_similar_tasks(
            current_spec_embedding, top_k=20
        )
        similar_success_with_combo = [
            t for t in similar_tasks
            if t.combination_hash == combination_hash and t.overall_success
        ]

        history_factor = self._compute_history_factor(
            combo_stats,
            similar_tasks_count=len(similar_tasks),
            similar_success_count=len(similar_success_with_combo)
        )
        cost_factor = self._compute_cost_factor(combo_stats)

        # 有3条以上历史数据才启用加权融合，否则退回纯语义得分
        if combo_stats and combo_stats.sample_count >= 3:
            final_score = (
                semantic_score * 0.4 +
                history_factor  * 0.4 +
                cost_factor     * 0.2
            )
        else:
            final_score = semantic_score

        return ScoredTeam(
            slugs=candidate_slugs,
            combination_hash=combination_hash,
            semantic_score=semantic_score,
            history_factor=history_factor,
            cost_factor=cost_factor,
            final_score=final_score,
            combo_stats=combo_stats,
        )

    def _compute_history_factor(
        self,
        stats: Optional["CombinationStats"],
        similar_tasks_count: int,
        similar_success_count: int,
    ) -> float:
        if stats is None or stats.sample_count < 3:
            return 0.5  # 无历史数据，中性

        global_sr = stats.success_rate
        similar_sr = (
            similar_success_count / similar_tasks_count
            if similar_tasks_count > 0 else global_sr
        )
        base = global_sr * 0.6 + similar_sr * 0.4
        gate_penalty = max(0, (stats.avg_gate_attempts - 1) * 0.1)
        return max(0.0, min(1.0, base - gate_penalty))

    def _compute_cost_factor(self, stats: Optional["CombinationStats"]) -> float:
        if stats is None:
            return 0.5
        GLOBAL_AVG_TOKENS = 120_000  # 经验值，可从DB动态计算
        efficiency = GLOBAL_AVG_TOKENS / max(stats.avg_tokens, 1)
        return max(0.1, min(1.0, efficiency))
```

---

### 5.3 MasterDispatcher v3 核心

```python
# agent_factory/dispatcher/master_dispatcher.py

class MasterDispatcher:
    """
    v3 核心变化：
    - dispatch 时读取历史反馈，调整候选团队得分
    - 任务完成后异步写入 DispatchOutcome（非阻塞）
    - explain_decision() 供检查点展示决策依据
    """

    def __init__(self, registry, outcome_store: DispatchOutcomeStore, **kwargs):
        super().__init__(registry, **kwargs)
        self.outcome_store = outcome_store
        self.scorer = FeedbackAwareScorer(outcome_store)

    async def dispatch_phase1(self, spec: AgentSpec, mode: ExecutionMode) -> DispatchPlan:
        relevant_divisions = self.domain_router.route(spec)
        candidate_pool = self.registry.query_by_divisions(relevant_divisions)
        spec_embedding = await self._embed_spec(spec)

        # 生成 Top-5 语义候选，叠加反馈评分
        top_candidates = self._semantic_top_k(spec, candidate_pool, k=5)
        scored_teams = await asyncio.gather(*[
            self.scorer.score_candidate_team(
                candidate_slugs=team,
                current_spec_embedding=spec_embedding,
                semantic_score=sem_score
            )
            for team, sem_score in top_candidates
        ])

        best_team = sorted(scored_teams, key=lambda t: -t.final_score)[0]
        final_team = self._apply_mandatory_roles(best_team.slugs, spec, mode)

        return DispatchPlan(
            discussion_team=final_team,
            discussion_rounds=mode.recommended_rounds,
            cost_estimate=self._estimate_cost(final_team, mode),
            decision_explanation=self._explain(scored_teams, best_team),
        )

    async def record_outcome(self, outcome: DispatchOutcome):
        """任务完成后非阻塞异步写入"""
        asyncio.create_task(self.outcome_store.write(outcome))
```

---

### 5.4 数据成熟后的升级路径

| 数据量 | 当前策略 | 升级路径 |
|--------|---------|---------|
| 0–50条 | 纯语义匹配（退回v2） | — |
| 50–500条 | 加权融合（§6.2） | — |
| 500–5000条 | 加权融合 + 按领域分组统计 | 引入 LightGBM 排序模型 |
| 5000+条 | 专用调度排序模型 | Fine-tune 小型分类器 |

---


## 6. 多轮讨论阶段（并行异步 DiscussionGraph）

### 6.0 问题本质

串行讨论的问题：

```
角色A发言 → 角色B发言 → 角色C发言 → 下一轮
```

正确的模型是**异步公告板（Async Bulletin Board）**：

```
轮次开始 → 所有角色同时读取公告板快照
         → 并行生成各自的回应（并行LLM调用，耗时=单次调用时间）
         → 并发写入公告板
轮次结束 → 协调者评估收敛度
```

效率提升：3角色×3轮，从 9 次串行调用变为 3 轮×1倍延迟，墙上时钟时间**降低约 3 倍**。

> **替换声明**：v2.0 串行讨论模型已废弃，统一采用并行异步 `DiscussionGraph v3`。

---

### 6.1 公告板数据结构

```python
# agent_factory/discussion/bulletin_board.py

@dataclass
class BulletinPost:
    """公告板上的单条发言"""
    post_id: str
    round_number: int
    author_slug: str
    author_name: str
    content: str
    position: str                        # 提炼的立场摘要（用于收敛计算）
    addressed_to: List[str]              # @回应的角色slug列表（空=广播）
    references: List[str]                # 引用的 post_id 列表
    timestamp: float
    confidence: float                    # 0~1，角色对自己立场的置信度
    key_claims: List[str]                # 核心主张（供综合节点使用）

class BulletinBoard:
    """线程安全的异步公告板"""

    def __init__(self):
        self._posts: List[BulletinPost] = []
        self._lock = asyncio.Lock()

    async def publish(self, post: BulletinPost):
        async with self._lock:
            self._posts.append(post)

    def read_all(self) -> List[BulletinPost]:
        return list(self._posts)

    def read_round(self, round_number: int) -> List[BulletinPost]:
        return [p for p in self._posts if p.round_number == round_number]

    def read_by_round_excluding(
        self, round_number: int, exclude_slug: str
    ) -> List[BulletinPost]:
        return [
            p for p in self._posts
            if p.round_number == round_number and p.author_slug != exclude_slug
        ]
```

---

### 6.2 并行讨论图（LangGraph Send API）

```python
# agent_factory/discussion/parallel_graph.py

from langgraph.graph import StateGraph, END
from langgraph.types import Send
from typing import TypedDict, List, Annotated
import operator, asyncio

class ParallelDiscussionState(TypedDict):
    agent_spec: AgentSpec
    discussion_team: List[AgentMeta]
    bulletin_board: BulletinBoard        # 共享公告板（跨节点共享引用）
    round_number: int
    max_rounds: int
    convergence_score: float
    convergence_round: int
    disagreements: List[str]
    role_positions: dict                 # {slug: position_str}
    tech_spec: Optional[TechSpec]

class SingleRoleInput(TypedDict):
    """LangGraph Send 分发给每个角色节点的输入"""
    agent_meta: AgentMeta
    board_snapshot: List[BulletinPost]   # 轮次开始时的快照（不可变）
    round_number: int
    agent_spec: AgentSpec

# ── 节点1：轮次扇出（并行触发所有角色）
async def round_fan_out(state: ParallelDiscussionState) -> List[Send]:
    """
    使用 LangGraph Send API 并行触发所有角色。
    每个角色收到相同的公告板快照，保证本轮输入一致性。
    """
    board_snapshot = state["bulletin_board"].read_all()

    return [
        Send(
            node="role_respond",
            arg=SingleRoleInput(
                agent_meta=agent,
                board_snapshot=board_snapshot,
                round_number=state["round_number"],
                agent_spec=state["agent_spec"]
            )
        )
        for agent in state["discussion_team"]
    ]

# ── 节点2：角色并行响应（每个角色独立，互不阻塞）
async def role_respond(input: SingleRoleInput) -> dict:
    agent = input["agent_meta"]
    board = input["board_snapshot"]

    context = _build_role_context(agent, board, input["agent_spec"])

    llm = ChatAnthropic(model="claude-opus-4-5", temperature=0.7)
    response = await llm.ainvoke([
        SystemMessage(content=agent.system_prompt + DISCUSSION_ADDON),
        HumanMessage(content=context)
    ])

    parsed = _parse_role_response(response.content, agent.slug, input["round_number"])
    return {"new_post": parsed}

# ── 节点3：汇聚节点（LangGraph 自动等待所有角色完成）
async def round_collect(
    state: ParallelDiscussionState,
    new_posts: Annotated[List[dict], operator.add]  # 自动聚合所有角色的输出
) -> ParallelDiscussionState:
    board = state["bulletin_board"]
    for post_data in new_posts:
        await board.publish(post_data["new_post"])

    new_positions = {
        p["new_post"].author_slug: p["new_post"].position
        for p in new_posts
    }

    convergence = _compute_convergence(new_positions, state["role_positions"])

    return {
        **state,
        "role_positions": {**state["role_positions"], **new_positions},
        "convergence_score": convergence,
        "round_number": state["round_number"] + 1,
    }

# ── 节点4：轮次决策
def round_decision(state: ParallelDiscussionState) -> str:
    if state["convergence_score"] >= 0.85:
        return "synthesize"
    if state["round_number"] >= state["max_rounds"]:
        return "synthesize"
    if _has_critical_disagreement(state) and state["round_number"] >= 2:
        return "arbitrate"
    return "next_round"

# ── 图构建
def build_parallel_discussion_graph() -> StateGraph:
    graph = StateGraph(ParallelDiscussionState)

    graph.add_node("round_fan_out",  round_fan_out)
    graph.add_node("role_respond",   role_respond)
    graph.add_node("round_collect",  round_collect)
    graph.add_node("arbitrator",     arbitrator_node)
    graph.add_node("synthesis",      synthesis_node)

    graph.set_entry_point("round_fan_out")
    graph.add_edge("round_fan_out", "role_respond")   # Send → 并行
    graph.add_edge("role_respond",  "round_collect")  # 自动等待所有角色

    graph.add_conditional_edges(
        "round_collect",
        round_decision,
        {
            "next_round": "round_fan_out",
            "arbitrate":  "arbitrator",
            "synthesize": "synthesis",
        }
    )
    graph.add_edge("arbitrator", "round_fan_out")
    graph.add_edge("synthesis",  END)

    return graph.compile(checkpointer=MemorySaver())
```

---

### 6.3 角色上下文构建策略

```python
def _build_role_context(agent: AgentMeta, board: List[BulletinPost], spec: AgentSpec) -> str:
    """
    每个角色看到定制化上下文：
    1. 任务描述
    2. 本轮@自己的帖子（优先）
    3. 其他角色最近的发言（过滤掉自己的）
    """
    addressed = [p for p in board if agent.slug in p.addressed_to]
    recent_others = [p for p in board if p.author_slug != agent.slug][-10:]
    context_posts = _deduplicate([*addressed, *recent_others])

    return f"""
## 任务
{spec.to_prompt_str()}

## 当前讨论公告板
{_format_bulletin(context_posts, perspective_slug=agent.slug)}

## 你的任务（作为 {agent.name}）
请从你的专业视角：
1. 回应与你专业最相关的观点（可@具体角色）
2. 提出尚未被充分讨论的关键问题
3. 明确表达你当前的立场

输出格式：
<position>你的立场一句话摘要</position>
<claims>
- 主张1
- 主张2
</claims>
<response>正文发言...</response>
"""
```

---

### 6.4 综合节点

```python
async def synthesis_node(state: ParallelDiscussionState) -> dict:
    board = state["bulletin_board"].read_all()

    clustered = _cluster_claims_by_topic(board)      # 按主题聚类
    consensus = _extract_consensus(board, threshold=0.8)
    disagreements = _extract_disagreements(board)

    llm = ChatAnthropic(model="claude-opus-4-5", temperature=0.1)
    tech_spec = await llm.with_structured_output(TechSpec).ainvoke(
        SYNTHESIS_PROMPT.format(
            clustered=clustered,
            consensus=consensus,
            disagreements=disagreements,
            spec=state["agent_spec"]
        )
    )

    return {
        "tech_spec": tech_spec,
        "convergence_round": state["round_number"] - 1,
        "discussion_disagreements": disagreements,   # 保留供检查点2展示
    }
```

---


## 7. 协作开发阶段

> 本章为 v2.1 版本：分流路由 + 结构化恢复增强。

> **替换声明**：v2.0 的 `error_handler` 已废弃；失败处理统一进入 `failure_classifier + recovery_strategy`。

### 6.1 任务分流路由器

不同类型的目标智能体需要不同的开发角色组合，系统基于 TechSpec 输出的任务清单进行智能分流：

```python
class DevTaskRouter:
    """
    根据技术规格书中的任务类型，将任务路由到对应的开发角色。
    每个任务可以有多个角色协作（主角色 + 辅助角色）。
    """
    
    TASK_ROLE_MAP = {
        TaskType.CORE_LOGIC:        ["backend-architect", "ai-engineer"],
        TaskType.FRONTEND_UI:       ["frontend-developer", "ui-designer"],
        TaskType.MCP_INTEGRATION:   ["mcp-builder", "backend-architect"],  
        TaskType.RAG_PIPELINE:      ["ai-data-remediation-engineer", "ai-engineer"],
        TaskType.DEPLOYMENT:        ["devops-automator"],
        TaskType.DOCUMENTATION:     ["technical-writer"],
        TaskType.GAME_MECHANICS:    ["unity-architect", "game-designer"],
        TaskType.XR_INTERFACE:      ["xr-interface-architect", "spatial-ux-designer"],
        TaskType.SMART_CONTRACT:    ["solidity-smart-contract-engineer"],
        TaskType.MOBILE:            ["mobile-app-builder"],
        TaskType.IDENTITY_CONFIG:   ["agentic-identity-architect"],  # ⭐必选
    }
```

### 6.2 MCP Builder 的工厂关键作用

**MCP Builder** 是 Specialized 部门中对 Agent Factory 最重要的角色，在开发阶段承担：

1. 分析目标智能体需要哪些外部工具和服务
2. 生成完整的 `mcp_config.yaml`
3. 为每个 MCP 服务器编写连接适配器代码
4. 生成 MCP 服务器的测试用例
5. 编写 MCP 配置的使用文档

这确保了交付的每个智能体都有"开箱即用"的工具接入能力。

### 6.3 失败恢复机制

#### 7.3.1 问题本质

失败处理必须具备以下能力：失败分类 / 分级恢复策略 / Circuit Breaker / 部分成功处理 / 失败知识积累。以下是完整的四层恢复体系设计。

---

### 6.4 完整的失败恢复系统

> 实现结构化的分类→策略→执行→记录四层恢复体系。

#### 7.4.1 失败分类体系

```python
# agent_factory/recovery/failure_taxonomy.py

class FailureDomain(Enum):
    LLM_CALL         = "llm_call"
    TOOL_EXECUTION   = "tool_execution"
    CODE_EXECUTION   = "code_execution"
    INTEGRATION      = "integration"
    QUALITY_GATE     = "quality_gate"
    SANDBOX          = "sandbox"
    EXTERNAL_SERVICE = "external_service"
    CONTRACT         = "contract"

class FailureType(Enum):
    # LLM 类
    LLM_TIMEOUT           = "llm_timeout"
    LLM_RATE_LIMIT        = "llm_rate_limit"
    LLM_CONTEXT_TOO_LONG  = "llm_context_too_long"
    # 代码类
    SYNTAX_ERROR          = "syntax_error"
    RUNTIME_ERROR         = "runtime_error"
    IMPORT_ERROR          = "import_error"
    # 质量类
    TEST_FAILURE          = "test_failure"
    SECURITY_VULNERABILITY = "security_vulnerability"
    PERFORMANCE_BELOW_THRESHOLD = "performance_below_threshold"
    CONTRACT_VIOLATION    = "contract_violation"
    # 集成类
    MCP_CONNECTION_FAILED = "mcp_connection_failed"
    MCP_CONFIG_INVALID    = "mcp_config_invalid"
    # 系统类
    SANDBOX_OOM           = "sandbox_oom"
    SANDBOX_TIMEOUT       = "sandbox_timeout"
    NETWORK_ERROR         = "network_error"

class RecoverySeverity(Enum):
    TRANSIENT   = "transient"    # 短暂故障，直接重试
    RECOVERABLE = "recoverable"  # 可通过调整恢复
    STRUCTURAL  = "structural"   # 需要重构才能解决
    FATAL       = "fatal"        # 无法自动恢复

@dataclass
class ClassifiedFailure:
    domain: FailureDomain
    failure_type: FailureType
    severity: RecoverySeverity
    raw_error: str
    context: dict
    affected_components: List[str]
```

---

#### 7.4.2 恢复策略引擎

```python
# agent_factory/recovery/strategy_engine.py

class RecoveryStrategy(Enum):
    RETRY_IMMEDIATE       = "retry_immediate"
    RETRY_WITH_BACKOFF    = "retry_with_backoff"
    RETRY_WITH_CONTEXT    = "retry_with_context"   # 加入错误信息后重试
    DECOMPOSE_AND_RETRY   = "decompose_and_retry"  # 拆解子任务后重试
    PARTIAL_ROLLBACK      = "partial_rollback"      # 只回滚失败组件
    SUBSTITUTE_ROLE       = "substitute_role"       # 换专业角色介入
    SUBSTITUTE_TOOL       = "substitute_tool"
    REDUCE_SCOPE          = "reduce_scope"          # 降低需求范围
    GRACEFUL_DEGRADE      = "graceful_degrade"      # 降级交付带警告
    ESCALATE_TO_HUMAN     = "escalate_to_human"     # 人工介入


class RecoveryStrategyEngine:
    """失败类型 → 恢复策略的映射和执行引擎"""

    # 恢复策略决策树（按优先级排列，第N次失败用第N个策略）
    STRATEGY_MAP = {
        FailureType.LLM_TIMEOUT:            [RecoveryStrategy.RETRY_WITH_BACKOFF],
        FailureType.LLM_RATE_LIMIT:         [RecoveryStrategy.RETRY_WITH_BACKOFF],
        FailureType.NETWORK_ERROR:          [RecoveryStrategy.RETRY_IMMEDIATE,
                                             RecoveryStrategy.RETRY_WITH_BACKOFF],
        FailureType.SYNTAX_ERROR:           [RecoveryStrategy.RETRY_WITH_CONTEXT,
                                             RecoveryStrategy.SUBSTITUTE_ROLE],
        FailureType.RUNTIME_ERROR:          [RecoveryStrategy.RETRY_WITH_CONTEXT,
                                             RecoveryStrategy.DECOMPOSE_AND_RETRY],
        FailureType.IMPORT_ERROR:           [RecoveryStrategy.RETRY_WITH_CONTEXT],
        FailureType.TEST_FAILURE:           [RecoveryStrategy.SUBSTITUTE_ROLE,
                                             RecoveryStrategy.PARTIAL_ROLLBACK],
        FailureType.SECURITY_VULNERABILITY: [RecoveryStrategy.SUBSTITUTE_ROLE,
                                             RecoveryStrategy.ESCALATE_TO_HUMAN],
        FailureType.CONTRACT_VIOLATION:     [RecoveryStrategy.RETRY_WITH_CONTEXT,
                                             RecoveryStrategy.REDUCE_SCOPE,
                                             RecoveryStrategy.ESCALATE_TO_HUMAN],
        FailureType.PERFORMANCE_BELOW_THRESHOLD: [
                                             RecoveryStrategy.SUBSTITUTE_ROLE,
                                             RecoveryStrategy.REDUCE_SCOPE,
                                             RecoveryStrategy.GRACEFUL_DEGRADE],
        FailureType.MCP_CONFIG_INVALID:     [RecoveryStrategy.SUBSTITUTE_ROLE],
        FailureType.MCP_CONNECTION_FAILED:  [RecoveryStrategy.RETRY_WITH_BACKOFF,
                                             RecoveryStrategy.SUBSTITUTE_TOOL],
        FailureType.SANDBOX_OOM:            [RecoveryStrategy.RETRY_WITH_CONTEXT,
                                             RecoveryStrategy.REDUCE_SCOPE],
    }

    # 替换角色映射（哪种失败换哪个角色）
    SUBSTITUTE_ROLE_MAP = {
        FailureType.SYNTAX_ERROR:                "code-reviewer",
        FailureType.RUNTIME_ERROR:               "backend-architect",
        FailureType.TEST_FAILURE:                "evidence-collector",
        FailureType.SECURITY_VULNERABILITY:      "security-engineer",
        FailureType.PERFORMANCE_BELOW_THRESHOLD: "performance-benchmarker",
        FailureType.MCP_CONFIG_INVALID:          "mcp-builder",
        FailureType.CONTRACT_VIOLATION:          "agentic-identity-architect",
    }

    async def execute_recovery(
        self,
        failure: ClassifiedFailure,
        state: "FactoryStateV3",
        attempt_number: int,
        max_attempts: int = 3
    ) -> "RecoveryResult":

        if attempt_number > max_attempts:
            return RecoveryResult(
                action=RecoveryStrategy.ESCALATE_TO_HUMAN,
                can_continue=False,
                human_message=self._compose_escalation(failure, state),
                options=["重新描述需求", "接受降级交付", "手动修复后继续", "放弃任务"]
            )

        strategies = self.STRATEGY_MAP.get(
            failure.failure_type,
            [RecoveryStrategy.RETRY_WITH_BACKOFF, RecoveryStrategy.ESCALATE_TO_HUMAN]
        )
        strategy_idx = min(attempt_number - 1, len(strategies) - 1)
        chosen = strategies[strategy_idx]
        return await self._apply_strategy(chosen, failure, state)

    async def _substitute_role(self, failure, state) -> "RecoveryResult":
        substitute_slug = self.SUBSTITUTE_ROLE_MAP.get(failure.failure_type)
        return RecoveryResult(
            action=RecoveryStrategy.SUBSTITUTE_ROLE,
            substitute_role_slug=substitute_slug,
            remediation_instruction=self._compose_remediation_prompt(failure, substitute_slug),
            can_continue=True,
            next_node="targeted_remediation"
        )

    async def _graceful_degrade(self, failure, state) -> "RecoveryResult":
        degraded_spec = self._compute_degraded_spec(
            original_spec=state["agent_spec"],
            failed_components=failure.affected_components
        )
        return RecoveryResult(
            action=RecoveryStrategy.GRACEFUL_DEGRADE,
            degraded_spec=degraded_spec,
            degradation_notice=(
                f"以下功能因 {failure.failure_type.value} 无法实现，已从交付范围移除: "
                f"{failure.affected_components}"
            ),
            can_continue=True,
            next_node="packaging"    # 直接跳到打包，带降级说明
        )
```

---

#### 7.4.3 失败分类器

```python
# agent_factory/recovery/failure_classifier.py

class FailureClassifier:
    """两阶段分类：规则树（快速）→ LLM兜底（覆盖长尾）"""

    RULE_TREE = {
        "anthropic.APITimeoutError":    (FailureDomain.LLM_CALL,    FailureType.LLM_TIMEOUT,           RecoverySeverity.TRANSIENT),
        "anthropic.RateLimitError":     (FailureDomain.LLM_CALL,    FailureType.LLM_RATE_LIMIT,        RecoverySeverity.TRANSIENT),
        r"SyntaxError":                 (FailureDomain.CODE_EXECUTION, FailureType.SYNTAX_ERROR,        RecoverySeverity.RECOVERABLE),
        r"ModuleNotFoundError":         (FailureDomain.CODE_EXECUTION, FailureType.IMPORT_ERROR,        RecoverySeverity.RECOVERABLE),
        r"MemoryError|OOMKilled":       (FailureDomain.SANDBOX,      FailureType.SANDBOX_OOM,           RecoverySeverity.RECOVERABLE),
        "test_failure":                 (FailureDomain.QUALITY_GATE, FailureType.TEST_FAILURE,          RecoverySeverity.RECOVERABLE),
        "security_scan_failed":         (FailureDomain.QUALITY_GATE, FailureType.SECURITY_VULNERABILITY, RecoverySeverity.STRUCTURAL),
        "contract_violation":           (FailureDomain.QUALITY_GATE, FailureType.CONTRACT_VIOLATION,    RecoverySeverity.STRUCTURAL),
        "mcp.*connection.*refused":     (FailureDomain.EXTERNAL_SERVICE, FailureType.MCP_CONNECTION_FAILED, RecoverySeverity.TRANSIENT),
    }

    async def classify(self, error: Exception, context: dict) -> ClassifiedFailure:
        for pattern, (domain, ftype, severity) in self.RULE_TREE.items():
            if self._matches(error, pattern):
                return ClassifiedFailure(
                    domain=domain, failure_type=ftype, severity=severity,
                    raw_error=str(error), context=context,
                    affected_components=self._extract_affected(error, context),
                )
        return await self._llm_classify(error, context)  # LLM兜底
```

---

#### 7.4.4 恢复日志（失败知识积累）

```python
# agent_factory/recovery/recovery_journal.py

class RecoveryJournal:
    """
    记录所有恢复尝试，形成失败知识库。
    数据回流给 MasterDispatcherV3（避免高失败率角色）和 ToolSelector（避免高失败率工具）。
    """

    async def record(
        self,
        session_id: str,
        failure: ClassifiedFailure,
        strategy: RecoveryStrategy,
        outcome: str,           # "success" / "failed_again" / "escalated"
        duration_seconds: float
    ):
        await self.db.execute("""
            INSERT INTO recovery_journal
            (session_id, failure_domain, failure_type, severity,
             affected_components, strategy_applied, outcome, duration_s, timestamp)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,NOW())
        """, session_id,
            failure.domain.value, failure.failure_type.value, failure.severity.value,
            json.dumps(failure.affected_components),
            strategy.value, outcome, duration_seconds
        )

    async def get_failure_patterns(self, lookback_days: int = 30) -> List[dict]:
        """
        查询常见失败模式，供调度器参考。
        示例输出：'backend-architect 在 MCP集成 任务上失败率 40%，建议改用 mcp-builder'
        """
        return await self.db.fetch("""
            SELECT
                failure_type,
                jsonb_array_elements_text(affected_components) AS role_or_tool,
                COUNT(*) AS total,
                AVG(CASE WHEN outcome='success' THEN 1 ELSE 0 END) AS recovery_success_rate
            FROM recovery_journal
            WHERE timestamp > NOW() - ($1 || ' days')::interval
            GROUP BY failure_type, role_or_tool
            HAVING COUNT(*) >= 3
            ORDER BY total DESC
        """, lookback_days)
```

---

#### 7.4.5 集成到 LangGraph 主图（替换 error_handler）

```python
# factory_graph_v3.py 相关节点替换

graph.add_node("failure_classifier",   failure_classifier_node)
graph.add_node("recovery_strategy",    recovery_strategy_node)
graph.add_node("targeted_remediation", targeted_remediation_node)  
graph.add_node("human_recovery",       human_recovery_node)        # 人工介入
graph.add_node("graceful_packager",    graceful_packager_node)     # 降级打包

# 任何节点失败 → 先分类
for failed_node in ["discussion", "development", "quality_gate", "packaging"]:
    graph.add_conditional_edges(
        failed_node,
        check_for_error,
        {"ok": next_map[failed_node], "error": "failure_classifier"}
    )

graph.add_edge("failure_classifier", "recovery_strategy")

graph.add_conditional_edges(
    "recovery_strategy",
    lambda s: s["recovery_result"].action.value,
    {
        "retry_immediate":    lambda s: s["failed_node"],
        "retry_with_backoff": lambda s: s["failed_node"],
        "retry_with_context": lambda s: s["failed_node"],
        "substitute_role":    "targeted_remediation",
        "graceful_degrade":   "graceful_packager",
        "escalate_to_human":  "human_recovery",
    }
)

graph.add_conditional_edges(
    "human_recovery",
    lambda s: s["human_decision"],
    {
        "retry":   lambda s: s["failed_node"],
        "degrade": "graceful_packager",
        "abort":   END
    }
)
```

---




## 8. 沙箱策略（全层次设计）

### 8.1 沙箱四层分级

四层沙箱分级强制执行，覆盖工厂全生命周期：

- **沙箱A（进程级）**：讨论阶段角色隔离
- **沙箱B（容器级）★主沙箱**：代码执行强制隔离
- **沙箱C（容器级+网络模拟）**：测试阶段
- **沙箱D（VM/全新容器）**：交付验证

### 8.2 Game Development 沙箱特殊配置

游戏开发部门的角色可能生成需要游戏引擎运行时的代码（Unity C#、GDScript等），需要特殊的沙箱配置：

```yaml
# game_dev_sandbox_config.yaml
containers:
  unity_sandbox:
    image: "unity-editor-headless:2023.3-lts"
    memory: "4g"
    cpu_quota: 200000  # 200% CPU
    network: "none"
    
  godot_sandbox:
    image: "godot-headless:4.x"
    memory: "2g"
    network: "none"
```

---

## 9. 成本控制与可观测性

### 9.1 Token 预算体系

```python
class CostController:
    """全程 Token 消耗追踪和预算管控"""
    
    # 各阶段 Token 预算上限（per task）
    PHASE_BUDGETS = {
        ExecutionMode.FAST: {
            "total": 50_000,
        },
        ExecutionMode.STANDARD: {
            "discussion": 20_000,
            "development": 80_000,
            "testing": 20_000,
            "total": 120_000,
        },
        ExecutionMode.THOROUGH: {
            "discussion": 40_000,
            "development": 200_000,
            "testing": 60_000,
            "total": 300_000,
        },
    }
    
    def check_budget(self, phase: str, used: int, mode: ExecutionMode) -> bool:
        """若超出预算，暂停并通知用户决策"""
        budget = self.PHASE_BUDGETS[mode][phase]
        if used > budget * 0.9:  # 90%警告
            self._notify_user_budget_warning(phase, used, budget)
        return used <= budget
```

### 9.2 可观测性架构

```python
# 集成 LangSmith + OpenTelemetry

from langsmith import traceable
from opentelemetry import trace

tracer = trace.get_tracer("agent-factory")

@traceable(name="discussion_round", tags=["phase:discussion"])
async def discussion_round_node(state: DiscussionState) -> DiscussionState:
    with tracer.start_as_current_span("role_invocation") as span:
        span.set_attribute("role.slug", current_role.slug)
        span.set_attribute("role.division", current_role.division.value)
        span.set_attribute("round.number", state["round_number"])
        span.set_attribute("tokens.estimated", estimated_tokens)
        # ... 节点逻辑 ...
```

**可观测数据点（每个节点）**：
- 角色名称和部门
- 输入/输出 Token 数量
- 执行耗时
- 角色立场摘要（讨论阶段）
- 代码行数和测试覆盖率（开发阶段）

---

## 10. 人机协作检查点

系统设置三个人机协作检查点（使用 LangGraph `interrupt_before`），在关键决策节点暂停等待用户确认：

### 检查点1：需求确认 + 语言选择（Intake之后）

```python
# 在 intake → dispatch_phase1 之间
# 展示给用户：
{
    "parsed_spec": {
        "target_agent_name": "AI客服助手",
        "detected_domain": "enterprise",
        "key_capabilities": ["多语言支持", "工单系统集成", "情绪识别"],
        "detected_tools_needed": ["Zendesk MCP", "Slack MCP"],
        "suggested_mode": "Standard",
        "cost_estimate": "~$2.50 | ~45分钟",

        # ── 语言选择（新增）──────────────────────────────────────
        "target_language": "python",         # IntakeAgent推断结果
        "language_inference_confidence": 0.82,  # 推断置信度
        "language_inference_reason": "用户描述中提到 langchain，推断为Python",
        # 若推断置信度 < 0.6，target_language 为 null，强制要求用户选择
    },
    "user_actions": ["确认并继续", "修改需求", "切换档位", "取消"],
    # ── 语言确认动作（新增）─────────────────────────────────────
    "language_actions": ["使用Python（推荐）", "改为Node.js"],
    "language_note": "此选择决定生成代码的运行时、依赖安装方式和Dockerfile基础镜像，开始开发后无法更改"
}
```

### 检查点2：技术规格书审查（Discussion之后）

```python
# 在 discussion → dispatch_phase2 之间
# 展示给用户：
{
    "tech_spec_preview": {
        "architecture": "...",
        "tech_stack": "...",
        "task_breakdown": [...],
        "risk_register": [...],
        "discussion_disagreements": [...]  # 保留的未解决分歧供用户决策
    },
    "user_actions": ["批准并开始开发", "编辑规格书", "调整讨论团队重新讨论"]
}
```

### 检查点3：交付预览（打包之后，发布之前）

```python
# 在 packaging → delivery 之间
# 展示给用户：
{
    "delivery_preview": {
        "agent_demo": "...",  # 目标智能体的试运行演示
        "test_report_summary": "...",
        "sandbox_validation": "通过/失败",
        "tutorial_preview": "..."
    },
    "user_actions": ["确认交付", "要求修改", "重新测试"]
}
```

---

## 11. LangGraph技术实现

### 11.1 主工作流图

```python
# agent_factory/core/factory_graph.py

class FactoryStateV3(TypedDict):
    session_id: str
    user_input: str
    execution_mode: ExecutionMode
    target_language: str                 # "python" | "nodejs"，检查点1确认后锁定
    agent_spec: Optional[AgentSpec]
    domain: Optional[str]
    cost_estimate: Optional[CostEstimate]
    dispatch_plan_phase1: Optional[DispatchPlan]
    tech_spec: Optional[TechSpec]
    dispatch_plan_phase2: Optional[DispatchPlan]
    development_artifacts: dict
    test_report: Optional[TestReport]
    retry_count: int
    failure: Optional[ClassifiedFailure]         # 结构化失败对象
    recovery_result: Optional[RecoveryResult]    # 恢复动作
    failed_node: Optional[str]                   # 失败来源节点
    delivery_package: Optional[DeliveryPackage]
    status: str
    token_usage: dict

def build_factory_graph_v3() -> StateGraph:
    graph = StateGraph(FactoryStateV3)

    # 核心节点
    graph.add_node("intake",              intake_node)
    graph.add_node("domain_router",       domain_router_node)
    graph.add_node("cost_estimate",       cost_estimate_node)
    graph.add_node("dispatch_phase1",     dispatch_phase1_node)
    graph.add_node("discussion",          discussion_node)
    graph.add_node("dispatch_phase2",     dispatch_phase2_node)
    graph.add_node("development",         development_node)
    graph.add_node("quality_gate",        quality_gate_node)
    graph.add_node("packaging",           packaging_node)
    graph.add_node("delivery",            delivery_node)

    # 失败恢复链
    graph.add_node("failure_classifier",   failure_classifier_node)
    graph.add_node("recovery_strategy",    recovery_strategy_node)
    graph.add_node("targeted_remediation", targeted_remediation_node)
    graph.add_node("human_recovery",       human_recovery_node)
    graph.add_node("graceful_packager",    graceful_packager_node)

    graph.set_entry_point("intake")
    graph.add_edge("intake", "domain_router")
    graph.add_edge("domain_router", "cost_estimate")
    graph.add_edge("cost_estimate", "dispatch_phase1")

    graph.add_conditional_edges(
        "dispatch_phase1",
        lambda s: "skip_discussion" if s["execution_mode"] == "fast" else "discussion",
        {"discussion": "discussion", "skip_discussion": "dispatch_phase2"}
    )
    graph.add_edge("discussion", "dispatch_phase2")
    graph.add_edge("dispatch_phase2", "development")
    graph.add_edge("development", "quality_gate")

    # Quality Gate：所有失败路径统一进入 failure_classifier 分类
    graph.add_conditional_edges(
        "quality_gate",
        route_quality_gate,
        {
            "pass":         "packaging",
            "fail":         "failure_classifier",   # 所有失败统一分类
        }
    )

    # failure_classifier → recovery_strategy → 按策略分流
    graph.add_edge("failure_classifier", "recovery_strategy")

    graph.add_conditional_edges(
        "recovery_strategy",
        lambda s: s["recovery_result"].action.value,
        {
            "retry_immediate":    lambda s: s["failed_node"],   # 回失败节点重试
            "retry_with_backoff": lambda s: s["failed_node"],
            "retry_with_context": lambda s: s["failed_node"],
            "substitute_role":    "targeted_remediation",       # 换角色定向修复
            "graceful_degrade":   "graceful_packager",          # 降级打包
            "escalate_to_human":  "human_recovery",             # 人工介入
        }
    )

    # 各失败分流出口
    graph.add_edge("targeted_remediation", "quality_gate")  # 修复后重新测试
    graph.add_edge("graceful_packager",    "delivery")       # 降级直接交付

    graph.add_conditional_edges(
        "human_recovery",
        lambda s: s["human_decision"],
        {
            "retry":   lambda s: s["failed_node"],
            "degrade": "graceful_packager",
            "abort":   END
        }
    )

    graph.add_edge("packaging", "delivery")
    graph.add_edge("delivery",  END)

    return graph.compile(
        checkpointer=PostgresSaver.from_conn_string(os.environ["DATABASE_URL"]),
        interrupt_before=["dispatch_phase1", "dispatch_phase2", "delivery"]
    )
```

---

## 12. 智能体工具基础引擎（带调度智能）

### 12.0 概述

传统被动工具库要求 agent 必须知道工具名才能调用，缺少：
- **给定子任务，自动选最合适的工具**
- **工具失败时，自动 fallback 到备选工具**
- **追踪哪些工具在哪类任务上成功率高**
- **工具组合推荐**（某些任务需要工具A + 工具B串联）

> **行为变化总结（v2.1）**：Agent 不再直接调用工具，而是统一通过 `ToolSelector` 生成执行计划，再由 `FallbackAwareToolExecutor` 执行。

---

### 12.1 工具能力描述符

```python
# agent_factory/engine/tool_descriptor.py

@dataclass
class ToolCapabilityDescriptor:
    """每个工具的机器可读能力说明，供 ToolSelector 匹配。"""
    tool_id: str
    name: str
    category: ToolCategory              # WEB_ACCESS/CODE_EXEC/FILE_OPS/...
    description: str                    # 自然语言说明（用于向量化）
    capability_embedding: List[float]   # 768维，预计算

    # 输入输出契约
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]

    # 成本与性能
    avg_latency_ms: float
    cost_per_call: float
    rate_limit_per_min: Optional[int]

    # 可靠性统计（运行时动态更新）
    success_rate: float = 1.0
    failure_modes: List[str] = field(default_factory=list)

    # 依赖与安全
    requires_env_vars: List[str] = field(default_factory=list)
    requires_sandbox: bool = False

    # 来源与组合
    source: str = "builtin"             # builtin / mcp / skill
    fallback_tool_ids: List[str] = field(default_factory=list)
    composable_with: List[str] = field(default_factory=list)
```

---

### 12.2 工具能力向量索引

```python
# agent_factory/engine/tool_capability_index.py

class ToolCapabilityIndex:
    """工具能力的向量索引，支持语义检索 + 分类过滤 + 组合推荐"""

    async def build(self, all_tools: List[ToolCapabilityDescriptor]):
        """启动时构建一次，新工具注册时增量更新"""
        embedder = EmbeddingModel()
        for tool in all_tools:
            embedding = await embedder.embed(f"{tool.name}: {tool.description}")
            tool.capability_embedding = embedding
            self._descriptors[tool.tool_id] = tool
            await self.vs.upsert(
                id=tool.tool_id,
                vector=embedding,
                metadata={
                    "category": tool.category.value,
                    "source": tool.source,
                    "cost": tool.cost_per_call,
                    "success_rate": tool.success_rate,
                }
            )

    async def search(
        self,
        task_description: str,
        top_k: int = 5,
        filter_category: Optional[ToolCategory] = None,
        max_cost_per_call: Optional[float] = None,
    ) -> List["ScoredTool"]:
        """给定子任务描述，返回能力匹配的 Top-K 工具"""
        task_embedding = await self._embedder.embed(task_description)

        results = await self.vs.query(
            vector=task_embedding,
            top_k=top_k * 2,
            filter=self._build_filter(filter_category, max_cost_per_call)
        )

        scored = [
            ScoredTool(
                descriptor=self._descriptors[r.id],
                semantic_score=r.score,
                adjusted_score=self._adjust_score(r.score, self._descriptors[r.id])
            )
            for r in results
            if r.id in self._descriptors and self._is_available(self._descriptors[r.id])
        ]

        return sorted(scored, key=lambda t: -t.adjusted_score)[:top_k]

    def _adjust_score(self, semantic_score: float, desc: ToolCapabilityDescriptor) -> float:
        """叠加可靠性(+)、成本(-)、延迟(+)修正"""
        reliability_bonus = (desc.success_rate - 0.5) * 0.3
        cost_penalty      = min(desc.cost_per_call * 10, 0.2)
        latency_bonus     = max(0, (2000 - desc.avg_latency_ms) / 10000)
        return semantic_score + reliability_bonus - cost_penalty + latency_bonus
```

---

### 12.3 ToolSelector — 智能工具选择器

```python
# agent_factory/engine/tool_selector.py

class ToolSelector:
    """给定子任务 → 返回最优工具执行计划（含 Fallback 链和组合推荐）"""

    async def select(
        self,
        task: SubTask,
        context: AgentContext,
        strategy: SelectionStrategy = SelectionStrategy.BALANCED
    ) -> "ToolExecutionPlan":

        # 1. 语义检索候选工具
        candidates = await self.index.search(task.description, top_k=5)

        # 2. 历史记录提升（同类任务成功过的工具加分）
        history_boosted = await self._history_boost(candidates, task.task_type)

        # 3. 按策略排序（CHEAPEST/FASTEST/RELIABLE/BALANCED）
        ranked = self._rank_by_strategy(history_boosted, strategy)

        if not ranked:
            raise NoSuitableToolError(f"未找到适合任务的工具: {task.description}")

        primary = ranked[0].descriptor

        # 4. 构建 Fallback 链（优先使用工具自身声明的，其次从候选中选不同来源）
        fallback_chain = self._build_fallback_chain(primary, ranked[1:])

        # 5. 检测工具组合需求（如"抓取网页并分析" → web_fetch + data_analyzer）
        composition = await self._detect_composition_need(task, primary)

        return ToolExecutionPlan(
            primary_tool=primary,
            fallback_chain=fallback_chain,
            composition=composition,
            selection_rationale=self._explain(ranked, strategy),
        )

    def _build_fallback_chain(
        self, primary: ToolCapabilityDescriptor, alternatives: List["ScoredTool"]
    ) -> List[ToolCapabilityDescriptor]:
        declared = [
            self.index._descriptors[fid]
            for fid in primary.fallback_tool_ids
            if fid in self.index._descriptors
        ]
        semantic = [
            t.descriptor for t in alternatives
            if t.descriptor.source != primary.source  # 不同来源，避免相同失败点
        ][:2]
        return declared + semantic
```

---

### 12.4 Fallback 感知执行器

```python
# agent_factory/engine/tool_executor.py

class FallbackAwareToolExecutor:
    """执行工具调用，自动处理失败和 Fallback，集成 Circuit Breaker。"""

    async def execute(
        self, plan: "ToolExecutionPlan", inputs: dict, context: AgentContext
    ) -> "ToolResult":

        attempt_chain = [plan.primary_tool] + plan.fallback_chain
        last_error = None

        for i, tool in enumerate(attempt_chain):
            cb = self._get_circuit_breaker(tool.tool_id)
            if cb.is_open():
                continue

            try:
                start = time.monotonic()
                result = await self._invoke_tool(tool, inputs, context)
                elapsed_ms = (time.monotonic() - start) * 1000

                cb.record_success()
                await self.tracker.record_success(tool.tool_id, context.task_type, elapsed_ms)

                if i > 0:
                    result.metadata["used_fallback"] = True
                    result.metadata["fallback_level"] = i
                return result

            except ToolExecutionError as e:
                cb.record_failure()
                last_error = e
                await self.tracker.record_failure(
                    tool.tool_id, context.task_type, type(e).__name__
                )

        raise AllToolsFailed(
            f"工具链全部失败，最后错误: {last_error}",
            attempted_tools=[t.tool_id for t in attempt_chain]
        )
```

---

### 12.5 工具使用追踪器（反馈闭环）

```python
# agent_factory/engine/tool_usage_tracker.py

class ToolUsageTracker:
    """追踪每个工具在每类任务上的成功率，数据回流给 ToolSelector 和 CapabilityIndex。"""

    async def record_success(self, tool_id: str, task_type: str, latency_ms: float):
        await self.db.execute("""
            INSERT INTO tool_usage (tool_id, task_type, success, latency_ms, timestamp)
            VALUES ($1, $2, TRUE, $3, NOW())
        """, tool_id, task_type, latency_ms)
        asyncio.create_task(self._update_descriptor_stats(tool_id))

    async def get_tool_stats(self, tool_id: str, task_type: str) -> Optional["ToolStats"]:
        return await self.db.fetchrow("""
            SELECT
                COUNT(*)                          AS sample_count,
                AVG(success::int)                 AS success_rate,
                AVG(latency_ms) FILTER(WHERE success) AS avg_latency_ms
            FROM tool_usage
            WHERE tool_id=$1 AND task_type=$2
              AND timestamp > NOW() - INTERVAL '30 days'
            GROUP BY tool_id, task_type
        """, tool_id, task_type)
```

---


## 13. 交付系统

> 本章为 v2.1 版本：Runtime Contract 增强。

> **替换声明**：v2.0 的“仅文件结构交付”模式已废弃，v2.1 交付包必须满足 Runtime Contract 并通过 Contract Validator。

### 13.1 交付产物结构

目标智能体的交付包结构根据 `target_language` 自动适配，以下分别列出：

**Python 交付包**（`target_language: "python"`）

```
{agent_name}/
├── agent.py                    # 主入口（可直接运行）
├── agent_identity.yaml         # 由Agentic Identity Architect生成
├── agent_config.yaml           # 智能体配置
├── system_prompt.md            # 系统提示词
├── requirements.txt            # 锁定版本的依赖清单（pip freeze生成）
├── mcp_config.yaml             # 由MCP Builder角色生成
├── skills/                     # 预装的Skill文件
├── tools/
├── tests/                      # pytest测试套件
├── docker/
│   ├── Dockerfile              # FROM python:3.12-slim
│   └── docker-compose.yml
├── docs/
│   ├── README.md               # 含 pip install + python agent.py 快速上手
│   ├── TUTORIAL.md
│   ├── API.md
│   └── ARCHITECTURE.md
├── factory_metadata.json       # 记录生产过程元数据（含target_language）
└── validation_report.json
```

**Node.js 交付包**（`target_language: "nodejs"`）

```
{agent_name}/
├── agent.ts                    # 主入口（TypeScript优先）
├── agent_identity.yaml
├── agent_config.yaml
├── system_prompt.md
├── package.json                # 含dependencies、devDependencies、scripts
├── package-lock.json           # 锁定版本（npm install --package-lock-only生成）
├── tsconfig.json               # TypeScript编译配置
├── mcp_config.yaml
├── skills/
├── tools/
├── tests/                      # jest / vitest测试套件
├── docker/
│   ├── Dockerfile              # FROM node:20-slim
│   └── docker-compose.yml
├── docs/
│   ├── README.md               # 含 npm install + npm start 快速上手
│   ├── TUTORIAL.md
│   ├── API.md
│   └── ARCHITECTURE.md
├── factory_metadata.json       # 含target_language: "nodejs"
└── validation_report.json
```

### 13.2 factory_metadata.json

```json
{
  "factory_version": "1.0",
  "agency_agents_version_hash": "abc123...",
  "production_timestamp": "2026-03-25T10:30:00Z",
  "execution_mode": "Standard",
  "target_language": "python",
  "runtime_version": "python:3.12-slim",
  "discussion_team": [
    {"slug": "senior-developer", "division": "engineering"},
    {"slug": "ai-engineer", "division": "engineering"},
    {"slug": "sprint-prioritizer", "division": "product"},
    {"slug": "agentic-identity-architect", "division": "specialized"}
  ],
  "discussion_rounds": 3,
  "key_decisions": [
    "选用 LangGraph 而非 AutoGen：理由是更好的状态管理",
    "使用 Qdrant 而非 Pinecone：理由是成本和自托管"
  ],
  "token_usage": {
    "discussion": 18500,
    "development": 72000,
    "testing": 15000,
    "total": 105500
  },
  "quality_gate_attempts": 1,
  "test_coverage": "87%"
}
```

---


### 13.3 运行时契约（AgentRuntimeContract）

#### 13.3.1 问题本质

没有运行时标准接口的交付物存在以下问题：
- 不同 agent 调用方式各异，无法统一编排
- 没有健康检查和就绪探针（无法接入 Kubernetes）
- 没有机器可读的能力声明（外部系统不知道这个 agent 能干什么）
- 没有资源限制约定（可能耗尽内存）

---

#### 13.4 AgentRuntimeContract 基类（含完整 Manifest Schema）

##### 13.4.1 AgentCapabilityManifest Schema（完整）

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "AgentCapabilityManifest",
  "type": "object",
  "required": [
    "agent_id",
    "agent_name",
    "version",
    "description",
    "supported_input_types",
    "supported_output_types",
    "primary_use_cases",
    "tools_available",
    "mcp_servers",
    "skills_loaded",
    "max_context_tokens",
    "max_response_tokens",
    "max_concurrent_sessions",
    "timeout_seconds",
    "required_env_vars",
    "required_services",
    "min_memory_mb",
    "factory_metadata"
  ],
  "properties": {
    "agent_id": { "type": "string", "minLength": 1 },
    "agent_name": { "type": "string", "minLength": 1 },
    "version": { "type": "string", "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$" },
    "description": { "type": "string" },
    "supported_input_types": { "type": "array", "items": { "type": "string" } },
    "supported_output_types": { "type": "array", "items": { "type": "string" } },
    "primary_use_cases": { "type": "array", "items": { "type": "string" } },
    "tools_available": { "type": "array", "items": { "type": "string" } },
    "mcp_servers": { "type": "array", "items": { "type": "string" } },
    "skills_loaded": { "type": "array", "items": { "type": "string" } },
    "max_context_tokens": { "type": "integer", "minimum": 1 },
    "max_response_tokens": { "type": "integer", "minimum": 1 },
    "max_concurrent_sessions": { "type": "integer", "minimum": 1 },
    "timeout_seconds": { "type": "integer", "minimum": 1 },
    "required_env_vars": { "type": "array", "items": { "type": "string" } },
    "required_services": { "type": "array", "items": { "type": "string" } },
    "min_memory_mb": { "type": "integer", "minimum": 64 },
    "factory_metadata": { "type": "object" }
  },
  "additionalProperties": false
}
```

##### 13.4.2 AgentRuntimeContract 参考实现

```python
# agent_factory/runtime/contract.py
# 所有由 Agent Factory 生成的 agent 必须继承此基类

from abc import ABC, abstractmethod
import asyncio
import os
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional, Dict, Any, List

@dataclass
class AgentCapabilityManifest:
    """机器可读的能力宣言。外部系统通过此文件了解 agent 能做什么。"""
    agent_id: str
    agent_name: str
    version: str
    description: str

    # 能力声明
    supported_input_types: List[str]     # ["text", "image", "file", "json"]
    supported_output_types: List[str]
    primary_use_cases: List[str]

    # 工具声明
    tools_available: List[str]
    mcp_servers: List[str]
    skills_loaded: List[str]

    # 限制声明（资源约定）
    max_context_tokens: int
    max_response_tokens: int
    max_concurrent_sessions: int
    timeout_seconds: int

    # 运行时需求
    required_env_vars: List[str]
    required_services: List[str]         # ["redis", "postgres", ...]
    min_memory_mb: int

    # 生产元数据
    factory_metadata: dict               # 参与角色、版本、讨论摘要等

@dataclass
class AgentInvokeRequest:
    session_id: str
    input: Any
    system_override: Optional[str] = None
    stream: bool = False
    timeout_override: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AgentInvokeResponse:
    session_id: str
    output: Any
    success: bool
    error: Optional[str] = None
    token_usage: Optional[dict] = None
    tool_calls_made: List[str] = field(default_factory=list)
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentRuntimeContract(ABC):
    """
    所有由 Agent Factory 生成的 agent 必须实现的运行时契约。
    packaging_node 的 ContractValidator 负责验证符合此契约。
    """

    def __init__(self):
        self._active_sessions = 0

    # ── 必须实现：核心调用接口
    @abstractmethod
    async def invoke(self, request: AgentInvokeRequest) -> AgentInvokeResponse:
        """同步调用，等待完整结果"""
        ...

    @abstractmethod
    async def stream(self, request: AgentInvokeRequest) -> AsyncIterator[str]:
        """流式调用，逐步输出"""
        ...

    @abstractmethod
    def get_manifest(self) -> AgentCapabilityManifest:
        """返回能力宣言（纯函数，无副作用）"""
        ...

    # ── 框架默认实现：运维接口（可覆盖）

    async def _ping_mcp_server(self, server: str) -> bool:
        """默认探针实现：子类可覆盖为真实网络探测。"""
        return True

    async def _ping_llm(self) -> str:
        """默认探针实现：子类可覆盖为真实模型连通性探测。"""
        return "ok"

    async def health_check(self) -> dict:
        """/health 端点，检查 MCP 连通性和 LLM 可用性"""
        checks = {}
        for server in self.get_manifest().mcp_servers:
            try:
                ok = await self._ping_mcp_server(server)
                checks[f"mcp.{server}"] = "ok" if ok else "degraded"
            except Exception:
                checks[f"mcp.{server}"] = "failed"
        checks["llm"] = await self._ping_llm()

        overall = "healthy"
        if any(v == "failed" for v in checks.values()):
            overall = "unhealthy"
        elif any(v == "degraded" for v in checks.values()):
            overall = "degraded"
        return {"status": overall, "checks": checks}

    async def ready_check(self) -> bool:
        """/ready 端点（Kubernetes readinessProbe）"""
        for env_var in self.get_manifest().required_env_vars:
            if not os.environ.get(env_var):
                return False
        return True

    async def graceful_shutdown(self, timeout_seconds: int = 30):
        """优雅关闭：等待进行中的请求完成"""
        deadline = asyncio.get_event_loop().time() + timeout_seconds
        while self._active_sessions > 0:
            if asyncio.get_event_loop().time() > deadline:
                break
            await asyncio.sleep(0.5)

    # ── 框架强制执行：资源限制
    async def _enforce_resource_limits(self, request: AgentInvokeRequest):
        manifest = self.get_manifest()
        if self._active_sessions >= manifest.max_concurrent_sessions:
            raise TooManyConcurrentSessionsError()
        if len(str(request.input)) > manifest.max_context_tokens * 4:
            raise InputTooLargeError()
```

---

#### 13.5 契约验证节点（集成到 packaging_node）

```python
# agent_factory/delivery/contract_validator.py

class AgentContractValidator:
    """在沙箱D中运行，验证生成的 agent 是否符合运行时契约。"""

    REQUIRED_METHODS = ["invoke", "stream", "get_manifest"]

    async def validate(self, agent_package_dir: str) -> "ContractValidationReport":
        issues = []

        # 1. 检查继承关系
        agent_class = self._import_agent_class(agent_package_dir)
        if not issubclass(agent_class, AgentRuntimeContract):
            issues.append(ContractIssue(
                severity="CRITICAL",
                message="主类未继承 AgentRuntimeContract"
            ))

        # 2. 检查必须实现的方法
        for method in self.REQUIRED_METHODS:
            if not hasattr(agent_class, method):
                issues.append(ContractIssue(
                    severity="CRITICAL", message=f"缺少必须方法: {method}"
                ))

        # 3. 检查 manifest 完整性
        try:
            manifest = agent_class().get_manifest()
            if not manifest.required_env_vars:
                issues.append(ContractIssue(
                    severity="WARNING",
                    message="required_env_vars 为空，可能遗漏必要的环境变量声明"
                ))
        except Exception as e:
            issues.append(ContractIssue(
                severity="CRITICAL", message=f"get_manifest() 异常: {e}"
            ))

        # 4. invoke() 冒烟测试
        smoke = await self._smoke_test_invoke(agent_package_dir)
        if not smoke.success:
            issues.append(ContractIssue(
                severity="CRITICAL", message=f"invoke() 冒烟测试失败: {smoke.error}"
            ))

        # 5. health_check 测试
        health = await self._test_health_check(agent_package_dir)
        if health.get("status") == "unhealthy":
            issues.append(ContractIssue(
                severity="WARNING", message=f"health_check 报告 unhealthy: {health}"
            ))

        return ContractValidationReport(
            passed=not any(i.severity == "CRITICAL" for i in issues),
            issues=issues
        )
```

---




## 13.6 语言感知打包器（LanguageAwarePackager）

### 13.6.1 设计动机

不同语言的依赖安装机制差异显著。如果打包器不区分语言，将导致：
- Python 包里生成了 `package.json`（无用文件）
- Node.js 包里的 `requirements.txt` 被误认为是 Python 项目
- Dockerfile 使用错误基础镜像，沙箱验证必然失败
- README 快速上手命令与实际运行时不一致

### 13.6.2 语言感知打包器核心实现

```python
# agent_factory/delivery/language_aware_packager.py

from enum import Enum
from pathlib import Path
from typing import Optional
import subprocess, json, textwrap

class TargetLanguage(str, Enum):
    PYTHON = "python"
    NODEJS = "nodejs"

class LanguageAwarePackager:
    """
    根据 target_language 生成正确的：
    1. 依赖清单（requirements.txt / package.json）
    2. Dockerfile（正确基础镜像 + 安装命令）
    3. README 快速上手命令
    4. 沙箱内依赖安装验证
    """

    def __init__(self, language: TargetLanguage):
        self.language = language

    # ── 1. 依赖清单生成 ─────────────────────────────────────────

    def generate_dependency_file(
        self,
        deps: list[str],
        dev_deps: Optional[list[str]] = None,
        output_dir: Path = Path(".")
    ) -> Path:
        """
        生成依赖清单文件。
        - Python: 生成 requirements.txt，版本号必须锁定
        - Node.js: 生成 package.json，包含 dependencies 和 devDependencies
        """
        if self.language == TargetLanguage.PYTHON:
            return self._write_requirements_txt(deps, output_dir)
        else:
            return self._write_package_json(deps, dev_deps or [], output_dir)

    def _write_requirements_txt(self, deps: list[str], output_dir: Path) -> Path:
        """
        Python 依赖格式：每行一个包，版本号必须精确锁定。
        示例：
            anthropic==0.40.0
            langchain-anthropic==0.3.10
            python-dotenv==1.0.1
        """
        content = "\n".join(deps) + "\n"
        path = output_dir / "requirements.txt"
        path.write_text(content, encoding="utf-8")
        return path

    def _write_package_json(
        self,
        deps: list[str],
        dev_deps: list[str],
        output_dir: Path,
        agent_name: str = "my-agent",
        version: str = "1.0.0",
    ) -> Path:
        """
        Node.js 依赖格式：标准 package.json，包含运行脚本。
        deps 格式：["@anthropic-ai/sdk@0.37.0", "dotenv@16.4.7"]
        """
        def parse_dep(dep_str: str) -> tuple[str, str]:
            # "@anthropic-ai/sdk@0.37.0" → ("@anthropic-ai/sdk", "0.37.0")
            if dep_str.startswith("@"):
                # scoped package: @scope/name@version
                parts = dep_str.rsplit("@", 1)
                return parts[0], parts[1] if len(parts) > 1 else "latest"
            else:
                parts = dep_str.split("@", 1)
                return parts[0], parts[1] if len(parts) > 1 else "latest"

        pkg = {
            "name": agent_name,
            "version": version,
            "description": f"Agent generated by Agent Factory",
            "main": "dist/agent.js",
            "scripts": {
                "start": "node dist/agent.js",
                "build": "tsc",
                "dev": "tsx agent.ts",
                "test": "jest"
            },
            "dependencies": {
                name: f"^{ver}" for name, ver in [parse_dep(d) for d in deps]
            },
            "devDependencies": {
                name: f"^{ver}" for name, ver in [parse_dep(d) for d in dev_deps]
            }
        }
        path = output_dir / "package.json"
        path.write_text(json.dumps(pkg, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    # ── 2. Dockerfile 生成 ──────────────────────────────────────

    def generate_dockerfile(self, output_dir: Path, agent_name: str = "agent") -> Path:
        """根据语言生成对应的 Dockerfile"""
        if self.language == TargetLanguage.PYTHON:
            content = self._python_dockerfile(agent_name)
        else:
            content = self._nodejs_dockerfile(agent_name)

        path = output_dir / "docker" / "Dockerfile"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def _python_dockerfile(self, agent_name: str) -> str:
        return textwrap.dedent(f"""\
            FROM python:3.12-slim

            WORKDIR /app

            # 安装系统依赖（可按需扩展）
            RUN apt-get update && apt-get install -y --no-install-recommends \\
                curl \\
                && rm -rf /var/lib/apt/lists/*

            # 先复制依赖清单并安装，利用Docker缓存层
            COPY requirements.txt .
            RUN pip install --no-cache-dir -r requirements.txt

            # 再复制源码
            COPY . .

            ENV PYTHONUNBUFFERED=1

            CMD ["python", "{agent_name}.py"]
        """)

    def _nodejs_dockerfile(self, agent_name: str) -> str:
        return textwrap.dedent(f"""\
            FROM node:20-slim

            WORKDIR /app

            # 安装系统依赖
            RUN apt-get update && apt-get install -y --no-install-recommends \\
                curl \\
                && rm -rf /var/lib/apt/lists/*

            # 先复制依赖清单并安装
            COPY package.json package-lock.json* ./
            RUN npm ci --only=production

            # TypeScript编译（如使用TS）
            COPY tsconfig.json* ./
            COPY . .
            RUN npm run build 2>/dev/null || true

            CMD ["node", "dist/{agent_name}.js"]
        """)

    # ── 3. 沙箱内依赖安装验证 ───────────────────────────────────

    async def verify_dependencies_in_sandbox(
        self,
        agent_package_dir: Path,
        docker_client,
        timeout_seconds: int = 120,
    ) -> "DependencyVerificationResult":
        """
        在沙箱D（全新容器）内真实安装依赖，验证：
        1. 依赖清单格式合法
        2. 所有包版本可解析（无冲突）
        3. 安装后主入口文件可导入（Python import / Node.js require）

        关键原则：不信任开发节点生成的依赖列表，必须实际跑一遍。
        """
        if self.language == TargetLanguage.PYTHON:
            return await self._verify_python_deps(agent_package_dir, docker_client, timeout_seconds)
        else:
            return await self._verify_nodejs_deps(agent_package_dir, docker_client, timeout_seconds)

    async def _verify_python_deps(self, pkg_dir: Path, docker_client, timeout: int):
        """
        在 python:3.12-slim 容器内：
        pip install -r requirements.txt --dry-run  ← 检查版本冲突
        pip install -r requirements.txt            ← 实际安装
        python -c "import agent"                  ← 导入验证
        """
        requirements = pkg_dir / "requirements.txt"
        if not requirements.exists():
            return DependencyVerificationResult(
                success=False,
                error="requirements.txt 不存在"
            )

        container = docker_client.containers.run(
            image="python:3.12-slim",
            command=f"""sh -c '
                pip install --no-cache-dir -r /app/requirements.txt 2>&1 &&
                python -c "import sys; sys.path.insert(0, \\"/app\\"); import agent; print(\\"IMPORT_OK\\")" 2>&1
            '""",
            volumes={str(pkg_dir): {"bind": "/app", "mode": "ro"}},
            detach=True,
            network_mode="bridge",   # 需要网络拉包
            mem_limit="512m",
            remove=True,
        )

        try:
            result = container.wait(timeout=timeout)
            logs = container.logs().decode()
            success = "IMPORT_OK" in logs and result["StatusCode"] == 0
            return DependencyVerificationResult(
                success=success,
                install_logs=logs,
                error=None if success else f"安装或导入失败:\n{logs}"
            )
        except Exception as e:
            return DependencyVerificationResult(success=False, error=str(e))

    async def _verify_nodejs_deps(self, pkg_dir: Path, docker_client, timeout: int):
        """
        在 node:20-slim 容器内：
        npm ci                                    ← 严格按 package-lock.json 安装
        node -e "require('./agent.js')"           ← 导入验证（编译后）
        """
        package_json = pkg_dir / "package.json"
        if not package_json.exists():
            return DependencyVerificationResult(
                success=False,
                error="package.json 不存在"
            )

        container = docker_client.containers.run(
            image="node:20-slim",
            command="""sh -c '
                npm ci --only=production 2>&1 &&
                node -e "try{require(\\\"./agent.js\\\");console.log(\\\"REQUIRE_OK\\\")}catch(e){console.error(e);process.exit(1)}" 2>&1
            '""",
            volumes={str(pkg_dir): {"bind": "/app", "mode": "rw"}},
            working_dir="/app",
            detach=True,
            network_mode="bridge",
            mem_limit="512m",
            remove=True,
        )

        try:
            result = container.wait(timeout=timeout)
            logs = container.logs().decode()
            success = "REQUIRE_OK" in logs and result["StatusCode"] == 0
            return DependencyVerificationResult(
                success=success,
                install_logs=logs,
                error=None if success else f"npm install 或 require 失败:\n{logs}"
            )
        except Exception as e:
            return DependencyVerificationResult(success=False, error=str(e))

    # ── 4. README 快速上手命令生成 ───────────────────────────────

    def generate_quickstart_section(self, agent_name: str, tools_needed: list[str]) -> str:
        """
        根据语言生成 README 的"快速上手"章节，确保命令与实际运行时一致。
        """
        env_vars = "\n".join(f"export {t.upper()}_API_KEY=..." for t in tools_needed)

        if self.language == TargetLanguage.PYTHON:
            return textwrap.dedent(f"""\
                ## 快速上手

                ### 1. 安装依赖
                ```bash
                pip install -r requirements.txt
                ```

                ### 2. 配置环境变量
                ```bash
                cp .env.example .env
                # 编辑 .env 填入以下 Key：
                {env_vars if env_vars else "# 本智能体无需外部 API Key"}
                ```

                ### 3. 运行
                ```bash
                python {agent_name}.py
                ```

                ### 4. 使用 Docker
                ```bash
                docker build -t {agent_name} -f docker/Dockerfile .
                docker run --env-file .env {agent_name}
                ```
            """)
        else:
            return textwrap.dedent(f"""\
                ## 快速上手

                ### 1. 安装依赖
                ```bash
                npm install
                ```

                ### 2. 配置环境变量
                ```bash
                cp .env.example .env
                # 编辑 .env 填入以下 Key：
                {env_vars if env_vars else "# 本智能体无需外部 API Key"}
                ```

                ### 3. 运行
                ```bash
                npm start
                # 或开发模式（热重载）：
                npm run dev
                ```

                ### 4. 测试
                ```bash
                npm test
                ```

                ### 5. 使用 Docker
                ```bash
                docker build -t {agent_name} -f docker/Dockerfile .
                docker run --env-file .env {agent_name}
                ```
            """)
```

### 13.6.3 依赖安装验证集成到打包节点

`LanguageAwarePackager.verify_dependencies_in_sandbox()` 在 `packaging_node` 调用 `AgentContractValidator` **之前**执行，依赖安装失败视为 CRITICAL 错误，进入失败恢复链：

```python
# agent_factory/delivery/packager.py（更新后）

async def packaging_node(state: FactoryStateV3) -> FactoryStateV3:
    language = TargetLanguage(state["target_language"])
    packager = LanguageAwarePackager(language)
    output_dir = Path(f"output/{state['agent_spec'].name}")

    # 步骤1：生成依赖清单
    packager.generate_dependency_file(
        deps=state["tech_spec"].dependencies,
        dev_deps=state["tech_spec"].dev_dependencies,
        output_dir=output_dir
    )

    # 步骤2：生成 Dockerfile
    packager.generate_dockerfile(output_dir, agent_name=state["agent_spec"].name)

    # 步骤3：生成 README（含语言对应快速上手命令）
    quickstart = packager.generate_quickstart_section(
        agent_name=state["agent_spec"].name,
        tools_needed=state["tech_spec"].tools_needed
    )
    (output_dir / "docs" / "README.md").write_text(quickstart)

    # 步骤4：沙箱内依赖安装验证（关键！）
    dep_result = await packager.verify_dependencies_in_sandbox(
        agent_package_dir=output_dir,
        docker_client=docker.from_env(),
        timeout_seconds=180,
    )
    if not dep_result.success:
        # 依赖安装失败 → 分类为 IMPORT_ERROR → 进入失败恢复
        raise DependencyInstallError(dep_result.error)

    # 步骤5：运行时契约验证
    validator = AgentContractValidator()
    contract_report = await validator.validate(str(output_dir))

    return {**state, "delivery_package": ..., "status": "packaged"}
```

---

```
agent_factory/
├── core/
│   ├── factory_graph.py            # LangGraph 主工作流图
│   └── state.py                    # 全局状态 TypedDict 定义
├── registry/
│   ├── loader.py                   # 动态注册表加载器（frontmatter解析）
│   ├── models.py                   # AgentMeta、Division枚举等数据模型
│   ├── factory_overrides.yaml      # 可选：覆盖自动推断的阶段映射
│   └── agency_agents/              # git submodule（147角色源文件）
├── router/
│   ├── domain_router.py            # 领域路由：147→20-30候选角色
│   └── dev_task_router.py          # 开发任务分流：TaskType→角色映射
├── dispatcher/
│   ├── master_dispatcher.py        # 主控调度器（反馈闭环版）
│   ├── feedback_store.py           # DispatchOutcome持久化（pgvector）
│   └── feedback_scorer.py          # 反馈感知评分器
├── discussion/
│   ├── parallel_graph.py           # 并行异步讨论图（Send API）
│   ├── bulletin_board.py           # 异步公告板（线程安全）
│   ├── token_budget.py             # Token预算管控
│   └── synthesis.py                # 讨论结果→TechSpec综合节点
├── engine/
│   ├── tool_descriptor.py          # 工具能力描述符
│   ├── tool_capability_index.py    # 工具向量索引（语义检索）
│   ├── tool_selector.py            # 智能工具选择器（含Fallback链）
│   ├── tool_executor.py            # Fallback感知执行器（Circuit Breaker）
│   ├── tool_usage_tracker.py       # 工具使用追踪（反馈闭环）
│   ├── skill_registry.py           # Skill文件管理
│   └── mcp_pool.py                 # MCP服务器连接池
├── recovery/
│   ├── failure_taxonomy.py         # 失败分类体系（Domain×Type×Severity）
│   ├── failure_classifier.py       # 规则树+LLM兜底分类器
│   ├── strategy_engine.py          # 10种恢复策略引擎
│   └── recovery_journal.py         # 失败知识库（回流给Dispatcher）
├── runtime/
│   └── contract.py                 # AgentRuntimeContract基类 + Manifest Schema
├── development/
│   ├── graph.py                    # 并行开发子图
│   └── nodes.py                    # 各开发角色节点实现
├── testing/
│   ├── graph.py                    # 5类测试并行子图
│   └── reporters.py                # 测试报告生成
├── sandbox/
│   ├── discussion_sandbox.py       # 沙箱A：进程级角色隔离
│   ├── code_sandbox.py             # 沙箱B：Docker代码执行隔离
│   ├── test_sandbox.py             # 沙箱C：容器级+网络模拟测试
│   ├── delivery_sandbox.py         # 沙箱D：VM级交付验证
│   └── game_sandbox.py             # 游戏引擎专用沙箱（Unity/Godot）
├── delivery/
│   ├── packager.py                 # 打包节点（调用LanguageAwarePackager）
│   ├── language_aware_packager.py  # 语言感知打包器（Python/Node.js依赖生成+验证）
│   ├── tutorial_generator.py       # 使用教程生成
│   └── contract_validator.py       # 运行时契约验证（沙箱D内运行）
├── cost/
│   ├── estimator.py                # 任务前成本预估
│   └── controller.py               # 运行中Token预算管控
├── observability/
│   ├── langsmith_tracer.py         # LangSmith集成
│   └── otel_exporter.py            # OpenTelemetry导出
├── api/
│   ├── main.py                     # FastAPI主入口
│   ├── ws.py                       # WebSocket实时进度推送
│   └── checkpoints.py              # 三个人机协作检查点API
└── config/
    └── settings.py                 # 全局配置（env var管理）
```

---

## 15. 推荐开发流程与注意事项

### 15.1 总体开发阶段划分

建议按以下 5 个阶段顺序推进，每个阶段有明确的入口条件和完成标准。

```
阶段0：环境搭建（1-2天）
  → 阶段1：核心骨架（1周）
    → 阶段2：角色与调度（2周）
      → 阶段3：讨论与执行（2-3周）
        → 阶段4：工具引擎与交付（2周）
          → 阶段5：反馈闭环与生产化（持续迭代）
```

---

### 15.2 阶段0：环境搭建

**目标**：一键启动本地开发环境，所有依赖就绪。

**工作清单**：

1. Python 3.12+ 虚拟环境，安装核心依赖：
```bash
pip install langgraph langchain-anthropic python-frontmatter \
            asyncpg pgvector docker fastapi uvicorn \
            langsmith opentelemetry-api opentelemetry-sdk
```

2. 启动基础服务（`docker-compose.yml`）：
```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: agent_factory
      POSTGRES_PASSWORD: dev_secret
    ports: ["5432:5432"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
```

3. 初始化 agency-agents 子模块：
```bash
git submodule add https://github.com/msitarzewski/agency-agents \
    agent_factory/registry/agency_agents
git submodule update --init --recursive
```

4. 配置环境变量（`.env`）：
```
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=postgresql://postgres:dev_secret@localhost:5432/agent_factory
LANGSMITH_API_KEY=ls__...    # 可选，用于可观测性
```

**注意点**：
- pgvector 扩展需要在 postgres 中手动执行 `CREATE EXTENSION vector;`
- Docker Desktop 需开启 Linux 容器模式（沙箱B/C需要）
- `ANTHROPIC_API_KEY` 必须有足够额度，Standard模式单次任务约消耗 $1-3

---

### 15.3 阶段1：核心骨架

**目标**：主工作流图跑通，能接收用户输入并走完整个生命周期（哪怕每个节点只是打印日志）。

**优先实现**：
1. `core/state.py` — `FactoryState` TypedDict 完整定义
2. `core/factory_graph.py` — LangGraph 主图，所有节点先用 stub 实现
3. `api/main.py` — FastAPI + WebSocket，能接收请求并推送进度
4. `config/settings.py` — 统一配置管理

**stub节点示例**（先跑通流程）：
```python
async def intake_node(state: FactoryState) -> FactoryState:
    print(f"[Intake] 收到需求：{state['user_input'][:50]}")
    return {**state, "agent_spec": {"name": "test", "domain": "general"}, "status": "intake_done"}
```

**完成标准**：`curl -X POST /api/factory/start -d '{"input":"帮我做一个天气查询代理"}'` 能收到 session_id，WebSocket 能收到各阶段状态推送。

**注意点**：
- LangGraph 的 `interrupt_before` 要在这里就配置好，不要等到后期补
- `PostgresSaver` checkpointer 在这里接入，确保 session 可断点续传
- State 的字段要设计得足够宽松，避免后期频繁改 TypedDict

---

### 15.4 阶段2：角色注册表与调度器

**目标**：AgentRegistry 能加载全部 147 个角色，MasterDispatcher 能根据需求返回合理的派遣计划。

**优先实现**：
1. `registry/models.py` — `AgentMeta`、`Division` 枚举、`AgentCapability`
2. `registry/loader.py` — `AgentRegistry` 动态加载（先实现基础版，不含向量索引）
3. `router/domain_router.py` — `DomainRouter`（先用关键词匹配，不用向量）
4. `dispatcher/master_dispatcher.py` — 基础版（纯 LLM 决策，不含反馈闭环）

**验证方式**：
```python
registry = AgentRegistry(Path("agent_factory/registry/agency_agents"))
print(f"加载角色数：{len(registry.list_all())}")  # 应 >= 100

dispatcher = MasterDispatcher(registry)
plan = await dispatcher.dispatch_phase1(
    AgentSpec(user_input="我想做一个GitHub PR自动审查代理"),
    ExecutionMode.STANDARD
)
print(plan.discussion_team)  # 应包含 senior-developer、ai-engineer 等
```

**注意点**：
- agency-agents 仓库的 Markdown 文件格式不统一，`frontmatter.load()` 要做异常捕获
- 某些 Markdown 文件没有 frontmatter，`slug` 直接用文件名（`path.stem`）
- 强制角色列表（`MANDATORY_DISCUSSION_ROLES`）要在这里就写死，否则后期讨论团队质量没保障
- `MasterDispatcher` 的 LLM 调用建议用 `claude-haiku` 而不是 `opus`，降低调度成本

---

### 15.5 阶段3：讨论子图与开发执行

**目标**：讨论阶段产出真实可用的 `TechSpec`，开发阶段能生成目标智能体的代码骨架。

**优先实现**：
1. `discussion/bulletin_board.py` — `BulletinBoard` 和 `BulletinPost`
2. `discussion/parallel_graph.py` — 并行讨论图（`round_fan_out` + `role_respond` + `round_collect`）
3. `discussion/synthesis.py` — 综合节点，输出结构化 `TechSpec`
4. `development/graph.py` — 开发子图（先实现串行版，后续改并行）
5. `development/nodes.py` — Backend Architect、AI Engineer 等核心角色节点

**注意点**：
- LangGraph `Send` API 并行讨论时，`round_collect` 节点必须用 `Annotated[List, operator.add]` 接收多个角色的输出，否则只能收到最后一个角色的结果
- 每个角色节点的 LLM 调用**必须加超时**（建议 120 秒），防止单个角色卡死整个讨论轮次
- `BulletinBoard` 的快照（`read_all()`）在轮次开始时就固定，本轮新发言不影响本轮其他角色的上下文，这是并行讨论一致性的关键
- 讨论轮次上限建议从 2 轮开始测试，不要一开始就设 6 轮，成本很高
- `TechSpec` 输出格式用 `with_structured_output(TechSpec)` 强制结构化，不要用字符串解析

---

### 15.6 阶段4：工具引擎与交付系统

**目标**：生成的智能体能拿到就运行，工具调用有 Fallback 保障，交付包符合运行时契约。

**优先实现**：
1. `engine/tool_descriptor.py` — 内置工具的 `ToolCapabilityDescriptor` 定义
2. `engine/tool_selector.py` — `ToolSelector` 基础版（先用规则匹配，后加向量索引）
3. `engine/tool_executor.py` — `FallbackAwareToolExecutor`（Circuit Breaker 优先实现）
4. `runtime/contract.py` — `AgentRuntimeContract` 基类
5. `delivery/contract_validator.py` — `AgentContractValidator`
6. `sandbox/code_sandbox.py` — 沙箱B Docker隔离（这是安全基线，不能省略）

**注意点**：
- `ToolCapabilityIndex` 的向量索引建议放到阶段5再做，阶段4先用工具ID直接匹配（能跑通即可）
- 沙箱B的 Docker 容器必须设置 `mem_limit`、`cpu_quota`、`network_mode: none`，否则生成的代码可能做任何事
- `AgentRuntimeContract` 的 `get_manifest()` 方法要在代码生成时就由角色节点自动填充，不要让用户手动写
- 沙箱D验证时从零依赖安装，所以 `requirements.txt` 的版本号必须锁定（`pip freeze` 而不是手写）

---

### 15.7 阶段5：反馈闭环与生产化

**目标**：调度器开始从历史任务中学习，系统具备生产级可靠性。

**优先实现**：
1. `dispatcher/feedback_store.py` — `DispatchOutcomeStore`（pgvector）
2. `dispatcher/feedback_scorer.py` — `FeedbackAwareScorer`（3条历史才启用）
3. `recovery/` — 全套失败恢复（`failure_classifier` + `strategy_engine` + `recovery_journal`）
4. `observability/` — LangSmith + OpenTelemetry 接入
5. `cost/` — Token预算管控（`CostController`）

**注意点**：
- pgvector 的 HNSW 索引在数据量少时查询很快，但插入时 `ef_construction` 参数影响索引质量，建议用默认值 64
- 反馈闭环的`FeedbackAwareScorer` 要设置冷启动门槛（`sample_count >= 3`），否则单条失败记录会严重拉低组合得分
- `recovery_journal` 的数据要定期查看，它是系统最重要的"经验积累"，对调优调度策略有直接价值
- LangSmith trace 数据量增长很快，建议设置 30 天自动清理策略

---

### 15.8 关键注意事项汇总

| 类别 | 注意点 | 严重程度 |
|------|--------|---------|
| **安全** | 沙箱B必须启用，所有生成代码在容器内执行 | 🔴 阻断 |
| **安全** | MCP服务器的 API Key 不能写入生成的代码，只能引用环境变量 | 🔴 阻断 |
| **语言** | `target_language` 在检查点1锁定后不可更改，代码生成节点必须读取此字段 | 🔴 阻断 |
| **语言** | Python包版本必须精确锁定（`==`），Node.js使用`package-lock.json`+`npm ci` | 🔴 阻断 |
| **语言** | 依赖安装验证必须在真实容器内执行，不能仅凭 dry-run 判断 | 🟡 重要 |
| **语言** | Node.js TypeScript项目需同时生成 `tsconfig.json` 和 `dist/` 编译步骤 | 🟡 重要 |
| **成本** | claude-opus 只用于讨论和关键决策，其余节点用 claude-haiku | 🟡 重要 |
| **成本** | Token预算管控从第一天就加入，否则测试阶段成本失控 | 🟡 重要 |
| **并发** | `BulletinBoard` 的 asyncio.Lock 不能省略，并行角色会发生写冲突 | 🔴 阻断 |
| **状态** | LangGraph checkpointer 的 session_id 必须唯一且幂等，避免状态污染 | 🟡 重要 |
| **数据** | agency-agents 子模块的更新不要在任务运行中触发，会导致角色定义变化 | 🟡 重要 |
| **测试** | 每个角色节点需要独立单测，验证 system_prompt 注入正确 | 🟢 建议 |
| **观测** | LangSmith 从阶段1就接入，不要等到生产再加 | 🟢 建议 |
| **契约** | 生成的 agent.py / agent.ts 必须通过 ContractValidator，否则不允许交付 | 🔴 阻断 |


---

## 17. 核心模块代码实现建议（完整实现参考）

> 本节内容源自《Agent Factory 核心模块代码实现建议》（Manus AI, 2026-03-30），依据本文档主技术方案及 LangGraph 最新最佳实践，提供各核心模块的详尽可落地代码实现。凡与前述章节描述一致处，以本节代码为权威实现参考；两处有差异时，本节提供更细粒度的实现细节。

本文档旨在根据用户提供的《Agent Factory — 智能体工厂完整技术方案》[1] 和 LangGraph 框架的最新特性与最佳实践，为核心模块提供详尽、可落地的代码实现建议。

### 17.1. 整体架构与 LangGraph 主工作流

Agent Factory 的核心是一个基于 LangGraph 的状态图（StateGraph），它将整个智能体生成流程抽象为一系列节点和边，并利用 LangGraph 的状态管理和条件路由能力，实现了复杂的多阶段、多角色协作工作流。主工作流图（`FactoryGraph`）的定义在技术方案的 `11.1 主工作流图` [1] 中有详细描述。

#### 17.1.1 `FactoryStateV3` 状态管理

`FactoryStateV3` 是整个 LangGraph 状态图的共享状态，它是一个 `TypedDict`，用于在不同节点之间传递和存储任务的上下文信息。其关键字段包括：

| 字段名 | 类型 | 描述 | 备注 |
|---|---|---|---|
| `session_id` | `str` | 任务会话唯一标识符 | | 
| `user_input` | `str` | 用户的原始需求输入 | | 
| `execution_mode` | `ExecutionMode` | 执行模式（Fast/Standard/Thorough） | 影响讨论团队规模、轮次、成本预算等 |
| `target_language` | `str` | 目标智能体的开发语言（"python" / "nodejs"） | 在 `检查点1` 确认后锁定 |
| `agent_spec` | `Optional[AgentSpec]` | 经过 IntakeAgent 解析后的智能体规格 | | 
| `domain` | `Optional[str]` | 任务所属领域 | 由 `DomainRouter` 识别 |
| `cost_estimate` | `Optional[CostEstimate]` | 任务成本预估 | | 
| `dispatch_plan_phase1` | `Optional[DispatchPlan]` | 讨论阶段的角色调度计划 | | 
| `tech_spec` | `Optional[TechSpec]` | 讨论阶段产出的技术规格书 | | 
| `dispatch_plan_phase2` | `Optional[DispatchPlan]` | 开发阶段的角色调度计划 | | 
| `development_artifacts` | `dict` | 开发阶段产出的代码、配置等 | | 
| `test_report` | `Optional[TestReport]` | 测试报告 | | 
| `retry_count` | `int` | 失败重试次数 | | 
| `failure` | `Optional[ClassifiedFailure]` | 结构化失败对象 | | 
| `recovery_result` | `Optional[RecoveryResult]` | 失败恢复策略结果 | | 
| `failed_node` | `Optional[str]` | 导致失败的节点名称 | | 
| `delivery_package` | `Optional[DeliveryPackage]` | 最终交付的智能体包 | | 
| `status` | `str` | 当前任务状态 | | 
| `token_usage` | `dict` | Token 消耗统计 | | 

#### 17.1.2 `build_factory_graph_v3()` 主图构建

主图的构建通过 `build_factory_graph_v3()` 函数实现，它定义了整个工厂的流程。核心实现思路如下：

```python
# agent_factory/core/factory_graph.py

from langgraph.graph import StateGraph, END
from langgraph.checkpoint import PostgresSaver
from typing import TypedDict, Optional
import os

# 导入所有节点函数和类型定义
from .nodes import (
    intake_node, domain_router_node, cost_estimate_node, dispatch_phase1_node,
    discussion_node, dispatch_phase2_node, development_node, quality_gate_node,
    packaging_node, delivery_node, failure_classifier_node, recovery_strategy_node,
    targeted_remediation_node, human_recovery_node, graceful_packager_node
)
from .types import (
    ExecutionMode, AgentSpec, CostEstimate, DispatchPlan, TechSpec, TestReport,
    ClassifiedFailure, RecoveryResult, DeliveryPackage
)

class FactoryStateV3(TypedDict):
    session_id: str
    user_input: str
    execution_mode: ExecutionMode
    target_language: str
    agent_spec: Optional[AgentSpec]
    domain: Optional[str]
    cost_estimate: Optional[CostEstimate]
    dispatch_plan_phase1: Optional[DispatchPlan]
    tech_spec: Optional[TechSpec]
    dispatch_plan_phase2: Optional[DispatchPlan]
    development_artifacts: dict
    test_report: Optional[TestReport]
    retry_count: int
    failure: Optional[ClassifiedFailure]
    recovery_result: Optional[RecoveryResult]
    failed_node: Optional[str]
    delivery_package: Optional[DeliveryPackage]
    status: str
    token_usage: dict
    human_decision: Optional[str] # 用于人机协作检查点

def build_factory_graph_v3() -> StateGraph:
    graph = StateGraph(FactoryStateV3)

    # 核心节点定义
    graph.add_node("intake", intake_node)
    graph.add_node("domain_router", domain_router_node)
    graph.add_node("cost_estimate", cost_estimate_node)
    graph.add_node("dispatch_phase1", dispatch_phase1_node)
    graph.add_node("discussion", discussion_node)
    graph.add_node("dispatch_phase2", dispatch_phase2_node)
    graph.add_node("development", development_node)
    graph.add_node("quality_gate", quality_gate_node)
    graph.add_node("packaging", packaging_node)
    graph.add_node("delivery", delivery_node)

    # 失败恢复链节点
    graph.add_node("failure_classifier", failure_classifier_node)
    graph.add_node("recovery_strategy", recovery_strategy_node)
    graph.add_node("targeted_remediation", targeted_remediation_node)
    graph.add_node("human_recovery", human_recovery_node)
    graph.add_node("graceful_packager", graceful_packager_node)

    # 定义边和条件路由
    graph.set_entry_point("intake")
    graph.add_edge("intake", "domain_router")
    graph.add_edge("domain_router", "cost_estimate")
    graph.add_edge("cost_estimate", "dispatch_phase1")

    # 讨论阶段的条件路由：Fast 模式跳过讨论
    graph.add_conditional_edges(
        "dispatch_phase1",
        lambda state: "skip_discussion" if state.get("execution_mode") == ExecutionMode.FAST else "discussion",
        {"discussion": "discussion", "skip_discussion": "dispatch_phase2"}
    )
    graph.add_edge("discussion", "dispatch_phase2")
    graph.add_edge("dispatch_phase2", "development")
    graph.add_edge("development", "quality_gate")

    # 质量门禁的条件路由：通过则打包，失败则进入失败分类器
    graph.add_conditional_edges(
        "quality_gate",
        lambda state: "pass" if state.get("test_report", {}).get("passed") else "fail", # 假设 test_report 中有 passed 字段
        {
            "pass": "packaging",
            "fail": "failure_classifier",
        }
    )

    # 失败恢复链的路由
    graph.add_edge("failure_classifier", "recovery_strategy")
    graph.add_conditional_edges(
        "recovery_strategy",
        lambda state: state.get("recovery_result", {}).get("action", "escalate_to_human").value, # 默认人工介入
        {
            "retry_immediate":    lambda state: state.get("failed_node"),
            "retry_with_backoff": lambda state: state.get("failed_node"),
            "retry_with_context": lambda state: state.get("failed_node"),
            "substitute_role":    "targeted_remediation",
            "graceful_degrade":   "graceful_packager",
            "escalate_to_human":  "human_recovery",
        }
    )

    graph.add_edge("targeted_remediation", "quality_gate") # 修复后重新测试
    graph.add_edge("graceful_packager", "delivery")       # 降级直接交付

    # 人工恢复后的决策
    graph.add_conditional_edges(
        "human_recovery",
        lambda state: state.get("human_decision"),
        {
            "retry":   lambda state: state.get("failed_node"),
            "degrade": "graceful_packager",
            "abort":   END
        }
    )

    graph.add_edge("packaging", "delivery")
    graph.add_edge("delivery", END)

    return graph.compile(
        checkpointer=PostgresSaver.from_conn_string(os.environ["DATABASE_URL"]),
        interrupt_before=["dispatch_phase1", "dispatch_phase2", "delivery"]
    )
```

**关键点：**
*   **节点定义：** 每个业务逻辑单元（如 `intake_node`, `discussion_node`）被定义为一个 LangGraph 节点。这些节点接收 `FactoryStateV3` 作为输入，并返回更新后的状态。节点函数应是异步的 (`async def`)。
*   **条件路由：** 使用 `add_conditional_edges` 实现基于状态的动态流程控制，例如根据 `execution_mode` 跳过讨论阶段，或根据 `quality_gate` 的结果决定是进入打包还是失败恢复流程。
*   **失败恢复链：** 整个失败恢复机制被集成到主图中，形成一个独立的子图，确保系统在遇到问题时能够智能地尝试恢复或寻求人工介入。
*   **人机协作检查点：** 利用 LangGraph 的 `interrupt_before` 功能，在 `dispatch_phase1` (需求确认+语言选择)、`dispatch_phase2` (技术规格书审查) 和 `delivery` (交付预览) 之前暂停，等待用户确认或干预。这与技术方案 `10. 人机协作检查点` [1] 的要求一致。
*   **状态持久化：** 使用 `PostgresSaver` 作为 `checkpointer`，确保任务状态在中断和恢复之间能够持久化，这对于长流程和人机协作至关重要。

### 17.2. 智能体注册表 (`AgentRegistry`)

`AgentRegistry` 是 Agent Factory 的核心组件之一，负责动态加载、管理和同步所有可用的智能体角色。技术方案的 `3.14 动态注册表加载器` [1] 提供了详细的设计和部分代码。

#### 17.2.1 `AgentRegistry` 类实现

```python
# agent_factory/registry/loader.py

import subprocess
from pathlib import Path
from typing import Dict, List, Optional
import frontmatter
import yaml
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class Division(str, Enum):
    ENGINEERING = "engineering"
    DESIGN = "design"
    MARKETING = "marketing"
    SALES = "sales"
    PRODUCT = "product"
    PROJECT_MANAGEMENT = "project-management"
    TESTING = "testing"
    SUPPORT = "support"
    SPATIAL_COMPUTING = "spatial-computing"
    SPECIALIZED = "specialized"
    GAME_DEVELOPMENT = "game-development"
    ACADEMIC = "academic"

@dataclass
class AgentMeta:
    slug: str
    name: str
    description: str
    color: str
    emoji: str
    vibe: str
    division: Division
    services: List[str]
    system_prompt: str
    capability: List[str] # 自动推断的能力标签
    factory_phases: List[str] # 适用于工厂的阶段 (discussion, development, testing, delivery)
    is_mandatory_discussion: bool
    is_mandatory_when_tools: bool

# 12个部门目录（含paid-media，统计时归入marketing）
DIVISION_DIRS = [
    "engineering", "design", "marketing", "paid-media",
    "sales", "product", "project-management", "testing",
    "support", "spatial-computing", "specialized",
    "game-development", "academic"
]

# 默认部门归属（paid-media → marketing统计）
DIR_TO_DIVISION = {
    "engineering": Division.ENGINEERING,
    "design": Division.DESIGN,
    "marketing": Division.MARKETING,
    "paid-media": Division.MARKETING,  # 归入市场部统计
    "sales": Division.SALES,
    "product": Division.PRODUCT,
    "project-management": Division.PROJECT_MANAGEMENT,
    "testing": Division.TESTING,
    "support": Division.SUPPORT,
    "spatial-computing": Division.SPATIAL_COMPUTING,
    "specialized": Division.SPECIALIZED,
    "game-development": Division.GAME_DEVELOPMENT,
    "academic": Division.ACADEMIC,
}

# 必须参与讨论的角色（强制规则）
MANDATORY_DISCUSSION_ROLES = {
    "senior-developer",           # 架构把关
    "ai-engineer",                # AI技术选型
    "sprint-prioritizer",         # 需求拆解
    "agentic-identity-architect", # 智能体身份设计（Specialized部门）
}

# MCP Builder：当目标代理需要外部工具时强制参与开发阶段
MANDATORY_WHEN_TOOLS_NEEDED = {"mcp-builder"}

class AgentRegistry:
    def __init__(self, repo_path: Path, auto_sync: bool = False):
        self.repo_path = repo_path
        self._agents: Dict[str, AgentMeta] = {}
        self._version_hash: str = ""
        self._load_all()
        if auto_sync:
            self._start_background_sync()

    def _load_all(self):
        self._agents.clear()
        for division_dir in DIVISION_DIRS:
            division_path = self.repo_path / division_dir
            if not division_path.exists():
                continue
            division = DIR_TO_DIVISION[division_dir]
            for md_file in division_path.rglob("*.md"):
                if md_file.name.startswith("_") or md_file.name == "README.md":
                    continue
                meta = self._parse_agent_file(md_file, division)
                if meta:
                    self._agents[meta.slug] = meta

        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.repo_path, capture_output=True, text=True
        )
        self._version_hash = result.stdout.strip()

    def _parse_agent_file(self, path: Path, division: Division) -> Optional[AgentMeta]:
        try:
            post = frontmatter.load(path)
        except Exception as e:
            logger.warning(f"无法解析角色文件 {path}: {e}")
            return None

        slug = path.stem
        fm = post.metadata
        body = post.content

        capability = self._infer_capability(body, slug, division)
        phases = self._infer_phases(slug, division, capability)
        
        return AgentMeta(
            slug=slug,
            name=fm.get("name", slug.replace("-", " ").title()),
            description=fm.get("description", ""),
            color=fm.get("color", "gray"),
            emoji=fm.get("emoji", "🤖"),
            vibe=fm.get("vibe", ""),
            division=division,
            services=fm.get("services", []),
            system_prompt=body,
            capability=capability,
            factory_phases=phases,
            is_mandatory_discussion=(slug in MANDATORY_DISCUSSION_ROLES),
            is_mandatory_when_tools=(slug in MANDATORY_WHEN_TOOLS_NEEDED),
        )

    def _infer_capability(self, body: str, slug: str, division: Division) -> List[str]:
        # TODO: 实现更复杂的关键词提取和LLM推断逻辑
        # 示例：根据 system_prompt 内容推断能力标签
        capabilities = []
        if "代码生成" in body or "编程" in body: capabilities.append("code_generation")
        if "测试" in body or "QA" in body: capabilities.append("testing")
        if "架构" in body or "设计" in body: capabilities.append("architecture_design")
        return capabilities

    def _infer_phases(self, slug: str, division: Division, capability: List[str]) -> List[str]:
        # TODO: 实现更复杂的阶段推断逻辑，可以结合部门、能力和强制规则
        phases = []
        if slug in MANDATORY_DISCUSSION_ROLES: phases.append("discussion")
        if slug in MANDATORY_WHEN_TOOLS_NEEDED: phases.append("development")
        # 默认情况下，所有角色都可能参与讨论和开发
        if "discussion" not in phases: phases.append("discussion")
        if "development" not in phases: phases.append("development")
        return list(set(phases))

    def sync_from_remote(self):
        subprocess.run(["git", "pull", "origin", "main"], cwd=self.repo_path)
        old_count = len(self._agents)
        self._load_all()
        new_count = len(self._agents)
        if new_count > old_count:
            logger.info(f"AgentRegistry 更新：新增 {new_count - old_count} 个角色")

    def get_agent_meta(self, slug: str) -> Optional[AgentMeta]:
        return self._agents.get(slug)

    def get_all_agents(self) -> Dict[str, AgentMeta]:
        return self._agents

    def get_agents_by_division(self, division: Division) -> List[AgentMeta]:
        return [meta for meta in self._agents.values() if meta.division == division]

    def _start_background_sync(self):
        # TODO: 实现后台定时同步逻辑，例如使用 APScheduler 或 asyncio.create_task
        logger.info("后台自动同步已启动 (待实现)")

```

**关键点：**
*   **动态加载：** `_load_all` 方法遍历预定义的部门目录 (`DIVISION_DIRS`)，查找所有 Markdown 文件，并使用 `frontmatter` 库解析文件头部的 YAML 元数据和文件体作为系统提示词。
*   **能力推断：** `_infer_capability` 和 `_infer_phases` 方法负责从角色的 `system_prompt` 或其他元数据中自动推断其能力标签和适用的工厂阶段。这部分可以结合 LLM 进行更智能的推断，以适应社区贡献的新角色。
*   **Git 同步：** `sync_from_remote` 方法通过执行 `git pull` 命令，实现从远程仓库同步最新的角色定义，并自动重新加载注册表。后台同步 (`_start_background_sync`) 确保注册表始终保持最新。
*   **强制规则：** `MANDATORY_DISCUSSION_ROLES` 和 `MANDATORY_WHEN_TOOLS_NEEDED` 确保在角色选择时，某些关键角色（如 `senior-developer`, `ai-engineer`, `mcp-builder`）能够被强制包含，以满足技术方案的硬性要求。

### 17.3. Intake 与 智能角色选择算法

Intake 阶段负责解析用户需求，并结合 `DomainRouter` 和其他选择机制，初步筛选出参与后续讨论和开发的角色。技术方案的 `4. 智能角色选择算法` [1] 详细阐述了三层选择机制。

#### 17.3.1 `intake_node` 实现

`intake_node` 是 LangGraph 中的第一个节点，它接收用户输入，并利用 LLM 将其解析为结构化的 `AgentSpec`。同时，它会处理目标语言的选择和确认。

```python
# agent_factory/core/nodes.py

from typing import Any, Dict, List
from langchain_anthropic import ChatAnthropic
import json, re
from .types import AgentSpec, FactoryStateV3, ExecutionMode

async def intake_node(state: FactoryStateV3) -> FactoryStateV3:
    user_input = state["user_input"]
    target_language = state["target_language"]
    session_id = state["session_id"]

    llm = ChatAnthropic(model="claude-opus-4-5", temperature=0) # 使用更强大的模型进行需求解析
    
    prompt = f"""
你是需求分析专家。用户想创建一个智能体，运行时语言已确认为：{target_language.upper()}

用户需求："{user_input}"

请提取：
1. 智能体名称（英文，snake_case）
2. 核心功能（1-3条）
3. 需要的外部工具（web_search/code_exec/file_ops/none，根据需求判断）
4. 目标用户
5. 依赖包列表（适用于 {target_language} 的真实包名，必须写明版本号）
   - Python 示例：["anthropic==0.40.0", "python-dotenv==1.0.1"]
   - Node.js 示例：["@anthropic-ai/sdk@0.37.0", "dotenv@16.4.7"]

以JSON格式返回，只返回JSON不要其他内容。字段：name, purpose, tools, target_user, dependencies
"""

    result = await llm.ainvoke(prompt)
    text = result.content
    match = re.search(r'\{{.*\}}', text, re.DOTALL)
    
    parsed_spec_data = {}
    if match:
        try:
            parsed_spec_data = json.loads(match.group())
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}, 原始LLM输出: {text}")
            # Fallback to default spec if parsing fails
            parsed_spec_data = {"name": "my_agent", "purpose": [], "tools": ["none"], "target_user": "general", "dependencies": []}
    else:
        logger.warning(f"LLM未返回有效JSON, 原始LLM输出: {text}")
        parsed_spec_data = {"name": "my_agent", "purpose": [], "tools": ["none"], "target_user": "general", "dependencies": []}

    # 确保 AgentSpec 结构完整
    agent_spec = AgentSpec(
        name=parsed_spec_data.get("name", "my_agent"),
        purpose=parsed_spec_data.get("purpose", []), 
        tools=parsed_spec_data.get("tools", ["none"]),
        target_user=parsed_spec_data.get("target_user", "general"),
        dependencies=parsed_spec_data.get("dependencies", []),
        target_language=target_language # 从状态中获取并设置
    )

    # TODO: 语言选择的置信度判断和用户确认逻辑
    # 技术方案中提到：若推断置信度 < 0.6，target_language 为 null，强制要求用户选择
    # 这部分逻辑应在调用 intake_node 之前或在 intake_node 内部触发 interrupt_before 实现

    return {**state, "agent_spec": agent_spec, "status": "intake_done"}
```

**关键点：**
*   **LLM 驱动解析：** `intake_node` 使用强大的 LLM (`claude-opus-4-5`) 将用户的自然语言需求转换为结构化的 `AgentSpec`，包括智能体名称、核心功能、所需工具和依赖等。
*   **语言锁定：** `target_language` 在此阶段被确定并锁定，后续所有生成和打包都将围绕此语言进行。
*   **健壮性：** 增加了 JSON 解析失败和 LLM 未返回有效 JSON 时的容错处理，确保流程不会中断。

#### 17.3.2 `DomainRouter` 实现

`DomainRouter` 负责根据 `AgentSpec` 的特征，预先筛选出相关的部门，缩小后续角色选择的范围。这对应技术方案的 `4.1 第一层：DomainRouter（领域路由）` [1]。

```python
# agent_factory/core/nodes.py

from .types import FactoryStateV3, AgentSpec, Division
from typing import List, Set

class DomainRouter:
    DOMAIN_SIGNALS = {
        "game": [Division.GAME_DEVELOPMENT, Division.SPECIALIZED],
        "xr": [Division.SPATIAL_COMPUTING, Division.ENGINEERING],
        "web3": [Division.ENGINEERING, Division.SPECIALIZED],  # Solidity等
        "enterprise": [Division.SUPPORT, Division.SPECIALIZED, Division.ENGINEERING],
        "mobile": [Division.ENGINEERING, Division.DESIGN],
        "data": [Division.ENGINEERING, Division.SPECIALIZED],
        "marketing": [Division.MARKETING, Division.SALES, Division.PRODUCT],
        "general": list(Division),  # 不做限制，包含所有部门
    }
    
    CORE_DIVISIONS = {
        Division.ENGINEERING,
        Division.PRODUCT,
        Division.PROJECT_MANAGEMENT,
        Division.TESTING
    }

    def _detect_domain(self, spec: AgentSpec) -> str:
        # TODO: 实现更智能的领域检测逻辑，可以基于关键词、工具需求、目标用户等
        # 示例：简单的关键词匹配
        purpose_str = " ".join(spec.purpose).lower()
        if "游戏" in purpose_str or "unity" in purpose_str or "unreal" in purpose_str: return "game"
        if "xr" in purpose_str or "ar" in purpose_str or "vr" in purpose_str: return "xr"
        if "web3" in purpose_str or "区块链" in purpose_str or "solidity" in purpose_str: return "web3"
        if "企业" in purpose_str or "crm" in purpose_str or "erp" in purpose_str: return "enterprise"
        if "移动" in purpose_str or "ios" in purpose_str or "android" in purpose_str: return "mobile"
        if "数据" in purpose_str or "分析" in purpose_str: return "data"
        if "市场" in purpose_str or "营销" in purpose_str: return "marketing"
        return "general"

    def route(self, spec: AgentSpec) -> Set[Division]:
        detected_domain_key = self._detect_domain(spec)
        
        # 获取领域相关的部门
        domain_divisions = set(self.DOMAIN_SIGNALS.get(detected_domain_key, self.DOMAIN_SIGNALS["general"]))
        
        # 始终包含核心部门
        all_relevant_divisions = domain_divisions.union(self.CORE_DIVISIONS)
        
        return all_relevant_divisions

async def domain_router_node(state: FactoryStateV3) -> FactoryStateV3:
    agent_spec = state["agent_spec"]
    if not agent_spec:
        raise ValueError("AgentSpec is missing in state for domain routing.")

    router = DomainRouter()
    relevant_divisions = router.route(agent_spec)
    
    # 将相关部门信息存储到状态中，供后续角色选择使用
    state["domain"] = router._detect_domain(agent_spec) # 存储检测到的领域
    state["relevant_divisions"] = [d.value for d in relevant_divisions] # 存储相关部门列表
    state["status"] = "domain_routed"
    return state
```

**关键点：**
*   **领域检测：** `_detect_domain` 方法根据 `AgentSpec` 中的 `purpose`、`tools` 等信息，通过关键词匹配或更复杂的 LLM 分类来识别任务所属的领域。
*   **部门筛选：** `route` 方法根据检测到的领域，从 `DOMAIN_SIGNALS` 中获取相关部门列表，并强制包含 `CORE_DIVISIONS`（工程、产品、项目管理、测试），确保基础职能的覆盖。
*   **状态更新：** `domain_router_node` 将检测到的领域和相关部门列表更新到 `FactoryStateV3` 中，供后续的 `dispatch_phase1_node` 进行角色选择。

#### 17.3.3 智能角色选择（`dispatch_phase1_node` 和 `dispatch_phase2_node`）

角色选择是 Agent Factory 的核心智能所在，它需要综合考虑 `AgentSpec`、领域路由结果、强制规则、语义匹配以及历史成功率等因素。这对应技术方案的 `4.1 第二层：语义向量匹配` 和 `4.1 第三层：平衡性校验 + 强制规则` [1]。

```python
# agent_factory/core/nodes.py

from .types import FactoryStateV3, AgentSpec, DispatchPlan, ExecutionMode
from agent_factory.registry.loader import AgentRegistry, MANDATORY_DISCUSSION_ROLES, MANDATORY_WHEN_TOOLS_NEEDED
from agent_factory.engine.embedding import EmbeddingModel # 假设有嵌入模型
from collections import defaultdict

async def dispatch_phase1_node(state: FactoryStateV3) -> FactoryStateV3:
    agent_spec = state["agent_spec"]
    execution_mode = state["execution_mode"]
    relevant_divisions_str = state.get("relevant_divisions", [])
    relevant_divisions = {Division(d) for d in relevant_divisions_str}
    
    registry = AgentRegistry(repo_path=Path("agency_agents")) # 假设仓库路径
    all_agents = registry.get_all_agents()

    candidate_agents: List[AgentMeta] = []
    for slug, meta in all_agents.items():
        if meta.division in relevant_divisions and "discussion" in meta.factory_phases:
            candidate_agents.append(meta)

    # 语义向量匹配 (第二层)
    # TODO: 实现 EmbeddingModel 和向量数据库查询
    # 这里简化为基于描述的关键词匹配，实际应使用向量相似度
    selected_discussion_agents_slugs = set()
    agent_spec_keywords = " ".join(agent_spec.purpose + agent_spec.tools).lower()

    # 强制角色 (第三层)
    for slug in MANDATORY_DISCUSSION_ROLES:
        if slug in all_agents: # 确保强制角色存在于注册表中
            selected_discussion_agents_slugs.add(slug)

    # 语义匹配选择其他角色
    for agent in candidate_agents:
        if agent.slug in selected_discussion_agents_slugs: continue
        if any(keyword in agent.description.lower() for keyword in agent_spec_keywords.split()):
            selected_discussion_agents_slugs.add(agent.slug)

    # 平衡性校验与团队规模控制 (第三层)
    discussion_team_size = 0
    if execution_mode == ExecutionMode.STANDARD: discussion_team_size = 3
    elif execution_mode == ExecutionMode.THOROUGH: discussion_team_size = 5
    # Fast 模式跳过讨论，所以这里不处理

    final_discussion_agents: List[AgentMeta] = []
    # 优先添加强制角色
    for slug in MANDATORY_DISCUSSION_ROLES:
        if slug in selected_discussion_agents_slugs and all_agents[slug] not in final_discussion_agents:
            final_discussion_agents.append(all_agents[slug])

    # 补充其他角色直到达到团队规模上限
    for slug in selected_discussion_agents_slugs:
        if all_agents[slug] not in final_discussion_agents:
            if len(final_discussion_agents) < discussion_team_size:
                final_discussion_agents.append(all_agents[slug])
            else:
                break # 达到上限
    
    # 如果仍未达到最低团队规模，可以从候选集中随机补充或根据重要性补充
    while len(final_discussion_agents) < discussion_team_size and len(final_discussion_agents) < len(candidate_agents):
        for agent in candidate_agents:
            if agent not in final_discussion_agents:
                final_discussion_agents.append(agent)
                if len(final_discussion_agents) == discussion_team_size: break

    dispatch_plan = DispatchPlan(
        phase="discussion",
        roles=[meta.slug for meta in final_discussion_agents],
        # TODO: 更多调度细节，如讨论轮次、仲裁机制等
    )

    state["dispatch_plan_phase1"] = dispatch_plan
    state["status"] = "phase1_dispatched"
    return state

async def dispatch_phase2_node(state: FactoryStateV3) -> FactoryStateV3:
    agent_spec = state["agent_spec"]
    tech_spec = state["tech_spec"]
    relevant_divisions_str = state.get("relevant_divisions", [])
    relevant_divisions = {Division(d) for d in relevant_divisions_str}

    registry = AgentRegistry(repo_path=Path("agency_agents"))
    all_agents = registry.get_all_agents()

    candidate_agents: List[AgentMeta] = []
    for slug, meta in all_agents.items():
        if meta.division in relevant_divisions and "development" in meta.factory_phases:
            candidate_agents.append(meta)

    # 强制角色：MCP Builder 当需要工具时
    selected_development_agents_slugs = set()
    if any(tool != "none" for tool in agent_spec.tools):
        for slug in MANDATORY_WHEN_TOOLS_NEEDED:
            if slug in all_agents:
                selected_development_agents_slugs.add(slug)
    
    # TODO: 结合 TechSpec (技术规格书) 进行更精确的角色选择
    # TechSpec 应该包含任务分解，每个子任务可以匹配到最合适的开发角色
    # 这里简化为选择 Senior Developer 和 AI Engineer
    if "senior-developer" in all_agents: selected_development_agents_slugs.add("senior-developer")
    if "ai-engineer" in all_agents: selected_development_agents_slugs.add("ai-engineer")

    final_development_agents: List[AgentMeta] = [
        all_agents[slug] for slug in selected_development_agents_slugs if slug in all_agents
    ]

    dispatch_plan = DispatchPlan(
        phase="development",
        roles=[meta.slug for meta in final_development_agents],
    )

    state["dispatch_plan_phase2"] = dispatch_plan
    state["status"] = "phase2_dispatched"
    return state
```

**关键点：**
*   **分阶段调度：** `dispatch_phase1_node` 负责为讨论阶段选择角色，`dispatch_phase2_node` 负责为开发阶段选择角色。这种分阶段调度允许在不同阶段应用不同的选择逻辑和强制规则。
*   **语义向量匹配（待实现）：** 技术方案中提到第二层是语义向量匹配。在上述代码中，这部分被简化为关键词匹配。实际实现中，需要一个 `EmbeddingModel` 来将 `AgentSpec` 和 `AgentMeta` 的描述转换为向量，并使用向量数据库（如 Faiss, Pinecone, Weaviate）进行相似度搜索。
*   **强制规则与平衡性：** 强制角色（如 `MANDATORY_DISCUSSION_ROLES` 和 `MANDATORY_WHEN_TOOLS_NEEDED`）被优先加入团队。同时，代码会尝试控制团队规模，并确保团队构成具有一定的平衡性（例如，至少包含一个工程角色、一个产品角色等）。
*   **结合 `TechSpec`：** `dispatch_phase2_node` 在开发阶段的角色选择中，应更深入地利用 `TechSpec` 中详细的任务分解，将不同的子任务分配给最合适的开发角色。目前代码中简化为选择 `Senior Developer` 和 `AI Engineer`。

### 17.4. 主控调度智能体 (`MasterDispatcherV3`)

技术方案的 `5. 主控调度智能体（含反馈闭环）` [1] 强调了 `MasterDispatcherV3` 作为有状态决策器的重要性，它能够从历史失败中学习，并优化未来的调度决策。

#### 17.4.1 `MasterDispatcherV3` 概念与实现思路

在 LangGraph 框架中，`MasterDispatcherV3` 的逻辑不会是一个独立的节点，而是其智能体逻辑会分散到 `dispatch_phase1_node` 和 `dispatch_phase2_node` 中，并通过 `RecoveryJournal` 获取历史反馈。它通过以下方式实现其“有状态决策器”的特性：

1.  **历史数据反馈：** `RecoveryJournal` 记录了所有失败尝试，包括失败类型、受影响的组件（角色或工具）和恢复策略。`MasterDispatcherV3`（或调度节点）在选择角色和工具时，会查询这些历史数据，避免选择高失败率的角色或工具。
2.  **成本感知：** `CostEstimator` 在任务开始前提供成本预估，并结合 `ExecutionMode` 进行预算控制。调度器会考虑成本因素，尤其是在选择讨论团队规模和工具时。
3.  **动态调整：** 调度器能够根据当前任务的进展和遇到的问题，动态调整后续的调度计划，例如在遇到特定失败时，触发不同的恢复策略。

**实现建议：**
*   在 `dispatch_phase1_node` 和 `dispatch_phase2_node` 内部，实例化 `RecoveryJournal` 和 `CostEstimator`，并在角色选择逻辑中引入它们的输出。
*   例如，在选择 `candidate_agents` 之后，可以根据 `RecoveryJournal` 提供的“高失败率角色”列表，降低这些角色的优先级或直接排除。

```python
# agent_factory/core/nodes.py (在 dispatch_phase1_node 或 dispatch_phase2_node 内部)

from agent_factory.recovery.recovery_journal import RecoveryJournal # 假设 RecoveryJournal 已实现

# ... (角色选择逻辑之前)

    recovery_journal = RecoveryJournal() # 实例化 RecoveryJournal
    # 获取过去30天内高失败率的角色/工具模式
    failure_patterns = await recovery_journal.get_failure_patterns(lookback_days=30)
    high_failure_roles = {p["role_or_tool"] for p in failure_patterns if p["failure_type"] == "test_failure" and p["total"] > 5}

    # 在选择角色时，降低高失败率角色的优先级或排除
    filtered_candidate_agents = []
    for agent in candidate_agents:
        if agent.slug in high_failure_roles:
            logger.warning(f"角色 {agent.slug} 历史失败率较高，已降低其优先级或排除。")
            # 可以选择跳过，或者在排序时给予较低权重
            continue 
        filtered_candidate_agents.append(agent)
    candidate_agents = filtered_candidate_agents

# ... (继续角色选择逻辑)
```

### 17.5. 多轮讨论阶段 (`DiscussionGraph`)

讨论阶段是 Agent Factory 的核心创新点之一，它借鉴了 MiroFish 的群体智能范式，通过多个智能体角色的结构化讨论来产出高质量的 `TechSpec`。这部分将作为一个 LangGraph 的子图实现。技术方案的 `6. 多轮讨论阶段（并行异步 DiscussionGraph）` [1] 提供了设计思路。

#### 17.5.1 `DiscussionGraph` 子图实现

`DiscussionGraph` 将是一个独立的 `StateGraph`，它被嵌入到主 `FactoryGraph` 的 `discussion_node` 中。它将包含以下核心节点：

*   **`init_discussion`：** 初始化讨论状态，分配角色，设置讨论轮次。
*   **`role_turn`：** 每个角色轮流发言，基于当前讨论状态和自身系统提示词生成观点。
*   **`arbitrator`：** 仲裁节点，负责总结当前轮次讨论，识别分歧，并推动讨论收敛。
*   **`summarizer`：** 在讨论结束后，总结所有讨论内容，生成 `TechSpec`。

```python
# agent_factory/discussion/discussion_graph.py

from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any, Optional
from langchain_anthropic import ChatAnthropic
from agent_factory.registry.loader import AgentMeta

class DiscussionState(TypedDict):
    round_number: int
    max_rounds: int
    agent_spec: AgentSpec
    participants: List[AgentMeta]
    discussion_history: List[Dict[str, Any]] # [{role_slug, content, sentiment}]
    current_turn_agent: Optional[AgentMeta]
    tech_spec_draft: Optional[TechSpec]
    disagreements: List[str]

async def init_discussion_node(state: DiscussionState) -> DiscussionState:
    # 初始化讨论轮次、参与者等
    # participants 来自 dispatch_phase1_node 选出的角色
    state["round_number"] = 1
    state["max_rounds"] = 3 # 根据 execution_mode 调整
    state["discussion_history"] = []
    state["disagreements"] = []
    state["current_turn_agent"] = state["participants"][0] # 从第一个角色开始
    return state

async def role_turn_node(state: DiscussionState) -> DiscussionState:
    current_agent = state["current_turn_agent"]
    agent_spec = state["agent_spec"]
    discussion_history = state["discussion_history"]

    llm = ChatAnthropic(model="claude-opus-4-5", temperature=0.5)

    # 构建提示词，包含角色系统提示词、AgentSpec 和讨论历史
    prompt = f"""
你是一个专业的 {current_agent.name} ({current_agent.division.value} 部门)。
你的系统提示词是：\n{current_agent.system_prompt}\n
当前任务是为以下 AgentSpec 讨论技术方案：
{json.dumps(agent_spec.model_dump(), indent=2, ensure_ascii=False)}

以下是之前的讨论历史：
{json.dumps(discussion_history, indent=2, ensure_ascii=False)}

请你基于你的专业视角，对当前讨论提出你的观点、建议或疑问。你的发言应该简洁、专业，并推动讨论向技术规格书的产出方向发展。
"""
    response = await llm.ainvoke(prompt)
    
    discussion_entry = {
        "role_slug": current_agent.slug,
        "content": response.content,
        "round": state["round_number"],
        "timestamp": datetime.now().isoformat()
    }
    state["discussion_history"].append(discussion_entry)

    # 轮换到下一个角色
    current_index = state["participants"].index(current_agent)
    next_index = (current_index + 1) % len(state["participants"])
    state["current_turn_agent"] = state["participants"][next_index]

    return state

async def arbitrator_node(state: DiscussionState) -> DiscussionState:
    # TODO: 实现仲裁逻辑，总结本轮讨论，识别分歧，推动收敛
    # 可以使用 LLM 来分析 discussion_history，提取关键点和未解决的分歧
    state["disagreements"].append(f"Round {state['round_number']} 存在分歧点：XXX")
    return state

async def summarizer_node(state: DiscussionState) -> DiscussionState:
    # TODO: 实现 TechSpec 总结生成逻辑
    # 使用 LLM 结合 discussion_history 产出结构化的 TechSpec
    state["tech_spec_draft"] = TechSpec(architecture="...") # 占位实现
    return state

def route_discussion_next(state: DiscussionState) -> str:
    if state["round_number"] < state["max_rounds"]:
        if state["current_turn_agent"] == state["participants"][0]: # 一轮结束，进入仲裁
            state["round_number"] += 1
            return "arbitrator"
        return "role_turn" # 继续角色发言
    return "summarizer" # 达到最大轮次，进入总结

def build_discussion_graph() -> StateGraph:
    graph = StateGraph(DiscussionState)

    graph.add_node("init_discussion", init_discussion_node)
    graph.add_node("role_turn", role_turn_node)
    graph.add_node("arbitrator", arbitrator_node)
    graph.add_node("summarizer", summarizer_node)

    graph.set_entry_point("init_discussion")
    graph.add_edge("init_discussion", "role_turn")

    graph.add_conditional_edges(
        "role_turn",
        route_discussion_next,
        {
            "role_turn": "role_turn",
            "arbitrator": "arbitrator",
            "summarizer": "summarizer"
        }
    )
    graph.add_edge("arbitrator", "role_turn") # 仲裁后继续下一轮角色发言
    graph.add_edge("summarizer", END)

    return graph.compile()

# 在主 FactoryGraph 的 discussion_node 中调用此子图
async def discussion_node(state: FactoryStateV3) -> FactoryStateV3:
    # 准备 DiscussionGraph 的初始状态
    discussion_participants = [AgentRegistry(Path("agency_agents")).get_agent_meta(slug) 
                               for slug in state["dispatch_plan_phase1"].roles]
    
    discussion_initial_state = DiscussionState(
        round_number=0, # 初始为0，init_discussion_node会设置为1
        max_rounds=state["execution_mode"].get_discussion_rounds(), # 根据执行模式获取轮次
        agent_spec=state["agent_spec"],
        participants=discussion_participants,
        discussion_history=[],
        current_turn_agent=None, # init_discussion_node 会设置
        tech_spec_draft=None,
        disagreements=[]
    )

    discussion_graph = build_discussion_graph()
    final_discussion_state = await discussion_graph.ainvoke(discussion_initial_state)

    state["tech_spec"] = final_discussion_state["tech_spec_draft"]
    state["status"] = "discussion_done"
    return state
```

**关键点：**
*   **子图封装：** `build_discussion_graph()` 创建一个独立的 LangGraph 子图，实现了讨论阶段的内部逻辑。这使得主图更加清晰，并提高了模块化程度。
*   **角色轮流发言：** `role_turn_node` 模拟智能体角色轮流发言，每个角色根据其系统提示词、`AgentSpec` 和讨论历史生成观点。这里可以引入更复杂的立场演化逻辑。
*   **仲裁机制：** `arbitrator_node` 负责总结讨论进展，识别分歧，并引导讨论向收敛方向发展。这对于避免无限循环和确保讨论效率至关重要。
*   **`TechSpec` 产出：** `summarizer_node` 在讨论结束后，将所有讨论内容提炼为结构化的 `TechSpec`，作为开发阶段的输入。
*   **人机协作：** 在 `discussion_node` 结束后，主图会触发 `interrupt_before="dispatch_phase2"`，等待用户审查 `TechSpec` 并决定是否继续。

### 17.6. 执行层（开发、测试、打包）

执行层是 Agent Factory 将 `TechSpec` 转化为可交付智能体的阶段，包括代码生成、测试验证和最终打包。这部分涉及多个 LangGraph 节点和外部工具的集成。

#### 17.6.1 `development_node` 实现

`development_node` 负责根据 `TechSpec` 和选定的开发角色生成目标智能体的代码。它可能涉及多个子任务，例如架构设计、代码编写、工具集成等。

```python
# agent_factory/core/nodes.py

from .types import FactoryStateV3, TechSpec, DevelopmentArtifacts
from agent_factory.registry.loader import AgentRegistry
from agent_factory.development.code_generator import CodeGenerator # 假设有代码生成器

async def development_node(state: FactoryStateV3) -> FactoryStateV3:
    tech_spec = state["tech_spec"]
    target_language = state["target_language"]
    development_roles_slugs = state["dispatch_plan_phase2"].roles

    # 实例化开发角色
    registry = AgentRegistry(repo_path=Path("agency_agents"))
    development_agents = [registry.get_agent_meta(slug) for slug in development_roles_slugs]

    # TODO: 实现更复杂的开发流程，例如并行开发、代码审查等
    # 这里简化为由 CodeGenerator 统一生成代码
    code_generator = CodeGenerator(llm=ChatAnthropic(model="claude-opus-4-5"))
    
    # 假设 CodeGenerator 能够根据 TechSpec 和语言生成代码和依赖
    generated_code, generated_dependencies = await code_generator.generate_agent_code(
        tech_spec=tech_spec,
        target_language=target_language,
        development_agents=development_agents
    )

    development_artifacts = DevelopmentArtifacts(
        code=generated_code,
        dependencies=generated_dependencies,
        # 其他产物，如配置文件、测试用例等
    )

    state["development_artifacts"] = development_artifacts
    state["status"] = "development_done"
    return state
```

**关键点：**
*   **`CodeGenerator`：** 引入一个 `CodeGenerator` 模块，它将利用 LLM 和开发角色的专业知识，根据 `TechSpec` 生成目标智能体的代码和依赖清单。
*   **多角色协作（待扩展）：** 尽管这里简化为 `CodeGenerator` 统一生成，但实际可以扩展为更复杂的子图，模拟多个开发角色并行工作、互相审查代码的流程。

#### 17.6.2 `quality_gate_node` 实现

`quality_gate_node` 负责对开发阶段产出的代码进行质量检查，包括单元测试、契约测试、安全扫描等。它将决定流程是继续打包还是进入失败恢复。

```python
# agent_factory/core/nodes.py

from .types import FactoryStateV3, TestReport
from agent_factory.testing.tester import AgentTester # 假设有测试模块

async def quality_gate_node(state: FactoryStateV3) -> FactoryStateV3:
    development_artifacts = state["development_artifacts"]
    agent_spec = state["agent_spec"]
    target_language = state["target_language"]

    tester = AgentTester() # 实例化测试器
    test_report = await tester.run_all_tests(
        code=development_artifacts.code,
        dependencies=development_artifacts.dependencies,
        agent_spec=agent_spec,
        target_language=target_language
    )

    state["test_report"] = test_report
    state["status"] = "quality_gate_checked"
    
    # LangGraph 的条件路由会根据 test_report.passed 决定下一步
    return state
```

**关键点：**
*   **`AgentTester`：** 引入一个 `AgentTester` 模块，它将封装各种测试逻辑，例如运行单元测试、集成测试、安全扫描等。测试结果将汇总为 `TestReport`。
*   **条件路由：** `quality_gate_node` 不直接决定流程走向，而是更新 `test_report` 状态，主图的 `add_conditional_edges` 会根据 `test_report.passed` 字段自动路由。

#### 17.6.3 失败恢复链

技术方案的 `7.4 失败恢复机制` [1] 详细描述了失败分类、恢复策略和恢复日志。这部分在 `build_factory_graph_v3` 中已经作为独立节点集成。

*   **`failure_classifier_node`：** 接收失败信息，将其分类为 `ClassifiedFailure` 对象，包括失败领域、类型、严重性等。这部分可以结合规则树和 LLM 进行分类。
*   **`recovery_strategy_node`：** 根据 `ClassifiedFailure` 和历史恢复日志，决定采取何种恢复策略（重试、替换角色、降级、人工介入等），产出 `RecoveryResult`。
*   **`targeted_remediation_node`：** 当恢复策略是 `substitute_role` 时，此节点负责选择新的角色或调整任务，然后重新进入 `quality_gate`。
*   **`human_recovery_node`：** 当恢复策略是 `escalate_to_human` 时，此节点会触发人机协作检查点，等待用户决策（重试、降级或中止）。
*   **`graceful_packager_node`：** 当恢复策略是 `graceful_degrade` 时，此节点负责生成一个带有降级说明的交付包，然后直接进入 `delivery` 阶段。

#### 17.6.4 智能体工具基础引擎（`ToolSelector-Driven Tool Engine`）

技术方案的 `12. 智能体工具基础引擎（带调度智能）` [1] 提出了一个智能的工具调度机制，Agent 不再直接调用工具，而是通过 `ToolSelector` 生成执行计划，再由 `FallbackAwareToolExecutor` 执行。

##### 17.6.4.1 `ToolCapabilityDescriptor`

每个工具都应有一个 `ToolCapabilityDescriptor` 来描述其能力、输入输出、成本、可靠性等元数据。这有助于 `ToolSelector` 进行智能决策。

```python
# agent_factory/engine/tool_descriptor.py

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

class ToolCategory(str, Enum):
    WEB_ACCESS = "web_access"
    CODE_EXEC = "code_exec"
    FILE_OPS = "file_ops"
    API_CALL = "api_call"
    # ... 其他类别

@dataclass
class ToolCapabilityDescriptor:
    tool_id: str
    name: str
    category: ToolCategory
    description: str
    capability_embedding: List[float] = field(default_factory=list) # 预计算的向量
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    avg_latency_ms: float = 0.0
    cost_per_call: float = 0.0
    rate_limit_per_min: Optional[int] = None
    success_rate: float = 1.0 # 运行时动态更新
    failure_modes: List[str] = field(default_factory=list) # 运行时动态更新
    requires_env_vars: List[str] = field(default_factory=list)
    requires_sandbox: bool = False
    source: str = "builtin" # builtin / mcp / skill
    fallback_tool_ids: List[str] = field(default_factory=list)
    composable_with: List[str] = field(default_factory=list)
```

##### 17.6.4.2 `ToolCapabilityIndex`

`ToolCapabilityIndex` 负责构建和维护工具能力的向量索引，支持语义检索。

```python
# agent_factory/engine/tool_capability_index.py

from typing import List, Optional
from agent_factory.engine.tool_descriptor import ToolCapabilityDescriptor, ToolCategory
from agent_factory.engine.embedding import EmbeddingModel # 假设有 EmbeddingModel
# from vector_db_client import VectorDBClient # 假设有向量数据库客户端

@dataclass
class ScoredTool:
    tool: ToolCapabilityDescriptor
    score: float

class ToolCapabilityIndex:
    def __init__(self):
        self._descriptors: Dict[str, ToolCapabilityDescriptor] = {}
        self._embedder = EmbeddingModel() # 实例化嵌入模型
        # self.vs = VectorDBClient() # 实例化向量数据库客户端

    async def build(self, all_tools: List[ToolCapabilityDescriptor]):
        for tool in all_tools:
            embedding = await self._embedder.embed(f"{tool.name}: {tool.description}")
            tool.capability_embedding = embedding
            self._descriptors[tool.tool_id] = tool
            # 实际应将向量和元数据存储到向量数据库
            # await self.vs.upsert(
            #     id=tool.tool_id,
            #     vector=embedding,
            #     metadata={
            #         "category": tool.category.value,
            #         "source": tool.source,
            #         "cost": tool.cost_per_call,
            #         "success_rate": tool.success_rate,
            #     }
            # )

    async def search(
        self,
        task_description: str,
        top_k: int = 5,
        filter_category: Optional[ToolCategory] = None,
        max_cost_per_call: Optional[float] = None,
    ) -> List[ScoredTool]:
        task_embedding = await self._embedder.embed(task_description)
        
        # 实际应从向量数据库查询，这里简化为模拟结果
        # results = await self.vs.query(
        #     vector=task_embedding,
        #     top_k=top_k * 2,
        #     filter=self._build_filter(filter_category, max_cost_per_call)
        # )
        # 模拟结果
        mock_results = []
        for tool_id, tool_desc in self._descriptors.items():
            # 简单的关键词匹配作为模拟相似度
            if any(keyword in tool_desc.description.lower() for keyword in task_description.lower().split()):
                mock_results.append(ScoredTool(tool=tool_desc, score=0.8))
        
        # 过滤和排序
        filtered_results = []
        for scored_tool in mock_results:
            if filter_category and scored_tool.tool.category != filter_category: continue
            if max_cost_per_call and scored_tool.tool.cost_per_call > max_cost_per_call: continue
            filtered_results.append(scored_tool)
        
        filtered_results.sort(key=lambda x: x.score, reverse=True)
        return filtered_results[:top_k]

    def _build_filter(self, filter_category: Optional[ToolCategory], max_cost_per_call: Optional[float]) -> Dict[str, Any]:
        # 构建向量数据库查询过滤器
        filters = {}
        if filter_category: filters["category"] = filter_category.value
        if max_cost_per_call: filters["cost"] = {"$lte": max_cost_per_call}
        return filters
```

##### 17.6.4.3 `ToolSelector` 与 `FallbackAwareToolExecutor`

`ToolSelector` 负责根据子任务描述，从 `ToolCapabilityIndex` 中选择最合适的工具，并生成一个包含 fallback 链的执行计划。`FallbackAwareToolExecutor` 则负责执行这个计划。

```python
# agent_factory/engine/tool_engine.py

from typing import List, Dict, Any
from agent_factory.engine.tool_descriptor import ToolCapabilityDescriptor
from agent_factory.engine.tool_capability_index import ToolCapabilityIndex, ScoredTool

@dataclass
class ToolExecutionPlan:
    tool_id: str
    args: Dict[str, Any]
    fallback_plan: Optional["ToolExecutionPlan"] = None

class ToolSelector:
    def __init__(self, tool_index: ToolCapabilityIndex):
        self.tool_index = tool_index
        self.llm = ChatAnthropic(model="claude-opus-4-5", temperature=0)

    async def select_and_plan(
        self, subtask_description: str, available_tools: List[ToolCapabilityDescriptor]
    ) -> ToolExecutionPlan:
        # 1. 语义搜索最相关工具
        scored_tools = await self.tool_index.search(subtask_description, top_k=3)
        if not scored_tools: raise ValueError("未找到合适的工具")

        # 2. 使用 LLM 决定最佳工具和参数，并生成 fallback 链
        # 提示词应引导 LLM 考虑工具的成功率、成本、输入输出契约和 fallback 选项
        prompt = f"""
根据以下子任务描述和可用工具列表，选择最合适的工具，并生成其调用参数。如果选定的工具失败，请提供一个备用工具及其参数。

子任务描述：{subtask_description}

可用工具列表：
{json.dumps([t.tool.model_dump() for t in scored_tools], indent=2, ensure_ascii=False)}

请以 JSON 格式返回一个执行计划，包含 'primary_tool' 和可选的 'fallback_tool'。每个工具应包含 'tool_id' 和 'args'。
示例：
{{
  "primary_tool": {{
    "tool_id": "web_search",
    "args": {{
      "query": "LangGraph 最新特性"
    }}
  }},
  "fallback_tool": {{
    "tool_id": "general_qa",
    "args": {{
      "question": "LangGraph 最新特性是什么"
    }}
  }}
}}
"""
        response = await self.llm.ainvoke(prompt)
        plan_data = json.loads(response.content)

        primary_tool_id = plan_data["primary_tool"]["tool_id"]
        primary_args = plan_data["primary_tool"]["args"]
        primary_plan = ToolExecutionPlan(tool_id=primary_tool_id, args=primary_args)

        if "fallback_tool" in plan_data:
            fallback_tool_id = plan_data["fallback_tool"]["tool_id"]
            fallback_args = plan_data["fallback_tool"]["args"]
            primary_plan.fallback_plan = ToolExecutionPlan(tool_id=fallback_tool_id, args=fallback_args)
        
        return primary_plan

class FallbackAwareToolExecutor:
    def __init__(self, tools: Dict[str, Any]): # tools 是 tool_id 到实际工具函数的映射
        self.tools = tools

    async def execute(self, plan: ToolExecutionPlan) -> Any:
        try:
            tool_func = self.tools.get(plan.tool_id)
            if not tool_func: raise ValueError(f"工具 {plan.tool_id} 未注册")
            result = await tool_func(**plan.args)
            # TODO: 记录工具成功率和耗时到 ToolCapabilityDescriptor
            return result
        except Exception as e:
            logger.error(f"工具 {plan.tool_id} 执行失败: {e}")
            # TODO: 记录工具失败模式到 ToolCapabilityDescriptor
            if plan.fallback_plan:
                logger.info(f"尝试执行备用工具 {plan.fallback_plan.tool_id}")
                return await self.execute(plan.fallback_plan) # 递归执行 fallback
            raise # 没有 fallback 或 fallback 也失败，则抛出异常
```

**关键点：**
*   **`ToolCapabilityDescriptor`：** 详细描述工具元数据，包括成本、成功率、fallback 选项等，为智能调度提供依据。
*   **`ToolCapabilityIndex`：** 利用嵌入模型和向量数据库实现工具的语义搜索，能够根据任务描述找到最相关的工具。
*   **`ToolSelector`：** 这是一个基于 LLM 的决策器，它不仅选择最佳工具，还能根据工具的 `fallback_tool_ids` 和 LLM 的推理能力，生成一个包含备用方案的执行计划。
*   **`FallbackAwareToolExecutor`：** 负责按计划执行工具，并在工具失败时自动尝试执行 fallback 方案，提高了系统的鲁棒性。
*   **动态更新：** 工具的成功率和失败模式可以在运行时动态记录和更新，为 `ToolSelector` 提供更准确的决策依据，体现了技术方案中“追踪哪些工具在哪类任务上成功率高”的理念。


### 17.7. 工程化与质量门禁

Agent Factory 强调高质量和高可靠性，通过严格的工程化实践和多层次的质量门禁来确保生成智能体的质量。这部分主要涉及 CI Gate、沙箱策略和交付系统。

#### 17.7.1 CI Gate 基础设施 (`run_gates.py`)

技术方案的 `0.10 项目创建后的首步限制操作（CI Gate Bootstrap，强制）` [1] 详细定义了 CI Gate 的最小检查项和强制规则。`run_gates.py` 是这些检查的核心执行脚本。

```python
# agent_factory/ci/run_gates.py

import argparse
import os
import re
import json
import sys
from pathlib import Path

class GateCheckResult:
    def __init__(self, name: str, passed: bool, message: str = ""):
        self.name = name
        self.passed = passed
        self.message = message

def scan_for_placeholders(repo_path: Path) -> GateCheckResult:
    """扫描代码中是否存在占位符（TODO, placeholder, 伪调用等）"""
    placeholder_patterns = [
        r"TODO", r"placeholder", r"FIXME",
        r"return 'input_echo'", # 仅回显输入的伪调用
        r"raise NotImplementedError",
    ]
    found_issues = []
    for file_path in repo_path.rglob("*.py"): # 假设只扫描 Python 文件
        if "ci" in file_path.parts: continue # 跳过 CI 脚本自身
        content = file_path.read_text()
        for pattern in placeholder_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                found_issues.append(f"文件 {file_path} 包含占位符: {pattern}")
    
    if found_issues:
        return GateCheckResult("placeholder_scan", False, "\n".join(found_issues))
    return GateCheckResult("placeholder_scan", True, "未发现占位符")

def check_required_files(repo_path: Path, language: str) -> GateCheckResult:
    """检查交付必备文件（例如 Python 的 requirements.txt, Node.js 的 package.json）"""
    required_files = {
        "python": ["requirements.txt", "main.py", "README.md"],
        "nodejs": ["package.json", "index.js", "README.md"],
    }
    missing_files = []
    for f in required_files.get(language, []):
        if not (repo_path / f).exists():
            missing_files.append(f)
    
    if missing_files:
        return GateCheckResult("required_files_check", False, f"缺少必备文件: {', '.join(missing_files)}")
    return GateCheckResult("required_files_check", True, "所有必备文件存在")

def check_declaration_implementation_consistency(repo_path: Path) -> GateCheckResult:
    """检查 README/Manifest 声明的能力与代码实现是否一致"""
    # 这是一个复杂检查，通常需要 LLM 或更复杂的 AST 分析
    # MVP 简化为检查 README 中声明的入口文件是否存在
    readme_path = repo_path / "README.md"
    if not readme_path.exists():
        return GateCheckResult("declaration_implementation_consistency", False, "README.md 不存在")
    
    readme_content = readme_path.read_text()
    # 假设 README 中会提到一个主要的入口文件，例如 `python main.py`
    match = re.search(r"CMD \["python", "(.*?)"\]", readme_content) # 示例：从 Dockerfile 风格的 CMD 中提取
    if match:
        entry_file = match.group(1)
        if not (repo_path / entry_file).exists():
            return GateCheckResult("declaration_implementation_consistency", False, f"README 中声明的入口文件 {entry_file} 不存在")
    
    return GateCheckResult("declaration_implementation_consistency", True, "声明与实现初步一致")

def check_selftest_records(repo_path: Path) -> GateCheckResult:
    """检查功能完成度提升是否附带自测证据"""
    # 这需要一个机制来跟踪功能完成度变化和自测记录文件
    # MVP 简化为检查是否存在任何 .selftest.yaml 文件
    selftest_files = list(repo_path.rglob("*.selftest.yaml"))
    if not selftest_files:
        return GateCheckResult("selftest_records_check", False, "未发现自测记录文件 (*.selftest.yaml)")
    
    # TODO: 更详细的检查，例如解析 YAML 内容，验证完成度与测试结果一致性
    return GateCheckResult("selftest_records_check", True, f"发现 {len(selftest_files)} 个自测记录文件")

def check_doc_impact(pr_template_path: Path) -> GateCheckResult:
    """检查 PR 描述是否包含 Doc Impact 小节"""
    # 在 CI/CD 流程中，这通常通过检查 PR 描述文本来实现
    # 这里模拟检查 PR 模板中是否包含 Doc Impact 的提示
    if not pr_template_path.exists():
        return GateCheckResult("doc_impact_check", False, "PR 模板文件不存在")
    
    content = pr_template_path.read_text()
    if "Doc Impact" not in content:
        return GateCheckResult("doc_impact_check", False, "PR 模板中未包含 'Doc Impact' 小节提示")
    return GateCheckResult("doc_impact_check", True, "PR 模板包含 'Doc Impact' 提示")

def run_gates(repo_path: Path, target_language: str, strict: bool = False) -> List[GateCheckResult]:
    results = []
    results.append(scan_for_placeholders(repo_path))
    results.append(check_required_files(repo_path, target_language))
    results.append(check_declaration_implementation_consistency(repo_path))
    results.append(check_selftest_records(repo_path))
    results.append(check_doc_impact(repo_path.parent / ".github" / "pull_request_template.md"))
    
    if strict:
        for res in results:
            if not res.passed:
                print(f"严格模式下，门禁 {res.name} 失败: {res.message}", file=sys.stderr)
                sys.exit(1)
    
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Agent Factory CI Gates.")
    parser.add_argument("--repo_path", type=str, default=".", help="Path to the agent repository.")
    parser.add_argument("--target_language", type=str, default="python", help="Target language of the agent (python/nodejs).")
    parser.add_argument("--strict", action="store_true", help="Exit immediately on first failure.")
    args = parser.parse_args()

    repo_path = Path(args.repo_path).resolve()
    results = run_gates(repo_path, args.target_language, args.strict)

    print("\n--- CI Gate Results ---")
    all_passed = True
    for res in results:
        status = "✅ PASSED" if res.passed else "❌ FAILED"
        print(f"{status}: {res.name} - {res.message}")
        if not res.passed: all_passed = False
    
    if not all_passed:
        print("\nCI Gate 检查失败，请修复上述问题。", file=sys.stderr)
        sys.exit(1)
    else:
        print("\nCI Gate 检查全部通过。")
```

**关键点：**
*   **模块化检查：** 每个检查项（如 `scan_for_placeholders`, `check_required_files`）都被封装为独立的函数，返回 `GateCheckResult` 对象，便于扩展和维护。
*   **占位符扫描：** 使用正则表达式扫描代码中的 `TODO`, `placeholder`, `FIXME` 等关键字，以及伪调用模式，强制开发者完成真实实现。
*   **声明-实现一致性：** 初步检查 README 中声明的入口文件是否存在，未来可扩展为更复杂的 AST 或语义分析，确保文档与代码行为一致。
*   **自测记录检查：** 强制要求功能完成度提升时附带自测记录文件，并通过检查这些文件的存在性来确保自测的执行。
*   **PR 模板检查：** 确保 PR 描述中包含 `Doc Impact` 小节，强制开发者关注文档同步更新。
*   **严格模式：** `--strict` 参数允许在 CI 环境中，一旦有任何门禁检查失败就立即退出，阻断后续流程。
*   **命令行接口：** 提供命令行接口，方便在 CI/CD 管道中集成和调用。

#### 17.7.2 沙箱策略

技术方案的 `8. 沙箱策略（全层次设计）` [1] 提出了四层沙箱分级，以确保智能体生成和执行过程的隔离性和安全性。在 LangGraph 框架中，沙箱的集成主要体现在节点执行环境的配置上。

##### 17.7.2.1 沙箱 A (进程级)：讨论阶段角色隔离

在 `DiscussionGraph` 中，每个角色智能体在生成观点时，其 LLM 调用应是独立的，并且其内部状态（如记忆）应与其它角色隔离。这可以通过为每个角色分配独立的 `Runnable` 实例，并确保其 `system_prompt` 和 `memory` 是独立的来实现。

```python
# agent_factory/discussion/discussion_graph.py (role_turn_node 内部)

# ... (省略)

    # 为每个角色创建独立的 LLM 实例或配置
    # 确保每个角色的系统提示词和记忆是独立的
    llm = ChatAnthropic(model="claude-opus-4-5", temperature=0.5)
    # 如果需要角色独立记忆，可以在这里加载或初始化
    # 例如：role_memory = get_role_memory(current_agent.slug, session_id)

    # 构建提示词，包含角色系统提示词、AgentSpec 和讨论历史
    # ... (省略)

    response = await llm.ainvoke(prompt)

# ... (省略)
```

##### 17.7.2.2 沙箱 B (容器级)：代码执行强制隔离

在 `development_node` 和 `quality_gate_node` 中执行代码生成和测试时，必须在一个隔离的容器环境中进行。这可以通过 Docker 或其他容器技术实现。`LanguageAwarePackager` 在 `verify_install` 阶段已经展示了如何使用 Docker 进行依赖安装验证，类似机制可用于代码执行。

```python
# agent_factory/development/code_executor.py (示例)

import docker
import os
from pathlib import Path

class CodeExecutor:
    def __init__(self, language: str):
        self.client = docker.from_env()
        self.language = language

    async def execute_code(self, code: str, dependencies: List[str], output_dir: Path) -> Dict[str, Any]:
        # 1. 创建临时目录，写入代码和依赖文件
        temp_dir = output_dir / "temp_execution"
        temp_dir.mkdir(exist_ok=True)
        
        if self.language == "python":
            (temp_dir / "main.py").write_text(code)
            (temp_dir / "requirements.txt").write_text("\n".join(dependencies))
            image = "python:3.12-slim"
            cmd = ["python", "main.py"]
        elif self.language == "nodejs":
            (temp_dir / "index.js").write_text(code)
            # TODO: 生成 package.json
            image = "node:20-slim"
            cmd = ["node", "index.js"]
        else:
            raise ValueError(f"不支持的语言: {self.language}")

        # 2. 构建或拉取 Docker 镜像
        # 实际可能需要更复杂的镜像管理，例如预构建基础镜像
        try:
            self.client.images.get(image)
        except docker.errors.ImageNotFound:
            print(f"拉取镜像 {image}...")
            self.client.images.pull(image)

        # 3. 运行容器执行代码
        container = None
        try:
            container = self.client.containers.run(
                image,
                command=cmd,
                volumes={str(temp_dir.resolve()): {'bind': '/app', 'mode': 'ro'}}, # 只读挂载代码
                working_dir="/app",
                detach=True,
                remove=True,
                network_disabled=True, # 默认禁用网络，除非明确需要
                mem_limit="512m", # 内存限制
                cpu_period=100000, # CPU 限制
                cpu_quota=50000, # 50% CPU
                environment={
                    "PYTHONUNBUFFERED": "1",
                    "NODE_ENV": "production"
                }
            )
            result = container.wait(timeout=60) # 等待容器完成，设置超时
            logs = container.logs().decode('utf-8')
            
            if result["StatusCode"] != 0:
                return {"success": False, "output": logs, "error": f"容器执行失败，退出码: {result['StatusCode']}"}
            return {"success": True, "output": logs}
        except docker.errors.ContainerError as e:
            return {"success": False, "output": e.stderr.decode('utf-8'), "error": str(e)}
        except docker.errors.ImageNotFound as e:
            return {"success": False, "output": "", "error": f"Docker 镜像未找到: {e}"}
        except Exception as e:
            return {"success": False, "output": "", "error": str(e)}
        finally:
            if container: # 确保容器被清理
                try: container.stop(timeout=5) 
                except: pass

# 在 development_node 或 quality_gate_node 中调用
async def development_node_with_sandbox(state: FactoryStateV3) -> FactoryStateV3:
    # ... (省略代码生成逻辑)
    executor = CodeExecutor(state["target_language"])
    execution_result = await executor.execute_code(generated_code, generated_dependencies, Path("/tmp"))
    
    if not execution_result["success"]:
        # 处理代码执行失败，可能触发失败恢复链
        state["failure"] = ClassifiedFailure(domain=FailureDomain.CODE_EXECUTION, ...)
        state["failed_node"] = "development"
        state["status"] = "development_failed"
        return state
    
    # ... (继续处理成功结果)
    return state
```

**关键点：**
*   **Docker 集成：** 使用 `docker-py` 库与 Docker 守护进程交互，创建和管理容器。
*   **资源限制：** 容器可以配置内存 (`mem_limit`)、CPU (`cpu_period`, `cpu_quota`) 等资源限制，防止恶意或失控代码耗尽系统资源。
*   **网络隔离：** `network_disabled=True` 默认禁用容器网络，增强安全性。只有在明确需要外部网络访问（如调用 MCP 服务器）时才应开启。
*   **只读挂载：** 将代码目录以只读方式挂载到容器中 (`mode='ro'`)，防止容器内的代码修改宿主机文件系统。
*   **超时控制：** `container.wait(timeout=60)` 设置容器执行超时，防止无限循环或长时间运行的任务。

##### 17.7.2.3 沙箱 C (容器级+网络模拟)：测试阶段

测试阶段的沙箱与代码执行沙箱类似，但可能需要更复杂的网络配置，例如模拟外部服务、数据库连接等。这可以通过 Docker Compose 或 Kubernetes 来管理。

```yaml
# docker-compose.test.yml (示例)

version: '3.8'
services:
  agent_under_test:
    build:
      context: ./agent_package
      dockerfile: docker/Dockerfile
    environment:
      - DATABASE_URL=postgres://user:password@db:5432/agent_db
      - MCP_SERVER_URL=http://mcp_mock:8080
    networks:
      - agent_network

  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=agent_db
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    networks:
      - agent_network

  mcp_mock:
    image: my_mcp_mock_server:latest # 模拟 MCP 服务器
    networks:
      - agent_network

networks:
  agent_network:
    driver: bridge
```

在 `quality_gate_node` 中，可以调用 `docker-compose` 命令来启动测试环境，运行测试，然后清理环境。

##### 17.7.2.4 沙箱 D (VM/全新容器)：交付验证

交付验证阶段的沙箱应尽可能模拟生产环境，确保生成的智能体在独立部署时能够正常运行。这通常意味着在一个全新的、干净的虚拟机或容器实例中进行最终的部署和冒烟测试。`AgentContractValidator` 应该在这个沙箱中运行。

#### 17.7.3 交付系统 (`AgentRuntimeContract`)

技术方案的 `13. 交付系统（Runtime Contract）` [1] 定义了 Agent Factory 生成的所有智能体必须遵循的运行时契约。这确保了生成智能体的可预测性、可测试性和可运维性。

##### 17.7.3.1 `AgentCapabilityManifest`

`AgentCapabilityManifest` 是智能体的机器可读能力宣言，通过 JSON Schema 定义，确保其结构和内容的一致性。

```python
# agent_factory/runtime/manifest_schema.py

AGENT_MANIFEST_SCHEMA = {
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "AgentCapabilityManifest",
  "description": "机器可读的智能体能力宣言",
  "type": "object",
  "required": [
    "agent_id", "agent_name", "version", "description",
    "supported_input_types", "supported_output_types", "primary_use_cases",
    "tools_available", "mcp_servers", "skills_loaded",
    "max_context_tokens", "max_response_tokens", "max_concurrent_sessions",
    "timeout_seconds", "required_env_vars", "required_services", "min_memory_mb"
  ],
  "properties": {
    "agent_id": { "type": "string", "pattern": "^[a-z0-9_-]+$" },
    "agent_name": { "type": "string", "minLength": 1 },
    "version": { "type": "string", "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$" },
    "description": { "type": "string" },
    "supported_input_types": { "type": "array", "items": { "type": "string" } },
    "supported_output_types": { "type": "array", "items": { "type": "string" } },
    "primary_use_cases": { "type": "array", "items": { "type": "string" } },
    "tools_available": { "type": "array", "items": { "type": "string" } },
    "mcp_servers": { "type": "array", "items": { "type": "string" } },
    "skills_loaded": { "type": "array", "items": { "type": "string" } },
    "max_context_tokens": { "type": "integer", "minimum": 1 },
    "max_response_tokens": { "type": "integer", "minimum": 1 },
    "max_concurrent_sessions": { "type": "integer", "minimum": 1 },
    "timeout_seconds": { "type": "integer", "minimum": 1 },
    "required_env_vars": { "type": "array", "items": { "type": "string" } },
    "required_services": { "type": "array", "items": { "type": "string" } },
    "min_memory_mb": { "type": "integer", "minimum": 64 },
    "factory_metadata": { "type": "object" }
  },
  "additionalProperties": false
}
```

##### 17.7.3.2 `AgentRuntimeContract` 基类

所有由 Agent Factory 生成的智能体都必须继承 `AgentRuntimeContract` 抽象基类，并实现其核心方法 (`invoke`, `stream`, `get_manifest`)。这确保了所有生成智能体都具有统一的调用接口和可发现的能力宣言。

```python
# agent_factory/runtime/contract.py

from abc import ABC, abstractmethod
import asyncio
import os
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional, Dict, Any, List

@dataclass
class AgentCapabilityManifest:
    agent_id: str
    agent_name: str
    version: str
    description: str
    supported_input_types: List[str]
    supported_output_types: List[str]
    primary_use_cases: List[str]
    tools_available: List[str]
    mcp_servers: List[str]
    skills_loaded: List[str]
    max_context_tokens: int
    max_response_tokens: int
    max_concurrent_sessions: int
    timeout_seconds: int
    required_env_vars: List[str]
    required_services: List[str]
    min_memory_mb: int
    factory_metadata: dict

@dataclass
class AgentInvokeRequest:
    session_id: str
    input: Any
    system_override: Optional[str] = None
    stream: bool = False
    timeout_override: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AgentInvokeResponse:
    session_id: str
    output: Any
    success: bool
    error: Optional[str] = None
    token_usage: Optional[dict] = None
    tool_calls_made: List[str] = field(default_factory=list)
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class AgentRuntimeContract(ABC):
    def __init__(self):
        self._active_sessions = 0

    @abstractmethod
    async def invoke(self, request: AgentInvokeRequest) -> AgentInvokeResponse:
        ...

    @abstractmethod
    async def stream(self, request: AgentInvokeRequest) -> AsyncIterator[str]:
        ...

    @abstractmethod
    def get_manifest(self) -> AgentCapabilityManifest:
        ...

    # 框架默认实现：运维接口（可覆盖）
    async def _ping_mcp_server(self, server: str) -> bool:
        return True

    async def _ping_llm(self) -> str:
        return "ok"

    async def health_check(self) -> dict:
        checks = {}
        for server in self.get_manifest().mcp_servers:
            try:
                ok = await self._ping_mcp_server(server)
                checks[f"mcp.{server}"] = "ok" if ok else "degraded"
            except Exception:
                checks[f"mcp.{server}"] = "failed"
        checks["llm"] = await self._ping_llm()

        overall = "healthy"
        if any(v == "failed" for v in checks.values()):
            overall = "unhealthy"
        elif any(v == "degraded" for v in checks.values()):
            overall = "degraded"
        return {"status": overall, "checks": checks}

    async def ready_check(self) -> bool:
        for env_var in self.get_manifest().required_env_vars:
            if not os.environ.get(env_var):
                return False
        return True

    async def graceful_shutdown(self, timeout_seconds: int = 30):
        deadline = asyncio.get_event_loop().time() + timeout_seconds
        while self._active_sessions > 0:
            if asyncio.get_event_loop().time() > deadline:
                break
            await asyncio.sleep(0.5)

    async def _enforce_resource_limits(self, request: AgentInvokeRequest):
        manifest = self.get_manifest()
        if self._active_sessions >= manifest.max_concurrent_sessions:
            raise TooManyConcurrentSessionsError("超过最大并发会话数")
        if len(str(request.input)) > manifest.max_context_tokens * 4:
            raise InputTooLargeError("输入内容过大")

class TooManyConcurrentSessionsError(Exception): pass
class InputTooLargeError(Exception): pass
```

##### 17.7.3.3 `AgentContractValidator`

`AgentContractValidator` 在交付阶段运行，负责验证生成的智能体是否符合 `AgentRuntimeContract`。这通常在沙箱 D 中进行。

```python
# agent_factory/delivery/contract_validator.py

import importlib.util
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass

from agent_factory.runtime.contract import AgentRuntimeContract, AgentInvokeRequest, AgentInvokeResponse, AgentCapabilityManifest

@dataclass
class ContractIssue:
    severity: str # CRITICAL, WARNING, INFO
    message: str

@dataclass
class ContractValidationReport:
    passed: bool
    issues: List[ContractIssue]

class AgentContractValidator:
    REQUIRED_METHODS = ["invoke", "stream", "get_manifest"]

    async def validate(self, agent_package_dir: Path) -> ContractValidationReport:
        issues = []

        # 动态加载 agent 类
        agent_class = self._import_agent_class(agent_package_dir)
        if not agent_class:
            issues.append(ContractIssue("CRITICAL", "无法加载 agent 主类"))
            return ContractValidationReport(False, issues)

        # 1. 检查继承关系
        if not issubclass(agent_class, AgentRuntimeContract):
            issues.append(ContractIssue("CRITICAL", "主类未继承 AgentRuntimeContract"))

        # 2. 检查必须实现的方法
        for method in self.REQUIRED_METHODS:
            if not hasattr(agent_class, method) or not callable(getattr(agent_class, method)):
                issues.append(ContractIssue("CRITICAL", f"缺少或未实现必须方法: {method}"))

        # 3. 检查 manifest 完整性
        manifest: Optional[AgentCapabilityManifest] = None
        try:
            agent_instance = agent_class()
            manifest = agent_instance.get_manifest()
            if not manifest.required_env_vars:
                issues.append(ContractIssue("WARNING", "required_env_vars 为空，可能遗漏必要的环境变量声明"))
            # TODO: 更多 manifest 字段的校验，例如版本号格式、输入输出类型是否合法等
        except Exception as e:
            issues.append(ContractIssue("CRITICAL", f"get_manifest() 异常: {e}"))

        # 4. invoke() 冒烟测试
        smoke_test_passed = False
        if manifest: # 只有 manifest 正常才能进行冒烟测试
            smoke_result = await self._smoke_test_invoke(agent_package_dir, agent_instance, manifest)
            if not smoke_result.success:
                issues.append(ContractIssue("CRITICAL", f"invoke() 冒烟测试失败: {smoke_result.error}"))
            else:
                smoke_test_passed = True

        # 5. health_check 测试
        if smoke_test_passed: # 只有冒烟测试通过才进行健康检查
            health = await agent_instance.health_check()
            if health.get("status") == "unhealthy":
                issues.append(ContractIssue("WARNING", f"health_check 报告 unhealthy: {health}"))

        return ContractValidationReport(
            passed=not any(i.severity == "CRITICAL" for i in issues),
            issues=issues
        )

    def _import_agent_class(self, agent_package_dir: Path):
        # 假设 agent 的主文件是 agent.py 或 index.js，并且主类名为 Agent
        # 这里以 Python 为例
        agent_file = agent_package_dir / "agent.py"
        if not agent_file.exists():
            return None
        
        spec = importlib.util.spec_from_file_location("agent_module", agent_file)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return getattr(module, "Agent", None) # 假设主类名为 Agent
        return None

    async def _smoke_test_invoke(self, agent_package_dir: Path, agent_instance: AgentRuntimeContract, manifest: AgentCapabilityManifest) -> AgentInvokeResponse:
        # 构造一个简单的 invoke 请求进行冒烟测试
        # 输入内容可以根据 manifest.supported_input_types 动态生成
        test_input = "hello world"
        if "json" in manifest.supported_input_types: test_input = {"query": "hello"}

        request = AgentInvokeRequest(
            session_id="smoke_test_session",
            input=test_input,
            stream=False,
            timeout_override=10 # 冒烟测试设置较短超时
        )
        try:
            response = await agent_instance.invoke(request)
            return response
        except Exception as e:
            return AgentInvokeResponse(
                session_id="smoke_test_session",
                output=None,
                success=False,
                error=str(e)
            )
```

**关键点：**
*   **JSON Schema 验证：** `AGENT_MANIFEST_SCHEMA` 定义了 `AgentCapabilityManifest` 的结构，可以在生成和验证阶段使用 `jsonschema` 库进行验证，确保 manifest 的格式正确性。
*   **抽象基类：** `AgentRuntimeContract` 强制所有生成的智能体实现统一的接口，包括同步调用 (`invoke`)、流式调用 (`stream`) 和能力宣言 (`get_manifest`)。
*   **运维接口：** `health_check` 和 `ready_check` 等方法提供了标准的运维探针，便于在生产环境中监控智能体的健康状况。
*   **资源限制：** `_enforce_resource_limits` 方法在运行时强制执行 manifest 中声明的资源限制，防止智能体滥用资源。
*   **动态加载与反射：** `AgentContractValidator` 通过 `importlib.util` 动态加载生成的智能体代码，并使用反射机制检查其是否符合契约要求。
*   **多层次验证：** 验证流程包括继承关系、方法实现、manifest 完整性、冒烟测试和健康检查，全面覆盖了契约的各个方面。

#### 17.7.4 语言感知打包器 (`LanguageAwarePackager`)

技术方案的 `13.6 语言感知打包器（LanguageAwarePackager）` [1] 解决了多语言环境下打包的复杂性。它根据目标语言生成正确的依赖清单、Dockerfile 和 README。

```python
# agent_factory/delivery/language_aware_packager.py

from enum import Enum
from pathlib import Path
from typing import Optional, List
import subprocess, json, textwrap
import docker # pip install docker

class TargetLanguage(str, Enum):
    PYTHON = "python"
    NODEJS = "nodejs"

@dataclass
class DepVerifyResult:
    success: bool
    install_log: str = ""
    error: str = ""

class LanguageAwarePackager:
    def __init__(self, language: TargetLanguage):
        self.language = language
        self.docker_client = docker.from_env()

    def generate_dependency_file(
        self,
        deps: List[str],
        dev_deps: Optional[List[str]] = None,
        output_dir: Path = Path("."),
        agent_name: str = "my-agent",
        version: str = "1.0.0",
    ) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        if self.language == TargetLanguage.PYTHON:
            return self._write_requirements_txt(deps, output_dir)
        else:
            return self._write_package_json(deps, dev_deps or [], output_dir, agent_name, version)

    def _write_requirements_txt(self, deps: List[str], output_dir: Path) -> Path:
        content = "\n".join(deps) + "\n"
        path = output_dir / "requirements.txt"
        path.write_text(content, encoding="utf-8")
        return path

    def _write_package_json(
        self,
        deps: List[str],
        dev_deps: List[str],
        output_dir: Path,
        agent_name: str,
        version: str,
    ) -> Path:
        def parse_dep(dep_str: str) -> tuple[str, str]:
            if dep_str.startswith("@"):
                parts = dep_str.rsplit("@", 1)
                return parts[0], parts[1] if len(parts) > 1 else "latest"
            else:
                parts = dep_str.split("@", 1)
                return parts[0], parts[1] if len(parts) > 1 else "latest"

        pkg = {
            "name": agent_name,
            "version": version,
            "description": f"Agent generated by Agent Factory",
            "main": "dist/agent.js",
            "scripts": {
                "start": "node dist/agent.js",
                "build": "tsc",
                "dev": "tsx agent.ts",
                "test": "jest"
            },
            "dependencies": {
                name: f"^{ver}" for name, ver in [parse_dep(d) for d in deps]
            },
            "devDependencies": {
                name: f"^{ver}" for name, ver in [parse_dep(d) for d in dev_deps]
            }
        }
        path = output_dir / "package.json"
        path.write_text(json.dumps(pkg, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def write_dockerfile(self, output_dir: Path, entry_file: str = None) -> Path:
        entry = entry_file or ("agent.py" if self.language == TargetLanguage.PYTHON else "agent.js")
        docker_dir = output_dir / "docker"
        docker_dir.mkdir(parents=True, exist_ok=True)
        path = docker_dir / "Dockerfile"

        if self.language == TargetLanguage.PYTHON:
            content = textwrap.dedent(f"""
                FROM python:3.12-slim
                WORKDIR /app
                COPY requirements.txt .
                RUN pip install --no-cache-dir -r requirements.txt
                COPY . .
                ENV PYTHONUNBUFFERED=1
                CMD ["python", "{entry}"]
            """)
        else:
            content = textwrap.dedent(f"""
                FROM node:20-slim
                WORKDIR /app
                COPY package.json ./
                RUN npm install --omit=dev
                COPY . .
                CMD ["node", "{entry}"]
            """)

        path.write_text(content, encoding="utf-8")
        return path

    def verify_install(self, output_dir: Path, timeout: int = 120) -> DepVerifyResult:
        # 确保 Dockerfile 存在
        dockerfile_path = output_dir / "docker" / "Dockerfile"
        if not dockerfile_path.exists():
            return DepVerifyResult(success=False, error="Dockerfile 不存在")

        # 构建镜像
        try:
            image_tag = f"agent-factory-temp-build:{output_dir.name.lower()}"
            self.docker_client.images.build(path=str(output_dir), dockerfile="docker/Dockerfile", tag=image_tag, rm=True)
        except docker.errors.BuildError as e:
            return DepVerifyResult(success=False, error=f"Docker 镜像构建失败: {e}")

        # 运行容器进行安装验证
        container = None
        try:
            if self.language == TargetLanguage.PYTHON:
                # Python 验证：尝试导入 agent 模块
                cmd = ["python", "-c", "import agent"]
            else:
                # Node.js 验证：尝试 require agent 模块
                cmd = ["node", "-e", "require('./agent.js')"]

            container = self.docker_client.containers.run(
                image_tag,
                command=cmd,
                working_dir="/app",
                detach=True,
                remove=True,
                network_disabled=True, # 验证安装时通常不需要网络
                environment={
                    "PYTHONUNBUFFERED": "1",
                    "NODE_ENV": "production"
                }
            )
            result = container.wait(timeout=timeout)
            logs = container.logs().decode('utf-8')

            if result["StatusCode"] != 0:
                return DepVerifyResult(success=False, install_log=logs, error=f"依赖安装验证失败，退出码: {result['StatusCode']}")
            return DepVerifyResult(success=True, install_log=logs)
        except docker.errors.ContainerError as e:
            return DepVerifyResult(success=False, install_log=e.stderr.decode('utf-8'), error=str(e))
        except Exception as e:
            return DepVerifyResult(success=False, error=str(e))
        finally:
            if container:
                try: container.stop(timeout=5)
                except: pass
```

**关键点：**
*   **语言枚举：** `TargetLanguage` 枚举清晰地定义了支持的语言类型。
*   **依赖文件生成：** `generate_dependency_file` 根据语言生成 `requirements.txt` (Python) 或 `package.json` (Node.js)，并确保版本号锁定。
*   **Dockerfile 生成：** `write_dockerfile` 根据语言选择正确的基础镜像和依赖安装命令，生成可用于构建 Docker 镜像的 Dockerfile。
*   **沙箱内依赖安装验证：** `verify_install` 方法在一个临时的 Docker 容器中执行依赖安装和基础的模块导入验证，确保生成的包是可部署和运行的。这使用了 `docker-py` 库与 Docker 守护进程交互。


---

## 16. MVP 最小可行实现方案

### 16.1 MVP 目标

**用最少的代码，在最短的时间内**，验证 Agent Factory 的核心价值主张：

> 用户指定需求和运行时语言（Python / Node.js） → 系统自动调用多个专业角色协作 → 输出一个依赖已安装、可直接运行的目标智能体

MVP 不追求完整性，只追求**端到端可演示**。语言选择是 MVP 必须支持的能力，因为它是用户最直接感受到"交付物可用"的信号——如果生成出来的代码缺少 `npm install` 或 `pip install` 步骤，用户根本无法运行。

---

### 16.2 MVP 裁剪原则

| 完整版功能 | MVP 处理方式 |
|-----------|------------|
| 147个角色动态加载 | 硬编码 5 个核心角色（Senior Developer、AI Engineer、Sprint Prioritizer、MCP Builder、Reality Checker）|
| 并行异步 DiscussionGraph | 串行讨论（3个角色轮流发言，2轮） |
| 反馈闭环（pgvector） | 完全跳过，每次任务独立决策 |
| 4层沙箱 | 只实现沙箱B（Docker代码执行隔离），其余用本地执行临时替代 |
| ToolSelector 向量索引 | 用 if-else 规则替代（web_search/code_exec/file_ops 三类） |
| 运行时契约验证 | 只做基础检查（invoke方法存在 + 冒烟测试） |
| Quality Gate 失败恢复 | 最多重试1次，失败直接人工介入 |
| 三个人机协作检查点 | 只保留检查点2（技术规格书审查），其余自动通过 |
| WebSocket实时推送 | 用轮询接口替代（每2秒 GET /status/{session_id}） |
| 成本预估 | 固定提示"Standard模式约$1-3" |
| **语言选择（Python/Node.js）** | **✅ MVP 必须实现**：用户通过 API 字段指定语言；自动生成对应依赖清单并在容器内完成安装验证（不支持自动推断，MVP 中语言为必填字段，缺失时直接返回 400） |
| 完整 LanguageAwarePackager | MVP 用精简版 `MvpLanguagePackager`：只处理依赖文件生成 + Docker安装验证，不生成 tsconfig.json / 不支持 TypeScript，Node.js 仅生成 CommonJS |

---

### 16.3 MVP 文件结构

```
agent_factory_mvp/
├── main.py                       # 入口：FastAPI + 主流程
├── state.py                      # MVP状态定义（含 target_language 字段）
├── registry_mvp.py               # 5个硬编码角色
├── discussion_mvp.py             # 串行讨论（3角色 × 2轮）
├── development_mvp.py            # 单角色开发节点（Backend Architect）
├── sandbox_mvp.py                # Docker沙箱B（代码执行隔离）
├── language_packager_mvp.py      # ✅ 精简语言感知打包器（依赖生成+安装验证）
├── delivery_mvp.py               # 基础打包 + 基础契约检查（调用language_packager）
├── agency_agents/                # git submodule（只用5个角色的md文件）
├── requirements.txt
└── docker-compose.yml            # postgres + redis（可选）
```

---

### 16.4 MVP 核心代码骨架

#### main.py — MVP 主入口

```python
# agent_factory_mvp/main.py

import asyncio
import uuid
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from state import MVPState
from registry_mvp import MVP_REGISTRY
from discussion_mvp import run_discussion
from development_mvp import run_development
from delivery_mvp import run_delivery

app = FastAPI(title="Agent Factory MVP")

# ── 请求模型（含语言字段）─────────────────────────────────────
class StartRequest(BaseModel):
    input: str
    language: str   # "python" 或 "nodejs"，MVP中为必填字段

    def validate_language(self):
        if self.language not in ("python", "nodejs"):
            raise HTTPException(
                status_code=400,
                detail=f"language 必须为 'python' 或 'nodejs'，收到: '{self.language}'"
            )

# ── 构建简化主图 ───────────────────────────────────────────────
def build_mvp_graph():
    graph = StateGraph(MVPState)

    graph.add_node("intake",      intake_node)
    graph.add_node("discussion",  discussion_node)
    graph.add_node("development", development_node)
    graph.add_node("delivery",    delivery_node)

    graph.set_entry_point("intake")
    graph.add_edge("intake",      "discussion")
    graph.add_edge("discussion",  "development")
    graph.add_edge("development", "delivery")
    graph.add_edge("delivery",    END)

    return graph.compile(
        checkpointer=MemorySaver(),
        interrupt_before=["development"]   # 只保留检查点2：技术规格书审查
    )

mvp_graph = build_mvp_graph()
sessions = {}

async def intake_node(state: MVPState) -> MVPState:
    """解析用户输入为简化的AgentSpec，语言已在API层确认"""
    from langchain_anthropic import ChatAnthropic
    
    language = state["target_language"]   # "python" 或 "nodejs"
    
    llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0)
    result = await llm.ainvoke(f"""
你是需求分析专家。用户想创建一个智能体，运行时语言已确认为：{language.upper()}

用户需求："{state['user_input']}"

请提取：
1. 智能体名称（英文，snake_case）
2. 核心功能（1-3条）
3. 需要的外部工具（web_search/code_exec/file_ops/none）
4. 目标用户
5. 依赖包列表（适用于 {language} 的真实包名，必须写明版本号）
   - Python 示例：["anthropic==0.40.0", "python-dotenv==1.0.1"]
   - Node.js 示例：["@anthropic-ai/sdk@0.37.0", "dotenv@16.4.7"]

以JSON格式返回，只返回JSON不要其他内容。字段：name, purpose, tools, target_user, dependencies
""")
    import json, re
    text = result.content
    match = re.search(r'\{{.*\}}', text, re.DOTALL)
    spec = json.loads(match.group()) if match else {
        "name": "my_agent",
        "tools": ["web_search"],
        "dependencies": []
    }
    spec["target_language"] = language
    return {{**state, "agent_spec": spec, "status": "intake_done"}}

async def discussion_node(state: MVPState) -> MVPState:
    """3角色串行讨论2轮，产出TechSpec（传递语言信息给讨论）"""
    tech_spec = await run_discussion(state["agent_spec"])
    return {{**state, "tech_spec": tech_spec, "status": "discussion_done"}}

async def development_node(state: MVPState) -> MVPState:
    """Backend Architect生成对应语言的智能体代码"""
    artifacts = await run_development(state["tech_spec"], state["target_language"])
    return {{**state, "artifacts": artifacts, "status": "development_done"}}

async def delivery_node(state: MVPState) -> MVPState:
    """打包 + 依赖安装验证 + 基础契约检查"""
    package = await run_delivery(
        artifacts=state["artifacts"],
        agent_spec=state["agent_spec"],
        language=state["target_language"]
    )
    return {{**state, "package": package, "status": "delivered"}}

# ── API 接口 ──────────────────────────────────────────────────
@app.post("/start")
async def start_task(body: StartRequest):
    body.validate_language()   # 语言校验，非法值直接400
    
    session_id = str(uuid.uuid4())
    config = {{"configurable": {{"thread_id": session_id}}}}
    asyncio.create_task(
        mvp_graph.ainvoke(
            {{
                "user_input": body.input,
                "target_language": body.language,
                "status": "started"
            }},
            config=config
        )
    )
    sessions[session_id] = config
    return {{
        "session_id": session_id,
        "target_language": body.language,   # 回显确认，方便调试
    }}

@app.get("/status/{session_id}")
async def get_status(session_id: str):
    config = sessions.get(session_id)
    if not config:
        return {{"error": "session not found"}}
    state = await mvp_graph.aget_state(config)
    return {{
        "status": state.values.get("status", "unknown"),
        "target_language": state.values.get("target_language"),
        "next": list(state.next),
        "interrupted": bool(state.next),
    }}

@app.post("/resume/{session_id}")
async def resume_task(session_id: str, body: dict):
    """用户审查TechSpec后点击继续"""
    config = sessions.get(session_id)
    if body.get("approved"):
        asyncio.create_task(mvp_graph.ainvoke(None, config=config))
    return {{"resumed": True}}

@app.get("/result/{session_id}")
async def get_result(session_id: str):
    config = sessions.get(session_id)
    state = await mvp_graph.aget_state(config)
    return state.values.get("package", {{}})
```

#### registry_mvp.py — 5个硬编码角色

```python
# agent_factory_mvp/registry_mvp.py

from pathlib import Path
import frontmatter

CORE_SLUGS = [
    "senior-developer",
    "ai-engineer",
    "sprint-prioritizer",
    "mcp-builder",
    "reality-checker",
]

def load_mvp_registry(agents_dir: Path = Path("agency_agents")) -> dict:
    """只加载5个核心角色"""
    registry = {}
    for slug in CORE_SLUGS:
        # 递归搜索，兼容不同子目录结构
        matches = list(agents_dir.rglob(f"{slug}.md"))
        if matches:
            post = frontmatter.load(matches[0])
            registry[slug] = {
                "slug": slug,
                "name": post.metadata.get("name", slug.replace("-", " ").title()),
                "system_prompt": post.content,
            }
        else:
            # Fallback：使用内置简化提示词
            registry[slug] = {
                "slug": slug,
                "name": slug.replace("-", " ").title(),
                "system_prompt": f"你是专业的{slug.replace('-', ' ')}，请从你的专业视角分析问题并给出建议。",
            }
    return registry

MVP_REGISTRY = load_mvp_registry()
```

#### language_packager_mvp.py — 精简语言感知打包器

```python
# agent_factory_mvp/language_packager_mvp.py
"""
MVP 精简版语言感知打包器。
与完整版 LanguageAwarePackager 的差异：
  - 不支持 TypeScript（Node.js 只生成 CommonJS 的 .js 文件）
  - 不生成 tsconfig.json
  - 依赖安装验证超时固定为 120 秒
  - 不生成 docker-compose.yml（只生成 Dockerfile）
"""

import json
import textwrap
from pathlib import Path
from dataclasses import dataclass

import docker  # pip install docker

@dataclass
class DepVerifyResult:
    success: bool
    install_log: str = ""
    error: str = ""

class MvpLanguagePackager:
    """
    根据 target_language 生成正确的依赖清单、Dockerfile、README快速上手，
    并在真实 Docker 容器内验证依赖安装成功。
    """

    SUPPORTED = ("python", "nodejs")

    def __init__(self, language: str):
        assert language in self.SUPPORTED, f"不支持的语言: {language}"
        self.language = language

    # ── 1. 生成依赖文件 ─────────────────────────────────────────

    def write_dependency_file(self, deps: list[str], output_dir: Path) -> Path:
        """
        Python → requirements.txt（每行一个包，版本号精确锁定）
        Node.js → package.json（CommonJS，包含 start/test 脚本）

        deps 格式（两种语言统一）：
          Python:  ["anthropic==0.40.0", "python-dotenv==1.0.1"]
          Node.js: ["@anthropic-ai/sdk@0.37.0", "dotenv@16.4.7"]
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        if self.language == "python":
            return self._write_requirements(deps, output_dir)
        else:
            return self._write_package_json(deps, output_dir)

    def _write_requirements(self, deps: list[str], output_dir: Path) -> Path:
        path = output_dir / "requirements.txt"
        path.write_text("\n".join(deps) + "\n", encoding="utf-8")
        return path

    def _write_package_json(self, deps: list[str], output_dir: Path) -> Path:
        def parse(dep: str):
            """'@anthropic-ai/sdk@0.37.0' → ('@anthropic-ai/sdk', '0.37.0')"""
            if dep.startswith("@"):
                name, _, ver = dep.rpartition("@")
                return name, ver or "latest"
            parts = dep.split("@", 1)
            return parts[0], parts[1] if len(parts) > 1 else "latest"

        pkg = {
            "name": output_dir.name,
            "version": "1.0.0",
            "description": "Generated by Agent Factory MVP",
            "main": "agent.js",
            "scripts": {
                "start": "node agent.js",
                "test": "node --experimental-vm-modules node_modules/.bin/jest"
            },
            "dependencies": {n: ver for n, ver in [parse(d) for d in deps]},
            "devDependencies": {
                "jest": "^29.0.0"
            }
        }
        path = output_dir / "package.json"
        path.write_text(json.dumps(pkg, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    # ── 2. 生成 Dockerfile ──────────────────────────────────────

    def write_dockerfile(self, output_dir: Path, entry_file: str = None) -> Path:
        entry = entry_file or ("agent.py" if self.language == "python" else "agent.js")
        docker_dir = output_dir / "docker"
        docker_dir.mkdir(parents=True, exist_ok=True)
        path = docker_dir / "Dockerfile"

        if self.language == "python":
            content = textwrap.dedent(f"""\
                FROM python:3.12-slim
                WORKDIR /app
                COPY requirements.txt .
                RUN pip install --no-cache-dir -r requirements.txt
                COPY . .
                ENV PYTHONUNBUFFERED=1
                CMD ["python", "{entry}"]
            """)
        else:
            content = textwrap.dedent(f"""\
                FROM node:20-slim
                WORKDIR /app
                COPY package.json ./
                RUN npm install --omit=dev
                COPY . .
                CMD ["node", "{entry}"]
            """)

        path.write_text(content, encoding="utf-8")
        return path

    # ── 3. 沙箱依赖安装验证 ────────────────────────────────────

    def verify_install(self, output_dir: Path, timeout: int = 120) -> DepVerifyResult:
        """
        在真实 Docker 容器内安装依赖并做最基础的导入验证。
        使用 docker SDK（同步版），MVP 不引入 asyncio 复杂度。

        验证逻辑：
          Python  → pip install -r requirements.txt && python -c "import agent"
          Node.js → npm install && node -e "require('./agent.js')"

        注意：容器需要网络访问（bridge模式）以拉取包，
        但不给写入系统目录权限（read-only 挂载源码）。
        """
        client = docker.from_env()

        if self.language == "python":
            image = "python:3.12-slim"
            cmd = (
                "sh -c 'pip install --no-cache-dir -r /app/requirements.txt 2>&1 "
                "&& python -c \"import sys; sys.path.insert(0,\\\"/app\\\"); "
                "import agent; print(\\\"VERIFY_OK\\\")\" 2>&1'"
            )
            ok_marker = "VERIFY_OK"
        else:
            image = "node:20-slim"
            cmd = (
                "sh -c 'cd /app && npm install --omit=dev 2>&1 "
                "&& node -e \"try{require(\\\"./agent.js\\\");"
                "console.log(\\\"VERIFY_OK\\\")}catch(e){console.error(e.message);process.exit(1)}\" 2>&1'"
            )
            ok_marker = "VERIFY_OK"

        try:
            logs = client.containers.run(
                image=image,
                command=cmd,
                volumes={str(output_dir.resolve()): {"bind": "/app", "mode": "rw"}},
                network_mode="bridge",
                mem_limit="512m",
                remove=True,
                timeout=timeout,
            )
            log_text = logs.decode("utf-8", errors="replace") if isinstance(logs, bytes) else logs
            success = ok_marker in log_text
            return DepVerifyResult(
                success=success,
                install_log=log_text,
                error="" if success else f"验证标记 '{ok_marker}' 未出现，安装或导入失败"
            )
        except docker.errors.ContainerError as e:
            return DepVerifyResult(success=False, error=str(e), install_log=str(e.stderr or ""))
        except Exception as e:
            return DepVerifyResult(success=False, error=f"Docker异常: {e}")

    # ── 4. 生成 README 快速上手 ─────────────────────────────────

    def quickstart_md(self, agent_name: str, env_vars: list[str]) -> str:
        env_block = "\n".join(f"{v}=your_key_here" for v in env_vars) or "# 无需额外配置"
        if self.language == "python":
            return textwrap.dedent(f"""\
                ## 快速上手

                ```bash
                # 1. 安装依赖
                pip install -r requirements.txt

                # 2. 配置环境变量
                cp .env.example .env
                # 编辑 .env：
                # {env_block}

                # 3. 运行
                python {agent_name}.py
                ```
            """)
        else:
            return textwrap.dedent(f"""\
                ## 快速上手

                ```bash
                # 1. 安装依赖
                npm install

                # 2. 配置环境变量
                cp .env.example .env
                # 编辑 .env：
                # {env_block}

                # 3. 运行
                npm start
                ```
            """)
```

```python
# agent_factory_mvp/discussion_mvp.py

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from registry_mvp import MVP_REGISTRY

DISCUSSION_ROLES = ["senior-developer", "ai-engineer", "sprint-prioritizer"]

async def run_discussion(agent_spec: dict) -> dict:
    """3角色 × 2轮串行讨论，产出 TechSpec（含语言感知的依赖列表）"""
    llm = ChatAnthropic(model="claude-opus-4-5", temperature=0.7)
    language = agent_spec.get("target_language", "python")

    discussion_history = []
    role_positions = {}

    for round_num in range(1, 3):  # 2轮
        for slug in DISCUSSION_ROLES:
            role = MVP_REGISTRY[slug]
            history_text = "\n".join([
                f"[{p['role']}]: {p['content'][:300]}..."
                for p in discussion_history[-6:]
            ])

            prompt = f"""
任务：为用户设计一个智能体
用户需求：{agent_spec}
目标运行时语言：{language.upper()}

当前讨论记录：
{history_text if history_text else '（讨论刚开始）'}

请从你的专业视角（{role['name']}）提出关键观点和建议。
特别注意：所有技术选型和依赖包必须适用于 {language.upper()} 运行时。
保持简洁，重点突出。100字以内。
"""
            resp = await llm.ainvoke([
                SystemMessage(content=role["system_prompt"]),
                HumanMessage(content=prompt)
            ])
            discussion_history.append({
                "role": role["name"],
                "round": round_num,
                "content": resp.content
            })
            role_positions[slug] = resp.content

    # 综合讨论结果生成 TechSpec（语言感知版）
    synthesis_llm = ChatAnthropic(model="claude-opus-4-5", temperature=0.1)
    all_opinions = "\n".join([f"{p['role']}: {p['content']}" for p in discussion_history])

    dep_format_hint = (
        'pip格式，精确版本，如 ["anthropic==0.40.0", "python-dotenv==1.0.1"]'
        if language == "python" else
        'npm格式，如 ["@anthropic-ai/sdk@0.37.0", "dotenv@16.4.7"]'
    )
    entry_file = "agent.py" if language == "python" else "agent.js"

    synthesis_resp = await synthesis_llm.ainvoke(f"""
基于以下专家讨论，生成智能体技术规格书（JSON格式，只返回JSON）：

目标运行时语言：{language.upper()}

{all_opinions}

输出字段：
- agent_name: 智能体名称（snake_case）
- purpose: 一句话描述
- target_language: "{language}"（固定值）
- tech_stack: 技术栈列表（必须适用于 {language}）
- core_capabilities: 核心能力列表
- tools_needed: 需要的工具列表
- dependencies: 依赖包列表（{dep_format_hint}）
- dev_dependencies: 开发依赖（测试框架等，同上格式）
- system_prompt_outline: 系统提示词大纲
- file_structure: 主要文件列表（入口文件为 {entry_file}）
- env_vars_needed: 需要配置的环境变量名列表（如 ANTHROPIC_API_KEY）
""")

    import json, re
    text = synthesis_resp.content
    match = re.search(r'\{.*\}', text, re.DOTALL)
    tech_spec = json.loads(match.group()) if match else {
        "agent_name": "my_agent",
        "target_language": language,
        "dependencies": [],
        "dev_dependencies": [],
        "env_vars_needed": ["ANTHROPIC_API_KEY"],
    }
    tech_spec["discussion_history"] = discussion_history
    return tech_spec
```

#### delivery_mvp.py — 打包与语言感知验证

```python
# agent_factory_mvp/delivery_mvp.py

import os, json
from pathlib import Path
from language_packager_mvp import MvpLanguagePackager

async def run_delivery(artifacts: dict, agent_spec: dict, language: str) -> dict:
    """
    生成完整的交付包文件结构，并验证依赖安装。
    language: "python" 或 "nodejs"
    """
    agent_name = agent_spec.get("name", "my_agent")
    output_dir = Path(f"output/{agent_name}")
    output_dir.mkdir(parents=True, exist_ok=True)

    packager = MvpLanguagePackager(language)

    # ── 1. 写入 LLM 生成的源码文件 ─────────────────────────────
    for filename, content in artifacts.items():
        (output_dir / filename).write_text(content, encoding="utf-8")

    # ── 2. 生成依赖清单（语言感知）─────────────────────────────
    deps = agent_spec.get("dependencies", [])
    dev_deps = agent_spec.get("dev_dependencies", [])
    packager.write_dependency_file(deps, output_dir)

    # ── 3. 生成 Dockerfile（语言感知）──────────────────────────
    entry = "agent.py" if language == "python" else "agent.js"
    packager.write_dockerfile(output_dir, entry_file=entry)

    # ── 4. 生成 .env.example ────────────────────────────────────
    env_vars = agent_spec.get("env_vars_needed", ["ANTHROPIC_API_KEY"])
    env_example = "\n".join(f"{v}=" for v in env_vars) + "\n"
    (output_dir / ".env.example").write_text(env_example, encoding="utf-8")

    # ── 5. 生成语言对应的 README ────────────────────────────────
    quickstart = packager.quickstart_md(agent_name, env_vars)
    readme = f"""# {agent_name}

{agent_spec.get('purpose', '')}

{quickstart}

## 功能

{chr(10).join(f"- {c}" for c in agent_spec.get("core_capabilities", []))}

## 工具配置

本智能体使用以下工具，请在 .env 中配置对应的 API Key：
{chr(10).join(f"- {t}" for t in agent_spec.get("tools_needed", []))}

## 运行时信息

- **语言**: {language.upper()}
- **入口文件**: {entry}
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")

    # ── 6. 依赖安装验证（在真实 Docker 容器内执行）───────────────
    dep_result = packager.verify_install(output_dir, timeout=120)

    # ── 7. 基础契约验证（检查 invoke 方法是否存在）───────────────
    agent_file = output_dir / entry
    if language == "python":
        contract_ok = agent_file.exists() and "async def invoke" in agent_file.read_text()
    else:
        contract_ok = agent_file.exists() and "invoke" in agent_file.read_text()

    return {
        "output_dir": str(output_dir),
        "files": [f.name for f in output_dir.iterdir()],
        "target_language": language,
        "entry_file": entry,
        "dependency_install": {
            "success": dep_result.success,
            "log_preview": dep_result.install_log[:500] if dep_result.install_log else "",
            "error": dep_result.error,
        },
        "contract_check": {
            "invoke_method_found": contract_ok,
        },
        "validation_passed": dep_result.success and contract_ok,
        "agent_name": agent_name,
    }
```

---

### 16.5 MVP 运行方式

```bash
# 1. 安装依赖（工厂本身的依赖，不是生成的智能体的）
pip install fastapi uvicorn langgraph langchain-anthropic python-frontmatter docker

# 2. 确认 Docker Desktop 已启动（依赖安装验证需要真实容器）
docker info   # 若输出正常则就绪

# 3. 设置环境变量
export ANTHROPIC_API_KEY=sk-ant-...

# 4. 启动服务
cd agent_factory_mvp
uvicorn main:app --reload --port 8000

# ──────────────────────────────────────────────────────────────────
# 5. 测试：Python 语言的智能体
# ──────────────────────────────────────────────────────────────────

# Step 1：发起任务（指定 language 字段，必填）
SESSION=$(curl -s -X POST http://localhost:8000/start \
  -H "Content-Type: application/json" \
  -d '{"input":"帮我做一个能搜索GitHub Issues并自动总结的代理","language":"python"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")
echo "Session: $SESSION"

# Step 2：轮询状态，等待检查点2（技术规格书审查）
while true; do
  STATUS=$(curl -s http://localhost:8000/status/$SESSION)
  echo $STATUS
  INTERRUPTED=$(echo $STATUS | python3 -c "import sys,json; print(json.load(sys.stdin).get('interrupted',False))")
  if [ "$INTERRUPTED" = "True" ]; then
    echo "=== 技术规格书已生成，等待审查 ==="
    break
  fi
  sleep 2
done

# Step 3：查看TechSpec（含 dependencies 和 target_language 字段）并确认继续
curl -s http://localhost:8000/result/$SESSION | python3 -m json.tool

# 审查OK后，确认继续开发
curl -X POST http://localhost:8000/resume/$SESSION \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'

# Step 4：轮询直到交付完成
while true; do
  STATUS=$(curl -s http://localhost:8000/status/$SESSION | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))")
  echo "当前状态: $STATUS"
  if [ "$STATUS" = "delivered" ]; then
    break
  fi
  sleep 3
done

# Step 5：查看交付结果（含 dependency_install 验证结果）
curl -s http://localhost:8000/result/$SESSION | python3 -m json.tool
# 期望输出中包含：
# "dependency_install": {"success": true, ...}
# "target_language": "python"
# "entry_file": "agent.py"

# ──────────────────────────────────────────────────────────────────
# 6. 测试：Node.js 语言的智能体（仅改 language 字段）
# ──────────────────────────────────────────────────────────────────
SESSION2=$(curl -s -X POST http://localhost:8000/start \
  -H "Content-Type: application/json" \
  -d '{"input":"帮我做一个能搜索GitHub Issues并自动总结的代理","language":"nodejs"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")
echo "Node.js Session: $SESSION2"
# 后续步骤与 Python 相同，交付结果中 entry_file 为 agent.js

# ──────────────────────────────────────────────────────────────────
# 7. 验证：缺少 language 字段时应返回 400
# ──────────────────────────────────────────────────────────────────
curl -s -X POST http://localhost:8000/start \
  -H "Content-Type: application/json" \
  -d '{"input":"帮我做一个代理"}' \
  | python3 -m json.tool
# 期望：{"detail": "language 必须为 'python' 或 'nodejs'，收到: ..."}
```

---

### 16.6 MVP → 完整版迁移路径

验证 MVP 核心流程后，按以下顺序逐步升级：

| 迁移步骤 | 替换内容 | 预估工时 |
|---------|---------|---------|
| Step 1 | 硬编码5角色 → 完整 AgentRegistry 动态加载 | 3天 |
| Step 2 | 串行讨论 → 并行异步 DiscussionGraph（Send API） | 3天 |
| Step 3 | 轮询状态 → WebSocket 实时推送 | 2天 |
| Step 4 | 必填语言字段 → 自动语言推断（IntakeAgent + 置信度阈值）| 2天 |
| Step 5 | MvpLanguagePackager → 完整 LanguageAwarePackager（TypeScript支持、tsconfig生成）| 2天 |
| Step 6 | 无反馈闭环 → pgvector + FeedbackAwareScorer | 4天 |
| Step 7 | if-else工具选择 → ToolCapabilityIndex 向量索引 | 3天 |
| Step 8 | 基础契约检查 → 完整 ContractValidator + 沙箱D | 3天 |
| Step 9 | 基础失败重试 → 完整 FailureRecovery 四层体系 | 5天 |
| Step 10 | 无可观测性 → LangSmith + OpenTelemetry | 2天 |

**总预估**：MVP 完成后，约 29 个工作日可迁移到完整版生产系统。

---


---

---

*文档版本：Merged v1 | 合并时间：2026-03-30 | 基础文档：Final Clean v2（2026-03-27）| 新增：§17 核心模块代码实现建议（来源：Manus AI，2026-03-30）| 角色数据以 git clone agency-agents 实际内容为准*

