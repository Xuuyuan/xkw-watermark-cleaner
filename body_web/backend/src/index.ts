import express from 'express';
import cors from 'cors';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { existsSync } from 'fs';
import filesRouter from './routes/files.js';
import configRouter from './routes/config.js';
import { cleanupOldFiles } from './services/fileStore.js';

const __dirname = dirname(fileURLToPath(import.meta.url));

const app = express();
const PORT = process.env.PORT || 3001;

// ─── 中间件 ───────────────────────────────────────────
app.use(cors());
app.use(express.json());

// ─── 静态文件（前端构建产物） ──────────────────────────
const frontendDist = join(__dirname, '..', '..', 'frontend', 'dist');
if (existsSync(frontendDist)) {
  app.use(express.static(frontendDist));
}

// ─── API 路由 ─────────────────────────────────────────
app.use('/api/files', filesRouter);
app.use('/api/config', configRouter);

// ─── 健康检查 ─────────────────────────────────────────
app.get('/api/health', (_req, res) => {
  res.json({ status: 'ok', timestamp: Date.now() });
});

// ─── 前端路由兜底（SPA） ───────────────────────────────
if (existsSync(frontendDist)) {
  app.get('*', (_req, res) => {
    res.sendFile(join(frontendDist, 'index.html'));
  });
}

// ─── 启动 ─────────────────────────────────────────────
app.listen(PORT, () => {
  console.log(`\n  ╔══════════════════════════════════════════╗`);
  console.log(`  ║  学科网水印清理工具 - 后端服务           ║`);
  console.log(`  ║  http://localhost:${PORT}                    ║`);
  console.log(`  ╚══════════════════════════════════════════╝\n`);

  // 定时清理过期文件
  setInterval(cleanupOldFiles, 30 * 60 * 1000);
});
