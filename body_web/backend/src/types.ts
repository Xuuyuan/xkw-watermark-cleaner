/** 文件状态 */
export type FileStatus = 'pending' | 'processing' | 'done' | 'failed';

/** 支持的文件类型 */
export type FileType = 'docx' | 'pdf' | 'doc' | 'unknown';

/** 上传文件元数据 */
export interface UploadFile {
  id: string;
  originalName: string;
  storedName: string;
  path: string;
  size: number;
  type: FileType;
  status: FileStatus;
  outputName?: string;
  outputPath?: string;
  error?: string;
  createdAt: number;
}

/** 处理选项 */
export interface ProcessOptions {
  overwrite: boolean;
  removeAllHeader: boolean;
}

/** 日志条目 */
export interface LogEntry {
  timestamp: string;
  message: string;
  level: 'info' | 'success' | 'warn' | 'error';
}

/** 处理进度事件 */
export interface ProgressEvent {
  type: 'progress' | 'log' | 'file-status' | 'done';
  current?: number;
  total?: number;
  fileId?: string;
  fileName?: string;
  status?: FileStatus;
  message?: string;
  level?: LogEntry['level'];
  success?: number;
  fail?: number;
}

/** 配置 */
export interface AppConfig {
  remove_all_header_content: boolean;
  metadata_keywords: string[];
  docx_core_properties: {
    override_enabled: boolean;
    values: {
      author?: string;
      comments?: string;
      title?: string;
      subject?: string;
      keywords?: string;
    };
  };
  pdf_metadata: {
    override_enabled: boolean;
    clear_xmp_metadata: 'never' | 'always' | 'if_keyword';
    values: {
      title?: string;
      author?: string;
      subject?: string;
      keywords?: string;
      creator?: string;
      producer?: string;
    };
  };
}
