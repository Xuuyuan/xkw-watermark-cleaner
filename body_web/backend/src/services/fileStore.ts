import { createHash } from 'crypto';
import { readFile, writeFile, mkdir, readdir, unlink, stat } from 'fs/promises';
import { join, extname } from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';
import type { UploadFile, FileType, FileStatus } from '../types.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const UPLOAD_DIR = join(__dirname, '..', '..', 'uploads');
const OUTPUT_DIR = join(__dirname, '..', '..', 'outputs');

// 确保目录存在
await mkdir(UPLOAD_DIR, { recursive: true });
await mkdir(OUTPUT_DIR, { recursive: true });

// 内存存储（无数据库）
const files = new Map<string, UploadFile>();

export function getFileType(filename: string): FileType {
  const ext = extname(filename).toLowerCase();
  if (ext === '.docx') return 'docx';
  if (ext === '.pdf') return 'pdf';
  if (ext === '.doc') return 'doc';
  return 'unknown';
}

export function getUploadDir(): string {
  return UPLOAD_DIR;
}

export function getOutputDir(): string {
  return OUTPUT_DIR;
}

export async function addFile(originalName: string, buffer: Buffer): Promise<UploadFile> {
  const id = createHash('md5').update(originalName + Date.now()).digest('hex').slice(0, 12);
  const ext = extname(originalName);
  const storedName = `${id}${ext}`;
  const filePath = join(UPLOAD_DIR, storedName);

  await writeFile(filePath, buffer);

  const file: UploadFile = {
    id,
    originalName,
    storedName,
    path: filePath,
    size: buffer.length,
    type: getFileType(originalName),
    status: 'pending',
    createdAt: Date.now(),
  };

  files.set(id, file);
  return file;
}

export function getFile(id: string): UploadFile | undefined {
  return files.get(id);
}

export function getAllFiles(): UploadFile[] {
  return Array.from(files.values()).sort((a, b) => a.createdAt - b.createdAt);
}

export function updateFile(id: string, updates: Partial<UploadFile>): void {
  const file = files.get(id);
  if (file) {
    Object.assign(file, updates);
  }
}

export function removeFile(id: string): void {
  const file = files.get(id);
  if (file) {
    // 删除物理文件
    unlink(file.path).catch(() => {});
    if (file.outputPath) {
      unlink(file.outputPath).catch(() => {});
    }
    files.delete(id);
  }
}

export function clearAllFiles(): void {
  for (const [id] of files) {
    removeFile(id);
  }
}

/** 清理超过 1 小时的文件 */
export async function cleanupOldFiles(): Promise<void> {
  const now = Date.now();
  const ONE_HOUR = 60 * 60 * 1000;

  for (const [id, file] of files) {
    if (now - file.createdAt > ONE_HOUR) {
      removeFile(id);
    }
  }

  // 清理 uploads 目录中的孤儿文件
  try {
    const entries = await readdir(UPLOAD_DIR);
    for (const entry of entries) {
      const filePath = join(UPLOAD_DIR, entry);
      const s = await stat(filePath);
      if (now - s.mtimeMs > ONE_HOUR) {
        await unlink(filePath).catch(() => {});
      }
    }
  } catch {}
}
