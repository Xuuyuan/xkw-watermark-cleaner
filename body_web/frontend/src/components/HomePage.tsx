import { useState, useCallback, useRef } from 'react';
import type { UploadedFile, ProcessOptions, LogEntry } from '../types';
import { processFiles, deleteFile, getDownloadUrl, formatTime } from '../api';
import { DropZone } from './DropZone';
import { FileTable } from './FileTable';
import { LogPanel } from './LogPanel';

interface HomePageProps {
  files: UploadedFile[];
  setFiles: React.Dispatch<React.SetStateAction<UploadedFile[]>>;
}

export function HomePage({ files, setFiles }: HomePageProps) {
  const [overwrite, setOverwrite] = useState(true);
  const [removeAllHeader, setRemoveAllHeader] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState({ current: 0, total: 0 });
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [statusText, setStatusText] = useState('就绪');
  const abortRef = useRef(false);

  const addLog = useCallback((message: string, level: LogEntry['level'] = 'info') => {
    setLogs((prev) => [...prev, { timestamp: formatTime(), message, level }]);
  }, []);

  const handleFilesAdded = useCallback((uploaded: UploadedFile[]) => {
    setFiles((prev) => [...prev, ...uploaded.map((f) => ({ ...f, selected: true }))]);
  }, [setFiles]);

  const handleToggle = useCallback((id: string) => {
    setFiles((prev) => prev.map((f) => f.id === id ? { ...f, selected: !f.selected } : f));
  }, [setFiles]);

  const handleToggleAll = useCallback((checked: boolean) => {
    setFiles((prev) => prev.map((f) => ({ ...f, selected: checked })));
  }, [setFiles]);

  const handleRemove = useCallback(async (id: string) => {
    await deleteFile(id);
    setFiles((prev) => prev.filter((f) => f.id !== id));
  }, [setFiles]);

  const handleClear = useCallback(() => {
    setFiles([]);
    setStatusText('列表已清空');
  }, [setFiles]);

  const handleClearLog = useCallback(() => {
    setLogs([]);
  }, []);

  const handleProcess = useCallback(async () => {
    const selected = files.filter((f) => f.selected);
    if (selected.length === 0) {
      addLog('请先勾选要处理的文件', 'warn');
      return;
    }

    setIsProcessing(true);
    abortRef.current = false;
    setProgress({ current: 0, total: selected.length });
    setStatusText(`正在处理...（共 ${selected.length} 项）`);
    addLog(`开始批量处理，共 ${selected.length} 个文件`, 'info');

    const options: ProcessOptions = { overwrite, removeAllHeader };

    try {
      await processFiles(
        selected.map((f) => f.id),
        options,
        {
          onProgress: (current, total) => {
            setProgress({ current, total });
          },
          onLog: (message, level) => {
            addLog(message, level);
          },
          onFileStatus: (fileId, _fileName, status) => {
            setFiles((prev) => prev.map((f) =>
              f.id === fileId ? { ...f, status: status as any } : f
            ));
          },
          onDone: (success, fail) => {
            addLog(`\n全部处理完成！成功 ${success}，失败 ${fail}`,
              fail === 0 ? 'success' : 'warn');
            setStatusText(`处理完成：成功 ${success}，失败 ${fail}`);
          },
        }
      );
    } catch (err: any) {
      addLog(`处理出错: ${err.message}`, 'error');
      setStatusText('处理出错');
    } finally {
      setIsProcessing(false);
    }
  }, [files, overwrite, removeAllHeader, addLog, setFiles]);

  const handleCancel = useCallback(() => {
    abortRef.current = true;
    addLog('用户取消了处理', 'warn');
    setIsProcessing(false);
    setStatusText('已取消');
  }, [addLog]);

  const handleDownload = useCallback((file: UploadedFile) => {
    if (file.status === 'done') {
      window.open(getDownloadUrl(file.id), '_blank');
    }
  }, []);

  const doneFiles = files.filter((f) => f.status === 'done');

  return (
    <>
      <DropZone onFilesAdded={handleFilesAdded} onLog={addLog} />

      <div className="options-row">
        <label>
          <input type="checkbox" checked={overwrite} onChange={(e) => setOverwrite(e.target.checked)} />
          覆盖源文件（不生成 (cleaned) 副本）
        </label>
        <label>
          <input type="checkbox" checked={removeAllHeader} onChange={(e) => setRemoveAllHeader(e.target.checked)} />
          删除页眉全部内容
        </label>
      </div>

      <div className="list-header">
        <span className="title">文件列表（共 {files.length} 个）</span>
        <div className="actions">
          {doneFiles.length > 0 && (
            <button
              className="btn-link"
              onClick={() => doneFiles.forEach(handleDownload)}
              style={{ marginRight: 8 }}
            >
              下载全部已处理
            </button>
          )}
          <button className="btn-link" onClick={handleClear}>清空列表</button>
        </div>
      </div>

      <FileTable
        files={files}
        onToggle={handleToggle}
        onToggleAll={handleToggleAll}
        onRemove={handleRemove}
        onClear={handleClear}
      />

      <div className="action-row">
        <button
          className="btn btn-primary"
          onClick={handleProcess}
          disabled={isProcessing}
        >
          {isProcessing ? '处理中...' : '▶ 开始处理'}
        </button>
        {isProcessing && (
          <button className="btn-cancel" onClick={handleCancel}>取消</button>
        )}
        {isProcessing && (
          <>
            <div className="progress-bar">
              <div
                className="fill"
                style={{ width: `${progress.total > 0 ? (progress.current / progress.total) * 100 : 0}%` }}
              />
            </div>
            <span className="progress-label">{progress.current}/{progress.total}</span>
          </>
        )}
        <div style={{ marginLeft: 'auto' }}>
          {doneFiles.length > 0 && (
            <span style={{ fontSize: 11, color: 'var(--success)' }}>
              {doneFiles.length} 个文件可下载
            </span>
          )}
        </div>
      </div>

      <LogPanel logs={logs} onClear={handleClearLog} />
    </>
  );
}
