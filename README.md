# Coding Agent System

多智能体协作的代码生成系统 - 第一阶段：TUI 入口与配置管理

## 项目简介

这是一个基于 LangGraph 的多智能体协作系统，旨在从自然语言描述自动完成软件开发任务。当前实现了第一阶段：友好的 TUI（Terminal User Interface）交互界面和配置管理系统。

## 功能特性

### 第一阶段（已完成）✅
- ✅ 使用 Rich 库构建的美观终端用户界面
- ✅ 基于 Pydantic 的配置文件读取和验证
- ✅ 欢迎界面和系统信息显示
- ✅ 配置信息表格展示（自动遮蔽敏感信息）
- ✅ 任务输入界面
- ✅ Rich 美化的日志系统

### 后续阶段（规划中）🚧
- 🚧 Phase 2: 实现 Planning、Coding、Evaluation 三种 Agent
- 🚧 Phase 3: 使用 LangGraph 构建多智能体协作工作流
- 🚧 Phase 4: 集成文件系统、Web 搜索、代码执行等工具
- 🚧 Phase 5: 完成 arXiv CS Daily 测试用例

## 项目结构

```
assignment1/
├── .env                    # 环境变量配置
├── .env.example           # 配置模板
├── pyproject.toml         # 项目配置（uv 管理）
├── README.md              # 本文档
│
├── src/                   # 源代码
│   ├── config/            # 配置管理
│   │   └── settings.py    # 配置加载与验证
│   ├── ui/                # TUI 界面
│   │   ├── welcome.py     # 欢迎界面
│   │   ├── display.py     # 配置显示
│   │   └── input.py       # 任务输入
│   ├── utils/             # 工具函数
│   │   └── logger.py      # 日志配置
│   ├── agents/            # Agent 模块（Phase 2）
│   ├── tools/             # 工具模块（Phase 4）
│   ├── graph/             # LangGraph 工作流（Phase 3）
│   └── main.py            # 主入口
│
├── workspace/             # Agent 工作目录
└── logs/                  # 日志文件
```

## 安装与配置

### 1. 环境要求

- Python >= 3.14
- [uv](https://github.com/astral-sh/uv) 包管理器

### 2. 安装 uv（如果尚未安装）

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 3. 克隆项目并安装依赖

```bash
cd assignment1

# 创建虚拟环境（如果还没有）
uv venv

# 激活虚拟环境
source .venv/bin/activate  # macOS/Linux
# 或
.venv\Scripts\activate     # Windows

# 安装依赖
uv sync
```

### 4. 配置环境变量

复制 `.env.example` 并修改为你的配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的配置：

```ini
# OpenAI Compatible API Configuration
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4

# Workspace Configuration
WORKSPACE_DIR=./workspace

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/code-agent.log
```

## 使用方法

### 运行程序

```bash
# 方法 1: 使用 uv run（推荐）
uv run python -m src.main

# 方法 2: 激活虚拟环境后运行
source .venv/bin/activate
python -m src.main

# 调试模式
uv run python -m src.main --debug
```

### 使用示例

运行程序后，你会看到：

1. **欢迎界面**：显示项目信息和系统状态
2. **配置信息**：以表格形式展示所有配置（API Key 已遮蔽）
3. **任务输入**：提示输入开发任务描述

示例输入：
```
Task Description: Build a simple calculator web app with HTML, CSS and JavaScript
```

程序会确认接收到的任务并记录日志。

## 技术栈

### 核心依赖
- **python-dotenv**: 环境变量管理
- **pydantic**: 配置验证和数据建模
- **pydantic-settings**: 设置管理
- **rich**: 终端 UI 美化
- **langchain**: LLM 框架（后续阶段使用）
- **langgraph**: 工作流编排（后续阶段使用）
- **openai**: OpenAI API 客户端

### 开发工具
- **pytest**: 单元测试
- **black**: 代码格式化
- **flake8**: 代码检查

## 开发说明

### 代码规范

项目遵循 PEP 8 标准：

```bash
# 格式化代码
uv run black src/

# 检查代码
uv run flake8 src/
```

### 运行测试

```bash
uv run pytest
```

### 日志系统

日志同时输出到：
- **控制台**：使用 Rich 美化，实时显示
- **文件**：保存到 `./logs/code-agent.log`

日志级别可通过 `.env` 中的 `LOG_LEVEL` 配置。

## 项目特色

1. **模块化设计**：清晰的目录结构，便于扩展
2. **类型安全**：使用 Pydantic 进行配置验证
3. **美观界面**：Rich 库提供的精美终端 UI
4. **安全性**：敏感信息（API Key）自动遮蔽
5. **完善日志**：双输出日志系统，方便调试
6. **现代工具链**：使用 uv 进行快速包管理

## 下一步计划

完成第一阶段后，将按以下顺序开发：

### Phase 2: Agent 实现
- 定义 Agent 基类
- 实现 Planning Agent（任务分解）
- 实现 Coding Agent（代码生成）
- 实现 Evaluation Agent（代码评审）
- 设计高质量的系统提示词

### Phase 3: LangGraph 工作流
- 定义状态图结构
- 实现 Agent 之间的协作流程
- 添加检查点和状态管理
- 实现任务调度逻辑

### Phase 4: 工具集成
- 文件系统工具（create_file, write_to_file, read_file）
- Web 搜索工具（集成 Brave Search API）
- 代码执行工具（Shell 命令执行）

### Phase 5: 测试与优化
- 完成 arXiv CS Daily 网页生成测试
- 优化提示词和工作流
- 性能调优
- 撰写项目报告

## 作业要求

本项目是 COMP7103C 课程作业的一部分。完整要求请参考 `COMP7103C Course Assignment Instructions (1).pdf`。

### 最终交付物
- ✅ Git 仓库链接（包含详细 README）
- 📝 项目报告（PDF）
- 🎥 TA 现场演示

## 许可证

本项目仅用于学术目的。

## 联系方式

如有问题，请联系助教：
- Zongwei Li: zongwei9888@gmail.com
- Yangqin Jiang: mrjiangyq99@gmail.com

---

**当前版本**: v0.1 (Phase 1 完成)
**最后更新**: 2024-12-13
