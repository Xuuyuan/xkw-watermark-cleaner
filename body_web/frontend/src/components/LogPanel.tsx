import type { LogEntry } from '../types';
import { formatTime } from '../api';

interface LogPanelProps {
  logs: LogEntry[];
  onClear: () => void;
}

export function LogPanel({ logs, onClear }: LogPanelProps) {
  return (
    <>
      <div className="log-header">
        <span className="title">处理日志</span>
        <div className="actions">
          <button className="btn-link" onClick={onClear}>清空日志</button>
        </div>
      </div>
      <div className="log-panel">
        {logs.length === 0 ? (
          <div style={{ color: 'var(--text-hint)' }}>等待操作...</div>
        ) : (
          logs.map((log, i) => (
            <div key={i} className={`log-line log-${log.level}`}>
              [{log.timestamp}] {log.message}
            </div>
          ))
        )}
      </div>
    </>
  );
}
