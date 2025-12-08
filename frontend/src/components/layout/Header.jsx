import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import logoMark from '../../assets/logo-mark.svg';

const navItems = [
  {
    to: '/future-landscape',
    labelEn: 'Future Landscape',
    labelZh: '技术趋势'
  },
  {
    to: '/value-spectrum',
    labelEn: 'Value Spectrum',
    labelZh: '薪资分析'
  },
  {
    to: '/career-compass',
    labelEn: 'Career Compass',
    labelZh: '个人建议'
  }
];

const Header = () => {
  const navigate = useNavigate();

  return (
    <header className="app-header">
      <div className="app-header-inner">
        <button
          className="brand-block"
          onClick={() => navigate('/')}
          aria-label="回到首页"
        >
          <img src={logoMark} alt="Logo" className="brand-logo" />
          <div className="brand-text">
            <span className="brand-title">Career Intelligence</span>
            <span className="brand-subtitle">职业洞察实验室</span>
          </div>
        </button>

        <nav className="app-nav">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                'nav-link' + (isActive ? ' nav-link-active' : '')
              }
            >
              <span className="nav-link-en">{item.labelEn}</span>
              <span className="nav-link-zh">{item.labelZh}</span>
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
};

export default Header;
