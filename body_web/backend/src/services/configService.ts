import { readFile, writeFile } from 'fs/promises';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import type { AppConfig } from '../types.js';

const __dirname = dirname(fileURLToPath(import.meta.url));

const DEFAULT_CONFIG: AppConfig = {
  remove_all_header_content: true,
  metadata_keywords: ['学科网', 'zxxk.com', 'zxxk', 'rbm.xkw.com', 'xkw'],
  docx_core_properties: {
    override_enabled: false,
    values: {
      author: 'User',
      comments: '',
      title: '清理后的文档',
      subject: '',
      keywords: '',
    },
  },
  pdf_metadata: {
    override_enabled: false,
    clear_xmp_metadata: 'if_keyword',
    values: {
      title: '',
      author: '',
      subject: '',
      keywords: '',
      creator: '-',
      producer: '-',
    },
  },
};

// config.json 放在 backend 根目录下
// 编译后从 dist/services/ 向上两级到 backend/
const CONFIG_PATH = join(__dirname, '..', '..', 'config.json');

export async function loadConfig(): Promise<AppConfig> {
  try {
    const data = await readFile(CONFIG_PATH, 'utf-8');
    return { ...DEFAULT_CONFIG, ...JSON.parse(data) };
  } catch {
    return { ...DEFAULT_CONFIG };
  }
}

export async function saveConfig(config: AppConfig): Promise<void> {
  await writeFile(CONFIG_PATH, JSON.stringify(config, null, 2), 'utf-8');
}
