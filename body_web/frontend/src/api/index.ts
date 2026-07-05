import type { UploadedFile, ProcessOptions, AppConfig, LogEntry } from '../types';

const API_BASE = '/api';

// ─── 文件上传 ─────────────────────────────────────────

export async function uploadFiles(files: File[]): Promise<UploadedFile[]> {
  const formData = new FormData();
  for (const file of files) {
    formData.append('files', file);
  }

  const res = await fetch(`${API_BASE}/files/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || '上传失败');
  }

  const data = await res.json();
  return data.files as UploadedFile[];
}

// ─── 获取文件列表 ─────────────────────────────────────

export async function getFiles(): Promise<UploadedFile[]> {
  const res = await fetch(`${API_BASE}/files/files`);
  if (!res.ok) throw new Error('获取文件列表失败');
  const data = await res.json();
  return data.files as UploadedFile[];
}

// ─── 删除文件 ─────────────────────────────────────────

export async function deleteFile(id: string): Promise<void> {
  await fetch(`${API_BASE}/files/files/${id}`, { method: 'DELETE' });
}

export async function clearAllFiles(): Promise<void> {
  await fetch(`${API_BASE}/files/files`, { method: 'DELETE' });
}

// ─── 处理文件（SSE 流式响应） ──────────────────────────

export interface ProcessCallbacks {
  onProgress?: (current: number, total: number) => void;
  onLog?: (message: string, level: LogEntry['level']) => void;
  onFileStatus?: (fileId: string, fileName: string, status: string) => void;
  onDone?: (success: number, fail: number) => void;
}

export async function processFiles(
  fileIds: string[],
  options: ProcessOptions,
  callbacks: ProcessCallbacks
): Promise<void> {
  const res = await fetch(`${API_BASE}/files/process`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fileIds, options }),
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || '处理失败');
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error('无法读取响应流');

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const event = JSON.parse(line.slice(6));
          switch (event.type) {
            case 'progress':
              callbacks.onProgress?.(event.current, event.total);
              break;
            case 'log':
              callbacks.onLog?.(event.message, event.level);
              break;
            case 'file-status':
              callbacks.onFileStatus?.(event.fileId, event.fileName, event.status);
              break;
            case 'done':
              callbacks.onDone?.(event.success, event.fail);
              break;
          }
        } catch {}
      }
    }
  }
}

// ─── 下载文件 ─────────────────────────────────────────

export function getDownloadUrl(id: string): string {
  return `${API_BASE}/files/download/${id}`;
}

// ─── 配置 ─────────────────────────────────────────────

export async function getConfig(): Promise<AppConfig> {
  const res = await fetch(`${API_BASE}/config/`);
  if (!res.ok) throw new Error('获取配置失败');
  return res.json();
}

export async function saveConfig(config: AppConfig): Promise<void> {
  const res = await fetch(`${API_BASE}/config/`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  if (!res.ok) throw new Error('保存配置失败');
}

// ─── 工具函数 ─────────────────────────────────────────

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function formatTime(): string {
  const now = new Date();
  return `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
}
