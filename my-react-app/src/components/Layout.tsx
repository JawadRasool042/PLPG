import React from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import Footer from './Footer';
import AIChatbot from './AIChatbot';

const Layout: React.FC = () => {
  return (
    <div className="site-shell min-h-[100dvh] flex flex-col overflow-x-clip">
      <Navbar />
      <main className="site-main flex-grow min-w-0 w-full">
        <Outlet />
      </main>
      <Footer />
      <AIChatbot />
    </div>
  );
};

export default Layout;
