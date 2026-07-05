import { Router, Response } from 'express';
import multer from 'multer';
import { addFile, getFile, getAllFiles, updateFile, removeFile, clearAllFiles, getOutputDir } from '../services/fileStore.js';
import { loadConfig } from '../services/configService.js';
import { cleanDocx } from '../services/docxCleaner.js';
import { cleanPdf } from '../services/pdfCleaner.js';
import { join, extname } from 'path';
import type { ProcessOptions } from '../types.js';

const router = Router();

// multer 配置：内存存储
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 100 * 1024 * 1024 }, // 100MB
});

// ─── 上传文件 ─────────────────────────────────────────

router.post('/upload', upload.array('files', 50), async (req, res: Response) => {
  try {
    if (!req.files || !Array.isArray(req.files) || req.files.length === 0) {
      return res.status(400).json({ error: '未检测到上传文件' });
    }

    const files = [];
    for (const file of req.files) {
      const uploaded = await addFile(file.originalname, file.buffer);
      files.push({
        id: uploaded.id,
        name: uploaded.originalName,
        size: uploaded.size,
        type: uploaded.type,
        status: uploaded.status,
      });
    }

    res.json({ files });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// ─── 获取文件列表 ─────────────────────────────────────

router.get('/files', (_req, res: Response) => {
  const files = getAllFiles().map((f) => ({
    id: f.id,
    name: f.originalName,
    size: f.size,
    type: f.type,
    status: f.status,
    outputName: f.outputName,
    error: f.error,
  }));
  res.json({ files });
});

// ─── 删除文件 ─────────────────────────────────────────

router.delete('/files/:id', (req, res: Response) => {
  removeFile(req.params.id);
  res.json({ ok: true });
});

// ─── 清空所有文件 ─────────────────────────────────────

router.delete('/files', (_req, res: Response) => {
  clearAllFiles();
  res.json({ ok: true });
});

// ─── 处理文件（SSE 流式响应） ──────────────────────────

router.post('/process', async (req, res: Response) => {
  const { fileIds, options } = req.body as {
    fileIds: string[];
    options: ProcessOptions;
  };

  if (!fileIds || fileIds.length === 0) {
    return res.status(400).json({ error: '未选择文件' });
  }

  // 设置 SSE
  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    Connection: 'keep-alive',
    'Access-Control-Allow-Origin': '*',
  });

  const sendEvent = (data: any) => {
    res.write(`data: ${JSON.stringify(data)}\n\n`);
  };

  const config = await loadConfig();
  const outputDir = getOutputDir();

  let success = 0;
  let fail = 0;
  const total = fileIds.length;

  for (let i = 0; i < fileIds.length; i++) {
    const fileId = fileIds[i];
    const file = getFile(fileId);

    if (!file) {
      fail++;
      sendEvent({
        type: 'log',
        message: `文件不存在: ${fileId}`,
        level: 'error',
      });
      sendEvent({
        type: 'progress',
        current: i + 1,
        total,
      });
      continue;
    }

    // 更新状态
    updateFile(fileId, { status: 'processing' });
    sendEvent({
      type: 'file-status',
      fileId,
      fileName: file.originalName,
      status: 'processing',
    });
    sendEvent({
      type: 'log',
      message: `开始处理: ${file.originalName}`,
      level: 'info',
    });
    sendEvent({
      type: 'progress',
      current: i,
      total,
    });

    try {
      // 构造输出路径
      const ext = extname(file.originalName);
      const baseName = file.originalName.replace(ext, '');
      const outputName = options.overwrite
        ? file.originalName
        : `${baseName}(cleaned)${ext}`;
      const outputPath = join(outputDir, `${file.id}_${outputName}`);

      let logs: string[] = [];

      if (file.type === 'docx') {
        logs = await cleanDocx(file.path, outputPath, config, options.removeAllHeader);
      } else if (file.type === 'pdf') {
        logs = await cleanPdf(file.path, outputPath, config, options.removeAllHeader);
      } else if (file.type === 'doc') {
        throw new Error('暂不支持 DOC 格式，请先转换为 DOCX');
      } else {
        throw new Error(`不支持的文件类型: ${file.originalName}`);
      }

      // 发送日志
      for (const log of logs) {
        sendEvent({ type: 'log', message: log, level: 'success' });
      }

      // 更新文件状态
      updateFile(fileId, {
        status: 'done',
        outputName,
        outputPath,
      });

      sendEvent({
        type: 'file-status',
        fileId,
        fileName: file.originalName,
        status: 'done',
      });
      sendEvent({
        type: 'log',
        message: `处理完成: ${outputName}`,
        level: 'success',
      });
      success++;
    } catch (err: any) {
      updateFile(fileId, { status: 'failed', error: err.message });
      sendEvent({
        type: 'file-status',
        fileId,
        fileName: file.originalName,
        status: 'failed',
      });
      sendEvent({
        type: 'log',
        message: `处理失败: ${file.originalName}\n原因: ${err.message}`,
        level: 'error',
      });
      fail++;
    }

    sendEvent({
      type: 'progress',
      current: i + 1,
      total,
    });
  }

  sendEvent({
    type: 'done',
    success,
    fail,
  });

  res.end();
});

// ─── 下载文件 ─────────────────────────────────────────

router.get('/download/:id', (req, res: Response) => {
  const file = getFile(req.params.id);
  if (!file || !file.outputPath) {
    return res.status(404).json({ error: '文件不存在或未处理' });
  }
  res.download(file.outputPath, file.outputName || file.originalName);
});

export default router;
