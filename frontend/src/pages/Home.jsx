import React from 'react';
import '../styles/home.css';
import ModuleCard from '../components/common/ModuleCard';

const Home = () => {
  return (
    <div className="home-page">
      {/* Hero 区域 */}
      <section className="home-hero">
        <div className="home-hero-content">
          <p className="home-hero-kicker">Career Intelligence · 职业洞察</p>
          <h1 className="home-hero-title">
            让职业决策
            <span className="home-hero-highlight"> 像选一台 Mac 一样清晰</span>
          </h1>
          <p className="home-hero-subtitle">
            用数据和趋势，而不是焦虑与猜测，来回答三个核心问题：
            <br />
            技术往哪里走？价值如何被定价？我应该怎么走？
          </p>

          <div className="home-hero-actions">
            <button
              className="primary-cta"
              onClick={() => (window.location.href = '/future-landscape')}
            >
              立即查看技术趋势
            </button>
            <button
              className="ghost-cta"
              onClick={() => (window.location.href = '/value-spectrum')}
            >
              浏览薪资版图
            </button>
          </div>

          <p className="home-hero-microcopy">
            为中高级开发者与技术管理者设计 · 不做招聘广告，只讲清楚信息。
          </p>
        </div>
      </section>

      {/* 模块总览 */}
      <section className="home-modules">
        <div className="home-modules-header">
          <h2>三块能力，一体化视角</h2>
          <p>
            从宏观趋势到个人路线，用三个模块构成你的职业决策系统。
          </p>
        </div>

        <div className="home-modules-grid">
          <ModuleCard
            to="/future-landscape"
            eyebrow="Module 01 · Future Landscape"
            title="技术地平线 · Future Landscape"
            description="7 大关键技术方向，配合趋势占位图，为你的技术栈和行业选择提供冷静的“高空视角”。"
            accent="聚焦 3–5 年视角"
          />
          <ModuleCard
            to="/value-spectrum"
            eyebrow="Module 02 · Value Spectrum"
            title="价值光谱 · Value Spectrum"
            description="从城市、职级、领域多个维度拆解薪资分布，帮你看清“什么样的能力组合，值多少钱”。"
            accent="多维薪资剖面图"
          />
          <ModuleCard
            to="/career-compass"
            eyebrow="Module 03 · Career Compass"
            title="职业罗盘 · Career Compass"
            description="根据你的阶段、偏好和约束，生成几条清晰的路线草图，并给出下一步行动建议。"
            accent="个人决策建议"
          />
        </div>
      </section>

      {/* 底部说明 */}
      <section className="home-bottom-note">
        <div className="home-bottom-card">
          <h3>如何使用这个网站？</h3>
          <p>
            推荐从 <strong>技术地平线</strong> 开始，确认自己所在的技术浪潮；
            然后进入 <strong>价值光谱</strong> 对齐现实薪资区间；
            最后在 <strong>职业罗盘</strong> 中，把信息转化成具体决策。
          </p>
        </div>
      </section>
    </div>
  );
};

export default Home;
