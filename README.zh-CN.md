# Azure Diagram MCP Server

[English](./README.md) | 中文

> 使用 Python diagrams DSL 生成专业架构图的 MCP 服务器

## 特性

| 特性 | 描述 |
|------|------|
| 🏗️ Azure-First | 100+ Azure 服务图标 |
| ☁️ Multi-Cloud | AWS, GCP, Kubernetes, 自定义图标支持 |
| 🎨 多种类型 | 架构图、流程图、类图、K8s、自定义图表 |
| 🔒 安全扫描 | AST + Bandit 代码分析 |
| 📱 MCP Apps Viewer | 交互式图表查看器 |

## 快速开始

### 安装

```bash
# 安装依赖
uv sync

# 验证安装
dot -V
```

### 启动服务器

```bash
uvx microsoft.azure-diagram-mcp-server
```

## 环境变量

| 变量 | 描述 | 默认值 |
|------|------|--------|
| `DIAGRAM_COPILOT_PROVIDER_TYPE` | Provider: `openai`, `azure` | `openai` |
| `DIAGRAM_COPILOT_BASE_URL` | API 端点 | - |
| `DIAGRAM_COPILOT_API_KEY` | API Key | - |
| `DIAGRAM_COPILOT_MODEL` | 模型 | `gpt-4` |

## 使用

### MCP Clients

```python
from diagrams import Diagram
from diagrams.azure.compute import AKS
from diagrams.azure.database import SQLDatabase

with Diagram("Azure Web App"):
    AKS() >> SQLDatabase()
```

## 许可证

MIT License
