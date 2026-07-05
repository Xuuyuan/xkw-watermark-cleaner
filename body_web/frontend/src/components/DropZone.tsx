import { useState, useCallback } from 'react';
import type { UploadedFile } from '../types';
import { uploadFiles } from '../api';

interface DropZoneProps {
  onFilesAdded: (files: UploadedFile[]) => void;
  onLog: (message: string, level: 'info' | 'success' | 'warn' | 'error') => void;
}

const SUPPORTED_EXTS = '.doc .docx .pdf';

export function DropZone({ onFilesAdded, onLog }: DropZoneProps) {
  const [dragover, setDragover] = useState(false);

  const handleFiles = useCallback(async (fileList: FileList | File[]) => {
    const files = Array.from(fileList).filter((f) => {
      const ext = '.' + (f.name.split('.').pop() || '').toLowerCase();
      return SUPPORTED_EXTS.includes(ext);
    });

    if (files.length === 0) {
      onLog('未检测到支持的文件格式（仅支持 .doc .docx .pdf）', 'warn');
      return;
    }

    try {
      const uploaded = await uploadFiles(files);
      onFilesAdded(uploaded);
      onLog(`已添加 ${uploaded.length} 个文件到列表`, 'info');
    } catch (err: any) {
      onLog(`上传失败: ${err.message}`, 'error');
    }
  }, [onFilesAdded, onLog]);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragover(false);
    handleFiles(e.dataTransfer.files);
  }, [handleFiles]);

  const onSelectClick = useCallback(() => {
    const input = document.createElement('input');
    input.type = 'file';
    input.multiple = true;
    input.accept = SUPPORTED_EXTS;
    input.onchange = () => {
      if (input.files) handleFiles(input.files);
    };
    input.click();
  }, [handleFiles]);

  return (
    <div
      className={`drop-zone ${dragover ? 'dragover' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setDragover(true); }}
      onDragLeave={() => setDragover(false)}
      onDrop={onDrop}
      onClick={onSelectClick}
    >
      <div className="icon">📂</div>
      <div className="text">将文件拖放到此处</div>
      <div className="hint">支持格式：{SUPPORTED_EXTS}</div>
      <div className="btn-row" onClick={(e) => e.stopPropagation()}>
        <button className="btn btn-secondary" onClick={onSelectClick}>
          选择文件
        </button>
      </div>
    </div>
  );
}
