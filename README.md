# SurveyEase - 智能调研助手

## 项目简介

SurveyEase 是一个基于 AI 的智能调研平台，专门用于进行消费者调研。通过聊天对话的方式，系统能够自动引导用户完成深度调研，收集有价值的用户洞察和反馈。

<img src="images/main.png" alt="Alt text" width="600" height="500">

### 项目场景

- **消费者调研**：通过自然对话收集用户对产品、服务的真实反馈
- **用户画像构建**：深入了解用户的消费习惯、偏好和需求
- **市场研究**：获取第一手的市场洞察和用户行为数据
- **产品优化**：基于用户反馈指导产品改进方向

## 技术架构

### 前端技术栈
- **React 18** + **TypeScript** - 现代化前端框架
- **Vite** - 快速构建工具
- **Express** - 静态文件服务器
- **Socket.io** - 实时通信
- **Axios** - HTTP 客户端

### 后端技术栈
- **FastAPI** - 高性能 Python Web 框架
- **LangGraph** - 对话流程管理
- **LangChain** - LLM 应用开发框架
- **LangMem** - 智能记忆管理
- **Pydantic** - 数据验证和序列化
- **SQLAlchemy** - ORM 框架
- **MySQL** - 关系型数据库

## 项目结构

```
SurveyEase/
├── se-backend/                 # 后端服务
│   ├── api/                   # API 接口层
│   │   ├── host.py           # 主持人管理 API
│   │   ├── survey.py         # 调研对话 API
│   │   └── template.py       # 模板管理 API
│   ├── cfg/                  # 配置管理
│   │   ├── environment.py   # 环境管理
│   │   └── setting.py       # 应用配置
│   ├── database/            # 数据库管理
│   │   ├── __init__.py
│   │   ├── connection.py    # MySQL连接管理
│   │   └── models.py        # 数据库模型定义
│   ├── constants/            # 常量定义
│   ├── graph/                # 对话图管理
│   │   └── survey_graph.py   # 调研对话流程
│   ├── llm_provider/         # LLM 提供商
│   ├── memory/               # 记忆管理
│   │   └── embeddings.py     # 向量嵌入
│   ├── services/             # 服务层
│   │   ├── service_manager.py # 服务管理器
│   │   └── chat_service.py   # 聊天记录服务
│   ├── utils/                # 工具类
│   │   ├── custom_serializer.py
│   │   ├── json_utils.py
│   │   └── unified_logger.py
│   ├── scripts/              # 启动脚本
│   │   ├── start.sh         # Python启动脚本
│   │   └── start_uvicorn.sh # Uvicorn启动脚本
│   ├── main.py               # 应用入口
│   └── pyproject.toml        # 项目配置
├── se-frontend/              # 前端应用
│   ├── src/
│   │   ├── components/       # React 组件
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── HostConfig.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   └── SurveyConfig.tsx
│   │   ├── hooks/            # 自定义 Hooks
│   │   │   └── useSurvey.ts
│   │   ├── services/         # API 服务
│   │   │   └── api.ts
│   │   ├── types/            # 类型定义
│   │   │   └── index.ts
│   │   └── utils/            # 工具函数
│   ├── package.json          # 前端依赖
│   └── server.js             # 静态服务器
└── README.md
```

## 核心模块

### 1. 对话流程管理 (SurveyGraph)
- **多轮对话控制**：支持复杂的多步骤调研流程
- **智能节点切换**：根据用户回答自动决定下一步
- **条件跳转**：支持基于条件的智能跳转，可根据用户回答跳转到不同步骤或结束流程
- **状态持久化**：使用 LangGraph 检查点机制保存对话状态
- **记忆压缩**：集成 LangMem 实现智能记忆管理
<img src="images/steps.png" alt="Alt text" width="600" height="500">

### 2. 模板管理系统
- **动态模板**：支持创建、编辑、删除调研模板
- **步骤配置**：灵活定义调研步骤和问题
  - **顺序跳转**：按顺序执行下一步骤
  - **条件跳转**：根据条件判断跳转到不同步骤或结束流程
- **变量系统**：支持定义变量并在模板中引用，使用 `{{变量key}}` 格式
- **主持人绑定**：为模板选择主持人，主持人角色信息自动追加到系统提示
- **背景知识**：可配置背景知识，自动拼接到系统提示
- **系统提示**：自定义 AI 调研员的行为和风格
- **最大轮数控制**：配置每个步骤最多对话轮数
- **模板缓存**：提高模板加载性能
<img src="images/basic.png" alt="Alt text" width="600" height="500">

