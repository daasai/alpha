import React, { useState } from 'react';
import { LayoutDashboard, Crosshair, Briefcase, FlaskConical, Settings, Zap, PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { PageView } from '../src/types/domain';

interface SidebarProps {
  activePage: PageView;
  onNavigate: (page: PageView) => void;
  onNewScan?: () => void;
  isOpen?: boolean;
}

const Sidebar: React.FC<SidebarProps> = ({ activePage, onNavigate, onNewScan, isOpen = false }) => {
  const [isCollapsed, setIsCollapsed] = useState(false);

  const menuItems: { id: PageView; label: string; icon: React.ReactNode }[] = [
    { id: 'dashboard', label: '驾驶舱 (Dashboard)', icon: <LayoutDashboard size={20} /> },
    { id: 'hunter', label: '猎场 (Hunter)', icon: <Crosshair size={20} /> },
    { id: 'portfolio', label: '模拟盘 (Portfolio)', icon: <Briefcase size={20} /> },
    { id: 'lab', label: '实验室 (Lab)', icon: <FlaskConical size={20} /> },
  ];

  return (
    <div 
      className={`
        fixed inset-y-0 left-0 z-50 bg-sidebar-bg text-gray-600 flex flex-col flex-shrink-0 border-r border-gray-200 
        transition-all duration-300 ease-in-out shadow-xl md:shadow-none
        md:relative md:translate-x-0
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        w-64 ${isCollapsed ? 'md:w-20' : 'md:w-64'}
      `}
    >
      {/* Header */}
      <div className={`p-6 flex transition-all duration-300 ${isCollapsed ? 'flex-col items-center gap-4' : 'flex-row items-center justify-between'}`}>
        {/* Logo & Identity */}
        <div className="flex items-center overflow-hidden">
          <div className="text-xl shrink-0 select-none">🛰️</div>
          <div className={`ml-2 whitespace-nowrap transition-all duration-300 ${isCollapsed ? 'w-0 opacity-0 hidden' : 'w-auto opacity-100 block'}`}>
            <h1 className="text-xl font-bold text-gray-900 leading-tight">DAAS Alpha</h1>
            <p className="text-[10px] text-gray-500 font-medium tracking-wider uppercase">v1.3 Pro</p>
          </div>
        </div>

        {/* Desktop Toggle Button */}
        <button
          type="button"
          onClick={() => setIsCollapsed(!isCollapsed)}
          className={`
            hidden md:flex items-center justify-center p-1.5 text-gray-400 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors
            ${isCollapsed ? 'w-full' : ''}
          `}
          title={isCollapsed ? "展开" : "折叠"}
        >
          {isCollapsed ? <PanelLeftOpen size={20} /> : <PanelLeftClose size={20} />}
        </button>
      </div>

      {/* Primary Action */}
      <div className="px-4 mb-8">
        <button 
          type="button"
          onClick={() => {
            if (onNewScan) {
              onNewScan();
            } else {
              onNavigate('hunter');
            }
          }}
          className={`
            bg-gray-900 hover:bg-black text-white font-semibold rounded-lg flex items-center justify-center transition-all shadow-md active:scale-95
            ${isCollapsed ? 'w-12 h-12 p-0 mx-auto' : 'w-full py-2.5 px-4 gap-2'}
          `}
          title={isCollapsed ? "新建扫描" : ""}
        >
          <Zap size={18} className="fill-white shrink-0" />
          <span className={`whitespace-nowrap overflow-hidden transition-all duration-300 ${isCollapsed ? 'w-0 opacity-0' : 'w-auto opacity-100'}`}>
            新建扫描
          </span>
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 space-y-1 overflow-y-auto overflow-x-hidden">
        {menuItems.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => onNavigate(item.id)}
            title={isCollapsed ? item.label : ""}
            className={`
              flex items-center rounded-md text-sm font-medium transition-all duration-300
              ${isCollapsed ? 'justify-center px-0 w-12 h-12 mx-auto' : 'justify-start w-full px-4 py-3 gap-3'}
              ${
                activePage === item.id
                  ? 'bg-gray-200 text-gray-900'
                  : 'hover:bg-gray-100 hover:text-gray-900 text-gray-600'
              }
            `}
          >
            <div className="shrink-0">{item.icon}</div>
            <span className={`whitespace-nowrap overflow-hidden transition-all duration-300 ${isCollapsed ? 'w-0 opacity-0' : 'w-auto opacity-100'}`}>
              {item.label}
            </span>
          </button>
        ))}
      </nav>

      {/* Footer / Settings */}
      <div className="p-4 border-t border-gray-200 mt-auto flex flex-col gap-2">
        <div className="text-sm">
          <button 
            type="button"
            className={`flex items-center text-gray-500 hover:text-gray-900 transition-colors ${isCollapsed ? 'justify-center w-12 h-12 mx-auto' : 'w-full py-2 gap-2'}`}
            title="系统设置"
            onClick={() => console.log('Settings clicked')}
          >
            <Settings size={16} className="shrink-0" />
            <span className={`whitespace-nowrap overflow-hidden transition-all duration-300 ${isCollapsed ? 'w-0 opacity-0' : 'w-auto opacity-100'}`}>
              系统设置
            </span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;