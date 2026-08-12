# 🤝 贡献指南

感谢你对 AI Panel Studio 的关注！我们欢迎各种形式的贡献。

## 行为准则

请以尊重和专业的态度参与项目讨论。我们致力于建设一个友好、包容的开源社区。

## 如何贡献

### 报告 Bug

1. 在 GitHub Issues 中搜索，确认 Bug 未被报告过
2. 使用 Bug Report 模板创建新 Issue
3. 清晰描述：
   - 预期行为 vs 实际行为
   - 复现步骤
   - 运行环境（OS、Python 版本、浏览器版本）
   - 相关的截图或日志

### 提交功能请求

1. 在 Issues 中搜索，确认未被提议过
2. 创建 Feature Request，说明：
   - 功能的使用场景
   - 期望的交互方式
   - 优先级建议

### 提交 Pull Request

#### 开发流程

```bash
# 1. Fork 本仓库并 Clone 到本地
git clone https://github.com/<your-username>/ai-panel-studio.git
cd ai-panel-studio

# 2. 添加上游仓库
git remote add upstream https://github.com/<org>/ai-panel-studio.git

# 3. 创建功能分支
git checkout -b feat/your-feature-name

# 4. 开发 + 测试
cd backend
pip install -r requirements.txt
pytest tests/ -v          # 确保现有测试通过
# ... 编写代码和新测试 ...

# 5. 提交 (遵循 Conventional Commits)
git commit -m "feat: add feature description"
```

#### Commit 格式

本项目遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

| 前缀 | 用途 | 示例 |
|------|------|------|
| `feat:` | 新功能 | `feat: add discussion export feature` |
| `fix:` | Bug 修复 | `fix: handle SSE timeout gracefully` |
| `docs:` | 文档更新 | `docs: update API reference` |
| `test:` | 测试 | `test: add API route integration tests` |
| `refactor:` | 重构 | `refactor: extract discussion context builder` |
| `chore:` | 杂项 | `chore: update dependencies` |
| `style:` | 代码风格 | `style: format with black` |

#### 代码规范

**Python (后端)：**
- 遵循 PEP 8
- 使用 type hints
- 新增功能需包含测试
- 测试覆盖率不降低

**TypeScript/React (前端)：**
- 遵循项目 ESLint 配置
- 使用 TypeScript strict mode
- 组件使用函数式 + Hooks
- 样式使用 Tailwind CSS 类名

#### PR 检查清单

提交 PR 前请确认：

- [ ] 代码通过所有现有测试 (`pytest tests/ -v`)
- [ ] 新功能包含测试
- [ ] 类型检查通过 (`npx tsc --noEmit`)
- [ ] 前端构建通过 (`npm run build`)
- [ ] 文档已更新（如适用）
- [ ] Commit 信息遵循 Conventional Commits
- [ ] 分支已 rebase 到最新的 main

### 本地开发环境

#### 后端设置

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov  # 测试依赖
cp .env.example .env
# 编辑 .env，配置 DEEPSEEK_API_KEY (或留空使用 Mock 模式)
```

#### 前端设置

```bash
cd frontend
npm install
npm run dev  # 启动开发服务器 (http://localhost:5173)
```

#### 运行测试

```bash
# 后端单元测试
cd backend && pytest tests/ -v

# 覆盖率
pytest tests/ --cov=app.services --cov-report=term

# 前端类型检查
cd frontend && npx tsc --noEmit

# 前端构建
npm run build
```

## 项目结构速览

```
├── backend/          # Python FastAPI 后端
│   ├── app/routers/  # API 路由处理器
│   ├── app/services/ # 业务逻辑层
│   └── tests/        # 测试文件
├── frontend/         # React TypeScript 前端
│   └── src/
│       ├── pages/    # 页面组件
│       ├── components/ # 可复用 UI 组件
│       └── store/    # Zustand 状态管理
├── scripts/          # 工具脚本
└── docs/             # 项目文档
```

## 问题反馈

如有任何问题，欢迎通过 GitHub Issues 或 Discussions 联系。

---

**感谢你的贡献！** 🎉
