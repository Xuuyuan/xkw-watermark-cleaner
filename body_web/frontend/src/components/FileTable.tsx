import type { UploadedFile } from '../types';
import { formatFileSize } from '../api';

interface FileTableProps {
  files: UploadedFile[];
  onToggle: (id: string) => void;
  onToggleAll: (checked: boolean) => void;
  onRemove: (id: string) => void;
  onClear: () => void;
}

const STATUS_TEXT: Record<string, string> = {
  pending: '待处理',
  processing: '处理中...',
  done: '已完成',
  failed: '失败',
};

export function FileTable({ files, onToggle, onToggleAll, onRemove, onClear }: FileTableProps) {
  const allChecked = files.length > 0 && files.every((f) => f.selected);

  if (files.length === 0) {
    return (
      <div className="file-table-wrapper">
        <div className="empty-list">暂无文件，请上传或拖放文件到上方区域</div>
      </div>
    );
  }

  return (
    <div className="file-table-wrapper">
      <table className="file-table">
        <thead>
          <tr>
            <th className="checkbox">
              <input
                type="checkbox"
                checked={allChecked}
                onChange={(e) => onToggleAll(e.target.checked)}
              />
            </th>
            <th>文件名</th>
            <th className="type">类型</th>
            <th className="size">大小</th>
            <th className="status">状态</th>
            <th style={{ width: 50 }}>操作</th>
          </tr>
        </thead>
        <tbody>
          {files.map((file) => (
            <tr key={file.id}>
              <td className="checkbox">
                <input
                  type="checkbox"
                  checked={file.selected || false}
                  onChange={() => onToggle(file.id)}
                />
              </td>
              <td className="name" title={file.name}>{file.name}</td>
              <td className="type">{file.type}</td>
              <td className="size">{formatFileSize(file.size)}</td>
              <td className={`status status-${file.status}`}>
                {STATUS_TEXT[file.status] || file.status}
              </td>
              <td>
                <button
                  className="btn-link"
                  style={{ color: 'var(--error)', fontSize: 11 }}
                  onClick={() => onRemove(file.id)}
                >
                  删除
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
