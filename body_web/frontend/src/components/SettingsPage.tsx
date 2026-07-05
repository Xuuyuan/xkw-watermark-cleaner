import { useState, useEffect, useCallback, Fragment } from 'react';
import type { AppConfig } from '../types';
import { getConfig, saveConfig } from '../api';

export function SettingsPage() {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    getConfig().then(setConfig).catch((err) => {
      setMessage(`加载配置失败: ${err.message}`);
    });
  }, []);

  const handleSave = useCallback(async () => {
    if (!config) return;
    setSaving(true);
    try {
      await saveConfig(config);
      setMessage('设置已保存！');
    } catch (err: any) {
      setMessage(`保存失败: ${err.message}`);
    }
    setSaving(false);
  }, [config]);

  if (!config) {
    return <div className="settings-page"><p>加载中...</p></div>;
  }

  return (
    <div className="settings-page">
      <h2>设置</h2>

      {/* 水印关键词 */}
      <div className="settings-group">
        <h3>水印关键词</h3>
        <p className="desc">每行一个关键词，匹配到即清除。修改后点击保存生效。</p>
        <textarea
          rows={5}
          value={config.metadata_keywords.join('\n')}
          onChange={(e) => setConfig({
            ...config,
            metadata_keywords: e.target.value.split('\n').filter((s) => s.trim()),
          })}
        />
      </div>

      {/* 页眉处理 */}
      <div className="settings-group">
        <h3>页眉处理</h3>
        <label>
          <input
            type="checkbox"
            checked={config.remove_all_header_content}
            onChange={(e) => setConfig({ ...config, remove_all_header_content: e.target.checked })}
          />
          删除页眉全部内容（不限于关键词匹配）
        </label>
      </div>

      {/* DOCX 文档属性 */}
      <div className="settings-group">
        <h3>DOCX 文档属性覆盖</h3>
        <label>
          <input
            type="checkbox"
            checked={config.docx_core_properties.override_enabled}
            onChange={(e) => setConfig({
              ...config,
              docx_core_properties: {
                ...config.docx_core_properties,
                override_enabled: e.target.checked,
              },
            })}
          />
          启用属性覆盖
        </label>
        <div className="settings-grid" style={{ marginTop: 10 }}>
          {([
            ['author', '作者'],
            ['title', '标题'],
            ['subject', '主题'],
            ['keywords', '关键词'],
            ['comments', '备注'],
          ] as const).map(([key, label]) => (
            <Fragment key={key}>
              <label>{label}：</label>
              <input
                type="text"
                value={config.docx_core_properties.values[key] || ''}
                onChange={(e) => setConfig({
                  ...config,
                  docx_core_properties: {
                    ...config.docx_core_properties,
                    values: { ...config.docx_core_properties.values, [key]: e.target.value },
                  },
                })}
              />
            </Fragment>
          ))}
        </div>
      </div>

      {/* PDF 元数据 */}
      <div className="settings-group">
        <h3>PDF 元数据覆盖</h3>
        <label>
          <input
            type="checkbox"
            checked={config.pdf_metadata.override_enabled}
            onChange={(e) => setConfig({
              ...config,
              pdf_metadata: {
                ...config.pdf_metadata,
                override_enabled: e.target.checked,
              },
            })}
          />
          启用元数据覆盖
        </label>
        <div className="settings-grid" style={{ marginTop: 10 }}>
          {([
            ['title', '标题'],
            ['author', '作者'],
            ['subject', '主题'],
            ['keywords', '关键词'],
            ['creator', '创建者'],
            ['producer', '生成器'],
          ] as const).map(([key, label]) => (
            <Fragment key={key}>
              <label>{label}：</label>
              <input
                type="text"
                value={config.pdf_metadata.values[key] || ''}
                onChange={(e) => setConfig({
                  ...config,
                  pdf_metadata: {
                    ...config.pdf_metadata,
                    values: { ...config.pdf_metadata.values, [key]: e.target.value },
                  },
                })}
              />
            </Fragment>
          ))}
        </div>
      </div>

      <button
        className="btn btn-primary"
        onClick={handleSave}
        disabled={saving}
        style={{ marginTop: 8 }}
      >
        {saving ? '保存中...' : '保存设置'}
      </button>

      {message && (
        <p style={{ marginTop: 8, fontSize: 12, color: message.includes('失败') ? 'var(--error)' : 'var(--success)' }}>
          {message}
        </p>
      )}
    </div>
  );
}
