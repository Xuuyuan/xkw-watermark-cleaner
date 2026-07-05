import { Router } from 'express';
import { Response } from 'express';
import { loadConfig, saveConfig } from '../services/configService.js';
import type { AppConfig } from '../types.js';

const router = Router();

// 获取配置
router.get('/', async (_req, res: Response) => {
  const config = await loadConfig();
  res.json(config);
});

// 更新配置
router.put('/', async (req, res: Response) => {
  try {
    const config = req.body as AppConfig;
    await saveConfig(config);
    res.json({ ok: true });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

export default router;
