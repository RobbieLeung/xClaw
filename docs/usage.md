# 使用 dev-team

## 运行要求

使用支持原生子 agent 和 `.codex/agents/*.toml` 角色配置的 Codex，主会话建议选择 `gpt-6.1-sol`。模型 provider 需要能够提供三个角色配置中指定的模型。委派前确认 `dev-team` 和 architect、developer、checker 均已识别。

## 安装到目标仓库或个人目录

从 dev-team 根目录运行下面的命令。`dev_team_target` 是已经存在的目标仓库；改成 `"$HOME"` 可安装为用户级 skill 与角色。脚本先检查全部目标，遇到同名 skill、角色文件或软链接就退出，不覆盖。目标已有 `.codex/config.toml` 时保留它，再手动合并后面的配置。

```bash
dev_team_target=/absolute/path/to/target-repo
python3 - "$PWD" "$dev_team_target" <<'PY'
from pathlib import Path
import shutil
import sys

source, target = (Path(value).expanduser().resolve() for value in sys.argv[1:])
if not target.is_dir():
    raise SystemExit("Target directory must already exist")
paths = [Path(".agents/skills/dev-team")]
paths += [Path(".codex/agents") / (name + ".toml")
          for name in ("architect", "developer", "checker")]
for path in paths:
    if not (source / path).exists():
        raise SystemExit("Missing source: " + str(path))
    destination = target / path
    if destination.exists() or destination.is_symlink():
        raise SystemExit("Refusing to replace: " + str(destination))
for path in paths:
    destination = target / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    if (source / path).is_dir():
        shutil.copytree(source / path, destination)
    else:
        shutil.copy2(source / path, destination)
config = target / ".codex/config.toml"
if not config.exists() and not config.is_symlink():
    shutil.copy2(source / ".codex/config.toml", config)
else:
    print("Existing config preserved; merge [agents] manually")
print("Installed dev-team and three agent configurations")
PY
```

安装前也应检查个人目录中是否已经存在同名角色，避免项目角色遮蔽原有个人角色。更新已有安装时先查看差异，不直接重复覆盖。配置只放在 dev-team 仓库不会让其他仓库自动获得三个角色；仅复制 skill 也不会注册角色。

已有配置中合并下列字段，不要重复创建 `[agents]` 表，不覆盖其他设置；已有更低的并发限制可以保留：

```toml
[agents]
enabled = true
max_concurrent_threads_per_session = 2
```

此上限是同时打开的子 agent 线程数，不含主会话，也不是费用或重试上限。按宿主要求信任项目配置并重新启动会话；确认 `dev-team` 和三个自定义角色均被识别。不要把 skill 的 `agents/openai.yaml` UI 元数据误当作子 agent 配置。

## 开始工作

在实际目标仓库启动 Codex 后输入：

```text
$dev-team 给 vLLM 增加一个调度策略，先设计方案，再实现和验证。
```

角色文件的 `model` 与 `model_reasoning_effort` 固定其设置。子 agent 继承父会话的 provider、工具和权限；项目配置不会提供新的模型权限，也不会给 architect/checker 创建独立只读沙箱。

主会话根据任务需要调用已安装的角色，接收设计或检查结果，再派发后续任务。子 agent 只完成被分配的工作，需要其他角色时返回主会话。小任务可由主会话直接完成；角色、原生工具或指定模型缺失时，明确报告缺项，并继续不依赖该能力的工作。

## 执行检查

Python 3.9+，macOS/Linux，无第三方依赖。每次运行都有独立工件目录：

```bash
python3 /installed/path/dev-team/scripts/run-checks.py \
  --cwd /absolute/path/to/target-repo --timeout 300 \
  --output-dir /absolute/path/to/check-artifacts -- \
  python3 -m unittest discover -s tests -v
```

使用目标项目自己的命令，例如 `pytest`、`ctest` 或 benchmark 命令；测试入口不自动猜测测试套件。参数按原样传给子进程，shell 管道、变量展开和通配符不会自动执行。不要把凭据写进命令或输出；脚本不保存命令参数和环境变量，但会原样保存子进程的 stdout/stderr。

| 情形 | 结果状态 | 脚本退出码 |
| --- | --- | --- |
| 命令正常返回 0 | `passed` | 0 |
| 检查失败 | `failed` | 命令退出码；信号退出映射为 128 + 信号编号 |
| 超时 | `timed_out` | 124 |
| Ctrl-C | `interrupted` | 130 |
| 找不到可执行文件 | `launch_failed` | 127 |
| 其他启动/工件写入错误 | `launch_failed` 或明确错误 | 126 |
| 缺命令、非法超时/目录 | 参数错误，未执行 | 2 |

`result.json` 包含状态、退出码、耗时、工作目录和日志路径。人工判断测试是否实际覆盖需求；“运行了一个返回 0 的空命令”不构成验收。

## 原生委派验证

使用临时项目和合成代码验证真实协作，保留子线程事件、最终 diff 与测试输出。一次完整验证应观察到主会话分派角色、子 agent 执行工具、主会话核对证据并交付，而不是只有模型文本声称已经委派。

按以下场景检查实际行为：

| 场景 | 应观察到的行为 |
| --- | --- |
| 小型明确改动 | 主会话直接完成并验证 |
| 有设计取舍的实现 | architect 返回方案，主会话派发 developer，再由 checker 检查稳定代码 |
| 检查失败 | checker 提供证据，主会话派发修复；设计原因交 architect 诊断 |
| 缺少角色或模型 | 主会话明确报告缺项，未执行的委派保持未验证状态 |

本地单元测试覆盖安装和检查脚本，不能证明真实模型委派成功。完整原生委派、跨线程工具执行和失败修复闭环尚未验证；此前免费测试端点拒绝了当前 Codex 请求中的 `input_text` 内容格式。

## 自定义测试模型

测试免费或自建模型时，先确认模型列表、Responses API 流式和工具调用均可用于当前 Codex 客户端。[官方 provider 文档](https://learn.chatgpt.com/docs/config-file/config-advanced)

不要修改真实的用户配置或正式角色模型。创建临时 `CODEX_HOME` 和一个只有合成代码的测试仓库，把 skill 与三份角色配置复制进去；只在临时副本把三个角色的模型改成端点实际公布的模型 ID，并选择该模型支持的推理强度。在临时用户配置中设置：

```toml
model = "MODEL_ID_FROM_ENDPOINT"
model_provider = "smoke"

[model_providers.smoke]
name = "Isolated smoke endpoint"
base_url = "https://your-endpoint/v1"
wire_api = "responses"
request_max_retries = 0
stream_max_retries = 0

# 若端点需要认证，使用 env_key 引用环境变量；不要把值写入文件。
```

在临时项目中启动一次 Codex 会话，由该会话原生派发三个测试角色。限制单次验证的总时间，按前一节核对真实委派、模型路由、最终 diff 与测试输出。

使用测试模型验证的结果只适用于该端点和模型。正式 Astra/Sol/Luna 的访问权限与协作表现需要使用正式角色配置另行验证。
