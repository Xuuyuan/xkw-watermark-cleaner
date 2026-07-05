export type FileType = 'docx' | 'pdf' | 'doc' | 'unknown';
export type FileStatus = 'pending' | 'processing' | 'done' | 'failed';

export interface UploadedFile {
  id: string;
  name: string;
  size: number;
  type: FileType;
  status: FileStatus;
  outputName?: string;
  error?: string;
  selected?: boolean;
}

export interface ProcessOptions {
  overwrite: boolean;
  removeAllHeader: boolean;
}

export interface LogEntry {
  timestamp: string;
  message: string;
  level: 'info' | 'success' | 'warn' | 'error';
}

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
