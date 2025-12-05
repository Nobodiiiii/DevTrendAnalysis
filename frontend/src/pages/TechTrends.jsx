import React from 'react';
import '../styles/tech-trends.css';
import { DimensionCard } from '../components/DimensionCard';

// 真正使用的 7 个维度，对应后端 DIMENSION_TABLES 的 key
// DIMENSION_TABLES: Dict[str, str] = {
//   "language": "language_usage_trend",
//   "database": "database_usage_trend",
//   "platform": "platform_usage_trend",
//   "webframe": "webframe_usage_trend",
//   "misctech": "misctech_usage_trend",
//   "toolstech": "toolstech_usage_trend",
//   "collabtools": "collabtools_usage_trend",
// }
const DIMENSION_CONFIGS = [
  {
    dimension: 'language',
    eyebrow: 'Dimension 01 · Language',
    title: '编程语言地平线',
    subtitle: '哪些语言正在成为默认选择，哪些逐渐淡出视野。'
  },
  {
    dimension: 'database',
    eyebrow: 'Dimension 02 · Database',
    title: '数据存储与数据库版图',
    subtitle: '从关系型到云原生数据库，不同场景下的主流选择。'
  },
  {
    dimension: 'platform',
    eyebrow: 'Dimension 03 · Platform',
    title: '云平台与运行环境',
    subtitle: '公有云、私有云与混合形态下，运行环境的偏好变化。'
  },
  {
    dimension: 'webframe',
    eyebrow: 'Dimension 04 · Web Framework',
    title: 'Web 框架与前端技术栈',
    subtitle: '从经典 MVC 到全栈框架，前端工程的主流路径。'
  },
  {
    dimension: 'misctech',
    eyebrow: 'Dimension 05 · Engineering Practices',
    title: '工程实践与杂项技术',
    subtitle: '测试、监控、可观测性等工程实践在团队中的普及度。'
  },
  {
    dimension: 'toolstech',
    eyebrow: 'Dimension 06 · Tooling',
    title: '开发工具与生产力堆栈',
    subtitle: 'IDE、CI/CD、代码质量工具对开发效率的实际影响。'
  },
  {
    dimension: 'collabtools',
    eyebrow: 'Dimension 07 · Collaboration',
    title: '协作工具与工作流',
    subtitle: '远程协作时代，团队如何在工具与流程上达成共识。'
  }
];

const TechTrends = () => {
  return (
    <div className="tech-page">
      {/* 顶部 Hero */}
      <section className="tech-hero">
        <div className="tech-hero-content">
          <p className="tech-hero-kicker">Module 01 · Future Landscape</p>
          <h1 className="tech-hero-title">
            技术地平线
            <span className="tech-hero-highlight"> · Future Landscape</span>
          </h1>
          <p className="tech-hero-subtitle">
            这不是新闻聚合，而是一张帮助你定位自己的技术地图。
            我们用少量、稳定的趋势维度，替代碎片化的“技术热点”。
          </p>
          <div className="tech-hero-meta">
            <span>视角：3–5 年</span>
            <span>关注对象：中高级工程师 & 技术管理者</span>
            <span>形式：交互式趋势图 + 文字解读</span>
          </div>
        </div>
      </section>

      {/* 趋势维度简介 */}
      <section className="tech-intro">
        <div className="tech-intro-card">
          <h2>如何阅读这张“技术地平线”</h2>
          <p>
            每一张趋势图代表一个<strong>持续 3 年以上</strong>的方向，而不是昙花一现的 buzzword。
            你可以用它做三件事：
          </p>
          <ol>
            <li>确认自己当前所在的技术浪潮，避免身处“退潮区”。</li>
            <li>识别下一步需要补齐的知识带，控制学习的“焦距”。</li>
            <li>与管理者或 HR 沟通时，拥有一张更宏观的语言地图。</li>
          </ol>
          <p className="tech-intro-note">
            下方 7 个维度都基于同一套趋势数据，你可以通过右侧的技术项筛选来叠加或对比不同技术曲线。
          </p>
        </div>
      </section>

      {/* 趋势图区域：一行一个维度，左说明，右图表 */}
      <section className="tech-charts">
        <div className="tech-charts-header">
          <h2>7 个关键趋势维度 · 交互式趋势图</h2>
          <p>
            每行代表一个趋势维度：左侧说明维度含义，右侧是可交互的<strong>在职使用 / 未来想用</strong>
            折线图，你可以勾选不同技术项进行对比。
          </p>
        </div>

        <div className="tech-charts-list">
          {DIMENSION_CONFIGS.map((cfg, index) => (
            <div key={cfg.dimension} className="tech-chart-row">
              {/* 左侧文案说明 */}
              <div className="tech-chart-row-label">
                <div className="tech-chart-row-index">
                  {String(index + 1).padStart(2, '0')}
                </div>
                <div className="tech-chart-row-label-text">
                  <div className="tech-chart-row-eyebrow">{cfg.eyebrow}</div>
                  <h3 className="tech-chart-row-title">{cfg.title}</h3>
                  <p className="tech-chart-row-subtitle">{cfg.subtitle}</p>
                </div>
              </div>

              {/* 右侧真实图表卡片 */}
              <div className="tech-chart-row-card">
                <DimensionCard
                  dimension={cfg.dimension}
                  title={cfg.title}
                  subtitle={cfg.subtitle}
                />
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};

export default TechTrends;
