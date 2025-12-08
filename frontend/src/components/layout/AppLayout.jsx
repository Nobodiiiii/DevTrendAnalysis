import React from 'react';
import Header from './Header';

const AppLayout = ({ children }) => {
  return (
    <div className="app-shell">
      <Header />
      <main className="app-main">
        <div className="app-main-inner">{children}</div>
      </main>
      <footer className="app-footer">
        <div className="app-footer-inner">
          <span>© {new Date().getFullYear()} Career Intelligence</span>
          <span className="app-footer-sub">Designed in an Apple-inspired style.</span>
        </div>
      </footer>
    </div>
  );
};

export default AppLayout;