### 3. 智能记忆管理
- **语义记忆**：自动提取和存储关键信息
- **消息压缩**：在节点切换时压缩对话历史
- **事实保留**：确保重要信息不丢失
- **向量存储**：使用嵌入向量进行语义搜索

### 4. 实时通信
- **流式响应**：支持实时显示 AI 回复
- **WebSocket**：前端与后端实时通信
- **状态同步**：保持前后端状态一致

### 5. 聊天记录管理
- **数据库存储**：所有聊天记录存储在 MySQL 数据库中
- **会话管理**：支持按会话ID查询和管理聊天记录
- **消息持久化**：实时保存每条消息到数据库
- **历史记录查询**：支持查询所有会话列表和详细信息

### 6. 主持人管理系统
- **主持人管理**：支持创建、编辑、删除主持人配置
- **角色定义**：为每个主持人定义独特的角色和性格
- **自动集成**：选择主持人后，角色信息自动追加到系统提示中
<img src="images/hosts.png" alt="Alt text" width="600" height="500">

### 7. 变量与高亮系统
- **变量定义**：在模板中定义可复用变量
- **变量引用**：在主题、系统提示、步骤内容中使用 `{{变量key}}` 格式引用
- **实时高亮**：输入框实时高亮显示变量引用，提升编辑体验
- **字符计数**：所有输入字段显示字符计数，便于控制内容长度

## 安装和启动

### 环境要求
- Python 3.11+
- Node.js 18+
- MySQL 5.7+ 或 MySQL 8.0+
- 支持的 LLM 提供商：Azure OpenAI、阿里云百炼

### 数据库初始化

在启动后端服务之前，需要先创建数据库并执行建表 SQL：

1. **创建数据库**
```sql
CREATE DATABASE survey_ease CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. **执行建表 SQL**

执行建表脚本：
```bash
mysql -u your_username -p survey_ease < se-backend/database/init.sql
```

或者直接在 MySQL 客户端中执行：
```sql
USE survey_ease;
SOURCE se-backend/database/init.sql;
```

数据库表结构包括：
- `ai_hosts` - 主持人表
- `ai_survey_templates` - 调研模板表
- `ai_survey_template_steps` - 调研模板步骤表
- `ai_survey_template_variables` - 调研模板变量表
- `ai_conversations` - 会话记录表
- `ai_chat_messages` - 聊天消息表

详细的建表 SQL 脚本位于 `se-backend/database/init.sql`，也可以参考模型定义文件 `se-backend/database/models.py`。

### 后端安装和启动

1. **进入后端目录**
```bash
cd se-backend
```

2. **安装依赖**
```bash
# 使用 uv 安装（推荐）
uv sync

# 或使用 pip 安装
pip install -e .
```

3. **配置环境变量**

项目支持多环境配置（本地环境、测试环境、生产环境）。根据你的需求创建对应的配置文件：

> **注意**：请使用 `.env.local`、`.env.test` 或 `.env.prod`

**本地开发环境** - 创建 `.env.local` 文件：
```env
# 环境配置
ENV=local

# Azure OpenAI 配置
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
AZURE_OPENAI_ENDPOINT=your_azure_endpoint
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# 阿里云百炼配置
DASHSCOPE_API_KEY=your_dashscope_api_key

# LLM 配置
FAST_LLM=azure_openai:gpt-4o-mini
EMBEDDING=dashscope:text-embedding-v2

# 服务器配置
HOST=0.0.0.0
PORT=8000

# MySQL数据库配置（本地环境）
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=survey_ease
MYSQL_USERNAME=root
MYSQL_PASSWORD=your_local_password
MYSQL_CHARSET=utf8mb4
MYSQL_USE_SSL=false
MYSQL_POOL_SIZE=10
MYSQL_POOL_RECYCLE=3600
```

**测试环境** - 创建 `.env.test` 文件（配置示例）：
```env
ENV=test
# ... 其他配置项，参考本地环境格式
# MySQL配置会使用测试环境的默认值
```

**生产环境** - 创建 `.env.prod` 文件（配置示例）：
```env
ENV=prod
# ... 其他配置项，参考本地环境格式
# MySQL配置会使用生产环境的默认值
```

> **注意**：
> - 必须创建对应环境的配置文件（`.env.local`、`.env.test` 或 `.env.prod`）
> - 如果不创建环境配置文件，系统会使用代码中的默认配置
> - 每个环境都有对应的 MySQL 默认配置（可在代码中查看或通过环境变量覆盖）
> - 生产环境密码建议从环境变量或密钥管理服务获取，不要直接写在配置文件中

4. **启动后端服务**

支持多种启动方式，可以根据环境选择：

**方式一：使用命令行参数指定环境**
```bash
# 本地环境
python main.py --env local

