import React from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import Footer from './Footer';
import AIChatbot from './AIChatbot';

const Layout: React.FC = () => {
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-grow pt-16 sm:pt-20">
        <Outlet />
      </main>
      <Footer />
      <AIChatbot />
    </div>
  );
};

export default Layout;

