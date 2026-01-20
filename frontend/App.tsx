import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import Dashboard from './components/Dashboard';
import Hunter from './components/Hunter';
import Portfolio from './components/Portfolio';
import Lab from './components/Lab';
import { PageView } from './types';
import { Menu } from 'lucide-react';

const App: React.FC = () => {
  const [activePage, setActivePage] = useState<PageView>('dashboard');
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const handleNavigate = (page: PageView) => {
    setActivePage(page);
    setIsMobileMenuOpen(false);
  };

  const renderContent = () => {
    switch (activePage) {
      case 'dashboard':
        return <Dashboard />;
      case 'hunter':
        return <Hunter />;
      case 'portfolio':
        return <Portfolio />;
      case 'lab':
        return <Lab />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-gray-50 relative">
      {/* Mobile Backdrop */}
      {isMobileMenuOpen && (
        <div 
          className="fixed inset-0 bg-black/20 z-40 md:hidden backdrop-blur-sm transition-opacity"
          onClick={() => setIsMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar (Responsive) */}
      <Sidebar 
        activePage={activePage} 
        onNavigate={handleNavigate} 
        isOpen={isMobileMenuOpen}
      />
      
      {/* Main Content Area */}
      <main className="flex-1 h-full overflow-hidden relative flex flex-col w-full">
        {/* Mobile Header */}
        <div className="md:hidden p-4 bg-white border-b border-gray-200 flex items-center justify-between shrink-0 z-30">
          <div className="flex items-center gap-2">
            <span className="text-xl">🛰️</span>
            <span className="font-bold text-gray-900">DAAS Alpha</span>
          </div>
          <button 
            onClick={() => setIsMobileMenuOpen(true)}
            className="p-2 -mr-2 text-gray-600 hover:bg-gray-100 rounded-md"
          >
            <Menu size={24} />
          </button>
        </div>
        
        {/* Page Content */}
        <div className="flex-1 overflow-hidden relative">
          {renderContent()}
        </div>
      </main>
    </div>
  );
};

export default App;