# 测试环境
python main.py --env test

# 生产环境
python main.py --env prod
```

**方式二：使用环境变量指定**
```bash
# 设置环境变量后启动
export ENV=test
python main.py

# 或使用 uvicorn
ENV=test uvicorn main:app --host 0.0.0.0 --port 8000
```

**方式三：使用启动脚本（推荐）**
```bash
# 使用启动脚本（Python 直接启动）
./scripts/start.sh local    # 本地环境
./scripts/start.sh test     # 测试环境
./scripts/start.sh prod     # 生产环境

# 使用 Uvicorn 启动脚本（支持热重载，适合开发）
./scripts/start_uvicorn.sh local   # 本地环境（开发模式）
./scripts/start_uvicorn.sh test   # 测试环境
```

**方式四：使用 uvicorn 直接启动**
```bash
# 本地环境（开发模式，支持热重载）
ENV=local uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 测试/生产环境
ENV=test uvicorn main:app --host 0.0.0.0 --port 8000
ENV=prod uvicorn main:app --host 0.0.0.0 --port 8000
```

> **配置优先级**（从高到低）：
> 1. 命令行参数 `--env`
> 2. 环境变量 `ENV`
> 3. `.env.{env}` 文件中的配置
> 4. 代码中的默认配置

### 前端安装和启动

1. **进入前端目录**
```bash
cd se-frontend
```

2. **安装依赖**
```bash
npm install
```

3. **启动开发服务器**
```bash
# 开发模式
npm run dev

# 或启动生产服务器
npm run start
```

4. **访问应用**
- 开发模式：http://localhost:5173
- 生产模式：http://localhost:3000

## 使用指南

### 1. 管理主持人配置
1. 点击"主持人配置"按钮进入主持人管理页面
2. 点击"添加主持人"创建新主持人
3. 填写主持人名称和角色描述（角色描述将作为系统提示的一部分）
4. 支持编辑和删除已有主持人配置

### 2. 创建调研模板
1. 点击"调研配置"按钮
2. **配置变量**（可选）：
   - 添加变量定义，例如：key 为 `product_name`，value 为 `元气森林`
   - 在后续配置中使用 `{{product_name}}` 引用该变量
3. **基本信息配置**：
   - 填写调研主题（最多50字符）
   - 编写系统提示（最多500字符），可使用变量引用如 `{{product_name}}`
   - 添加背景知识（最多500字符），将自动拼接到系统提示后
   - 选择主持人（可选），主持人角色信息将自动追加到系统提示
   - 设置最大轮数，控制每个步骤最多对话轮数
4. **配置开场白和结束语**：
   - 设置欢迎消息（最多50字符）
   - 设置结束消息（最多50字符）
5. **配置调研步骤**：
   - 添加步骤内容（最多500字符），可使用变量引用
   - 选择步骤类型：
     - **顺序跳转**：按顺序执行下一步骤
     - **条件跳转**：根据条件判断跳转
       - 输入跳转条件（支持变量引用，如 `{{变量key}}`）
       - 设置条件为"是"时跳转到哪个步骤（或结束流程）
       - 设置条件为"否"时跳转到哪个步骤（或结束流程）
6. 保存模板

<img src="images/config.png" alt="Alt text" width="600" height="500">
<img src="images/config2.png" alt="Alt text" width="600" height="500">

### 3. 开始调研对话
1. 选择已创建的调研模板
2. 点击"开始调研"
3. 与 AI 调研员进行自然对话
4. 系统会根据预设步骤引导调研
   - 如果步骤配置为顺序跳转，将按顺序执行
   - 如果步骤配置为条件跳转，系统会根据对话内容判断条件是否满足，自动跳转到对应步骤

<img src="images/chat.png" alt="Alt text" width="600" height="500">

### 4. 管理调研数据
- **对话历史自动保存**：所有聊天记录实时保存到 MySQL 数据库
- **支持多轮对话和状态恢复**：使用 LangGraph 检查点机制保存对话状态
- **智能记忆管理**：确保重要信息不丢失
- **聊天记录查询**：
  - 支持查看所有会话列表
  - 支持按会话ID查询详细信息
  - 消息按时间顺序存储和查询
- **数据库存储**：
  - 会话记录存储在 `ai_conversations` 表
  - 消息记录存储在 `ai_chat_messages` 表
  - 支持消息类型：HumanMessage、AIMessage、SystemMessage

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request 来改进项目。

## 联系方式

如有问题或建议，请通过 GitHub Issues 联系我们。
