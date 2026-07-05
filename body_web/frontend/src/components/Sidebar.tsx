interface SidebarProps {
  current: string;
  onNavigate: (page: 'home' | 'settings' | 'about') => void;
}

const NAV_ITEMS = [
  { key: 'home', label: '🏠 首页' },
  { key: 'settings', label: '⚙ 设置' },
  { key: 'about', label: 'ℹ 关于' },
] as const;

export function Sidebar({ current, onNavigate }: SidebarProps) {
  return (
    <div className="sidebar">
      {NAV_ITEMS.map((item) => (
        <button
          key={item.key}
          className={`nav-btn ${current === item.key ? 'active' : ''}`}
          onClick={() => onNavigate(item.key)}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
