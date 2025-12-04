// src/App.jsx
import React from 'react';
import { DimensionCard } from './components/DimensionCard';
import './index.css';

const DIMENSIONS = [
  {
    key: 'language',
    title: '编程语言生态（Language Ecosystem）',
    subtitle: '主流与边缘语言的在职使用与未来偏好演化。',
  },
  {
    key: 'database',
    title: '数据库技术栈（Database）',
    subtitle: '关系型与新型数据存储的采用趋势。',
  },
  {
    key: 'platform',
    title: '平台与运行环境（Platform）',
    subtitle: '云平台、桌面与移动端的长期分布。',
  },
  {
    key: 'webframe',
    title: 'Web 框架与框架族（Web Framework）',
    subtitle: '从单体框架到前后端分离的演进轨迹。',
  },
  {
    key: 'misctech',
    title: '通用技术栈（Misc Tech）',
    subtitle: '基础设施、数据与工程效率技术的渗透情况。',
  },
  {
    key: 'toolstech',
    title: '工程工具（Tools & Toolchains）',
    subtitle: '构建、部署与质量保障工具的采用率。',
  },
  {
    key: 'collabtools',
    title: '协作与生产力工具（Collaboration）',
    subtitle: '从代码托管到协同办公的全链路协作。',
  },
];

function App() {
  return (
    <div className="app-root">
      <main className="app-shell">
        {/* 顶部 Hero 区域 */}
        <header className="app-hero">
          <div>
            <div className="badge-pill">DevTrend Observatory</div>
            <h1 className="hero-title">工程技术栈趋势总览</h1>
            <p className="hero-subtitle">
              基于多年度调研样本，对不同维度的「实际使用」与「未来意向」进行对比，
              以观察技术栈的生命周期与演化节奏。
            </p>
          </div>
        </header>

        {/* 一列排列：每行一个大卡片 */}
        <section className="grid-single-column">
          {DIMENSIONS.map((dim) => (
            <DimensionCard
              key={dim.key}
              dimension={dim.key}
              title={dim.title}
              subtitle={dim.subtitle}
            />
          ))}
        </section>
      </main>
    </div>
  );
}

export default App;
