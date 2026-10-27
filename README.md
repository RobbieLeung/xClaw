# dev-team：多 agent 开发框架

dev-team（开发小队）用一个 Codex 主会话组织设计、实现与验证。主 skill 定义协作策略，三个原生子 agent 承接有明确边界的任务，测试入口记录可复核的执行结果。主会话负责目标、分派、整合和最终验收。

```text
.agents/skills/dev-team/
  SKILL.md                       协作策略与精简交接
  scripts/run-checks.py           确定性的测试执行与结果记录
.codex/
  config.toml                    最多两个并发子 agent
  agents/architect.toml           Astra / medium：复杂设计、诊断
  agents/developer.toml           Sol / medium：实现、修复
  agents/checker.toml             Luna / high：明确检查与证据
```

主会话建议选择 `gpt-6.1-sol`。小任务直接完成；复杂设计交给 architect，实现与修复交给 developer，明确检查交给 checker。按任务需要选择角色，只有主会话可以分派子任务。共享 worktree 中同时只有一个代码写入者。

## 安装和使用

需要支持原生子 agent 和独立 TOML 角色配置的 Codex 客户端，以及配置中各模型的访问权限。使用前确认 `dev-team` 与 architect、developer、checker 均已识别。用于其他项目时，把 skill 和角色配置安装到实际工作的目标仓库，或用户级目录。

详见 [安装、使用与验证](docs/usage.md)。安装不会替换已有角色、skill 或用户配置。

在目标仓库启动 Codex 后输入：

```text
$dev-team 给 vLLM 增加一个调度策略，先设计方案，再实现和验证。
```

## 本仓库验证

测试仅使用 Python 3.9+ 标准库，不依赖模型服务：

```bash
python3 .agents/skills/dev-team/scripts/run-checks.py \
  --cwd . --timeout 60 --output-dir .dev-team/checks -- \
  python3 -m unittest discover -s tests -v
```

本地测试覆盖安装与检查命令执行。原生委派的端到端验证方法及验证范围见 [使用文档](docs/usage.md#原生委派验证)。

## 运行边界

执行依赖当前 Codex 会话提供的原生工具、角色加载、模型权限和 provider。委派需要对应的已安装角色；能力缺失时明确报告，继续不依赖该角色的工作。

Skill 是工作指引。并发上限由宿主配置控制；重试约定、写入职责和禁止子 agent 递归分派依赖 agent 遵循指令。脚本约束单条命令的超时；整体预算需要宿主提供控制。角色继承父会话权限与 provider，“只读职责”不产生额外沙箱。

完整协作策略与角色边界见 [dev-team](.agents/skills/dev-team/SKILL.md)。

配置依据：[官方子 agent 文档](https://learn.chatgpt.com/docs/agent-configuration/subagents)、[官方 Skills 文档](https://learn.chatgpt.com/docs/build-skills)、[配置参考](https://learn.chatgpt.com/docs/config-file/config-reference)。
