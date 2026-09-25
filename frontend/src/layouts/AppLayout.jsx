import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { RoleProvider, useRole } from '../context/RoleContext';
import { Navbar } from '../components/layout/Navbar';
import { Sidebar } from '../components/layout/Sidebar';

function AppLayoutInner() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const { roleInfo } = useRole();

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col transition-colors duration-300">
      <Navbar onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)} />

      <div className="flex flex-1">
        <Sidebar
          isOpen={isSidebarOpen}
          onCloseSidebar={() => setIsSidebarOpen(false)}
        />

        <main className="flex-1 p-4 md:p-6 lg:p-8 max-w-7xl mx-auto w-full overflow-x-hidden space-y-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export function AppLayout() {
  return (
    <RoleProvider>
      <AppLayoutInner />
    </RoleProvider>
  );
}
