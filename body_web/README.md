# 学科网水印清理工具 - 在线版 (Web)

基于 Vite + React + TypeScript + Express 构建，浏览器直接使用。

## 技术栈

- **前端**: React 18 + TypeScript + Vite
- **后端**: Express + TypeScript
- **PDF 处理**: pdf-lib
- **DOCX 处理**: adm-zip + @xmldom/xmldom + xpath
- **无数据库**: 文件存储在内存+临时目录，1小时后自动清理

## 目录结构

```
body_web/
  frontend/          # 前端 (React + Vite)
    src/
      components/     # 组件
      api/           # API 调用
      types/         # 类型定义
      styles/        # 样式
  backend/           # 后端 (Express + TS)
    src/
      routes/        # 路由
      services/      # 业务逻辑
      utils/         # 工具函数
  scripts/           # 构建脚本
```

## 开发

### 1. 安装依赖

```bash
cd body_web/frontend
npm install

cd ../backend
npm install
```

### 2. 启动开发服务器

前端和后端分别启动（两个终端）：

```bash
# 终端 1 - 前端 (端口 5173)
cd body_web/frontend
npm run dev

# 终端 2 - 后端 (端口 3001)
cd body_web/backend
npm run dev
```

访问 http://localhost:5173

或同时启动：

```bash
cd body_web
npm install
npm run dev
```

## 构建

```bash
cd body_web
npm run build
```

构建产物：
- 前端: `frontend/dist/`
- 后端: `backend/dist/`

## 部署

```bash
cd body_web/backend
npm start
```

访问 http://localhost:3001

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/files/upload | 上传文件 |
| GET | /api/files/files | 获取文件列表 |
| DELETE | /api/files/files/:id | 删除文件 |
| DELETE | /api/files/files | 清空所有文件 |
| POST | /api/files/process | 处理文件 (SSE) |
| GET | /api/files/download/:id | 下载文件 |
| GET | /api/config/ | 获取配置 |
| PUT | /api/config/ | 更新配置 |
| GET | /api/health | 健康检查 |
