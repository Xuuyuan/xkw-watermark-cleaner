import { useState } from 'react';
import type { UploadedFile } from './types';
import { Sidebar } from './components/Sidebar';
import { HomePage } from './components/HomePage';
import { SettingsPage } from './components/SettingsPage';
import { AboutPage } from './components/AboutPage';

type Page = 'home' | 'settings' | 'about';

export default function App() {
  const [page, setPage] = useState<Page>('home');
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [statusText, setStatusText] = useState('就绪');

  return (
    <div className="app">
      <header className="app-header">
        <h1>学科网水印清理工具</h1>
        <span className="subtitle">支持 DOC / DOCX / PDF 水印清理</span>
        <span className="version">v3.0 在线版</span>
      </header>

      <div className="app-body">
        <Sidebar current={page} onNavigate={setPage} />

        <main className="main-content">
          {page === 'home' && <HomePage files={files} setFiles={setFiles} />}
          {page === 'settings' && <SettingsPage />}
          {page === 'about' && <AboutPage />}
        </main>
      </div>

      <footer className="status-bar">
        <span>{statusText}</span>
      </footer>
    </div>
  );
}
