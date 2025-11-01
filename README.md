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

## 项目结构

```
SurveyEase/
├── se-backend/                 # 后端服务
│   ├── api/                   # API 接口层
│   │   ├── host.py           # 主持人管理 API
│   │   ├── survey.py         # 调研对话 API
│   │   └── template.py       # 模板管理 API
│   ├── cfg/                  # 配置管理
│   │   └── setting.py        # 应用配置
│   ├── constants/            # 常量定义
│   ├── graph/                # 对话图管理
│   │   └── survey_graph.py   # 调研对话流程
│   ├── llm_provider/         # LLM 提供商
│   ├── memory/               # 记忆管理
│   │   └── embeddings.py     # 向量嵌入
│   ├── services/             # 服务层
│   │   └── service_manager.py # 服务管理器
│   ├── template/             # 模板配置
│   │   ├── host_config.json  # 主持人配置
│   │   └── survey_template.json  # 调研模板
│   ├── utils/                # 工具类
│   │   ├── custom_serializer.py
│   │   ├── json_utils.py
│   │   └── unified_logger.py
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

### 5. 主持人管理系统
- **主持人管理**：支持创建、编辑、删除主持人配置
- **角色定义**：为每个主持人定义独特的角色和性格
- **自动集成**：选择主持人后，角色信息自动追加到系统提示中
<img src="images/hosts.png" alt="Alt text" width="600" height="500">

### 6. 变量与高亮系统
- **变量定义**：在模板中定义可复用变量
- **变量引用**：在主题、系统提示、步骤内容中使用 `{{变量key}}` 格式引用
- **实时高亮**：输入框实时高亮显示变量引用，提升编辑体验
- **字符计数**：所有输入字段显示字符计数，便于控制内容长度

## 安装和启动

### 环境要求
- Python 3.11+
- Node.js 18+
- 支持的 LLM 提供商：Azure OpenAI、阿里云百炼

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
创建 `.env` 文件：
```env
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

# 聊天记录保存路径配置
CHAT_LOG_PATH=logs/chat_logs
```

4. **启动后端服务**
```bash
# 使用 uvicorn 启动
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 或使用 Python 直接启动
python main.py
```

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

### 1. 管理主持人配置（可选）
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
- 对话历史自动保存
- 支持多轮对话和状态恢复
- 智能记忆管理确保重要信息不丢失
- 聊天记录持久化：每个调研会话结束后自动保存到指定路径
- 文件命名格式：`chat_{conversation_id}_{yyyymmddHHmmss}.json`

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request 来改进项目。

## 联系方式

如有问题或建议，请通过 GitHub Issues 联系我们。
