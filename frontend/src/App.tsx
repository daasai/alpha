import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { ToastProvider } from './components/common/Toast';
import Sidebar from '../components/Sidebar';
import Dashboard from './components/pages/Dashboard';
import Hunter from './components/pages/Hunter';
import Portfolio from './components/pages/Portfolio';
import Lab from './components/pages/Lab';
import { PageView } from './types/domain';
import { Menu } from 'lucide-react';

// Inner component that uses router hooks
const AppContent: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  // Map pathname to PageView
  const getActivePage = (): PageView => {
    const path = location.pathname;
    if (path === '/hunter') return 'hunter';
    if (path === '/portfolio') return 'portfolio';
    if (path === '/lab') return 'lab';
    return 'dashboard';
  };

  const activePage = getActivePage();

  const handleNavigate = (page: PageView) => {
    setIsMobileMenuOpen(false);
    // Navigate using router
    switch (page) {
      case 'dashboard':
        navigate('/');
        break;
      case 'hunter':
        navigate('/hunter');
        break;
      case 'portfolio':
        navigate('/portfolio');
        break;
      case 'lab':
        navigate('/lab');
        break;
    }
  };

  const handleNewScan = () => {
    setIsMobileMenuOpen(false);
    navigate('/hunter?autoScan=true');
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-gray-50 relative">
      {/* Mobile Backdrop */}
      {isMobileMenuOpen && (
        <div 
          className="fixed inset-0 bg-black/20 z-40 md:hidden backdrop-blur-sm transition-opacity"
          onClick={() => setIsMobileMenuOpen(false)}
          onKeyDown={(e) => {
            if (e.key === 'Escape') {
              setIsMobileMenuOpen(false);
            }
          }}
          role="button"
          tabIndex={0}
          aria-label="关闭菜单"
        />
      )}

      {/* Sidebar (Responsive) */}
      <Sidebar 
        activePage={activePage} 
        onNavigate={handleNavigate}
        onNewScan={handleNewScan}
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
            type="button"
            onClick={() => setIsMobileMenuOpen(true)}
            className="p-2 -mr-2 text-gray-600 hover:bg-gray-100 rounded-md"
          >
            <Menu size={24} />
          </button>
        </div>
        
        {/* Page Content */}
        <div className="flex-1 overflow-hidden relative">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/hunter" element={<Hunter />} />
            <Route path="/portfolio" element={<Portfolio />} />
            <Route path="/lab" element={<Lab />} />
          </Routes>
        </div>
      </main>
    </div>
  );
};

// Main App component with Router
const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <ToastProvider>
        <BrowserRouter>
          <AppContent />
        </BrowserRouter>
      </ToastProvider>
    </ErrorBoundary>
  );
};

export default App;
