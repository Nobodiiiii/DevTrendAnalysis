import React, { useEffect, useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts';
import '../styles/salary-analysis.css';
import { fetchSalaryTimeline } from '../api/salary';
import { TREND_COLORS } from '../components/TrendChart';

// 薪酬走势曲线配置
const SALARY_TREND_LINES = [
  { dataKey: 'median', name: 'P50 中位数', strokeWidth: 2.6 },
  { dataKey: 'p75', name: 'P75 分位', strokeWidth: 1.8 },
  { dataKey: 'p25', name: 'P25 分位', strokeWidth: 1.8 },
  { dataKey: 'p90', name: 'P90 分位', strokeWidth: 1.8 },
];

// 美元转人民币汇率
const USD_TO_CNY = 7.2;

const formatMoneyShort = (value) => {
  if (value == null || Number.isNaN(value)) return '-';
  // 转换为人民币，以"万"为单位
  const cny = value * USD_TO_CNY;
  const wan = cny / 10000;
  if (wan >= 1) {
    const n = wan.toFixed(1);
    return `¥${n.endsWith('.0') ? n.slice(0, -2) : n}万`;
  }
  return `¥${Math.round(cny).toLocaleString()}`;
};

const moneyTick = (value) => {
  if (value == null || Number.isNaN(value)) return '-';
  const cny = value * USD_TO_CNY;
  const wan = cny / 10000;
  if (wan >= 1) {
    const n = wan.toFixed(0);
    return `${n}万`;
  }
  return `${Math.round(cny / 1000)}k`;
};

const formatDateTime = (value) => {
  if (!value) return '--';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
};

const clusterPalette = ['#0F62FE', '#2DD4BF', '#F97316', '#8B5CF6', '#16A34A'];

const buildWideSeries = (seriesList, minYear = null) => {
  const map = {};
  seriesList.forEach((series) => {
    series.points.forEach((pt) => {
      if (minYear && pt.year < minYear) return;
      if (!map[pt.year]) map[pt.year] = { year: pt.year };
      map[pt.year][series.name] = pt.median;
    });
  });
  return Object.values(map).sort((a, b) => a.year - b.year);
};

const SalaryAnalysis = () => {
  const [timeline, setTimeline] = useState(null);
  const [selectedYear, setSelectedYear] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setError('');
        setLoading(true);
        const res = await fetchSalaryTimeline();
        if (!cancelled) {
          setTimeline(res);
          const years = (res?.snapshots || [])
            .map((s) => s.year)
            .filter(Boolean)
            .sort((a, b) => a - b);
          setSelectedYear(years[years.length - 1] || null);
        }
      } catch (e) {
        if (!cancelled) setError(e.message || '加载失败');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const snapshots = timeline?.snapshots || [];
  const snapshotYears = useMemo(
    () =>
      [...new Set(snapshots.map((s) => s.year))]
        .filter(Boolean)
        .sort((a, b) => a - b),
    [snapshots],
  );

  const snapshot = useMemo(() => {
    if (!snapshots.length) return null;
    const hit = snapshots.find((s) => s.year === selectedYear);
    return hit || snapshots[snapshots.length - 1];
  }, [snapshots, selectedYear]);

  const overview = snapshot?.distribution;
  const countries = snapshot?.top_countries || [];
  const expBuckets = snapshot?.experience_buckets || [];
  const roleBenchmarks = snapshot?.role_benchmarks || [];
  const satisfactionBands = snapshot?.satisfaction_bands || [];
  const clusters = snapshot?.clusters || [];

  const headline = useMemo(() => {
    if (!overview) return '--';
    return `${formatMoneyShort(overview.median)} · 中位数`;
  }, [overview]);

  const clusterSeries = useMemo(
    () =>
      clusters.map((c, idx) => ({
        ...c,
        color: clusterPalette[idx % clusterPalette.length],
      })),
    [clusters],
  );

  const overallTrend = timeline?.overall_trend || [];
  const countryTrends = timeline?.country_trends || [];
  const roleTrends = timeline?.role_trends || [];
  const experienceTrends = timeline?.experience_trends || [];

  const renderLoader = () => (
    <div className="salary-loader">
      <span className="pill-dot" />
      正在拉取薪资画像...
    </div>
  );

  const renderError = () => (
    <div className="salary-error">
      <span className="pill-dot pill-dot-error" />
      {error}
    </div>
  );

  // 高对比度颜色调色板
  const HIGH_CONTRAST_COLORS = [
    '#0F62FE', // 深蓝
    '#EF4444', // 红色
    '#10B981', // 绿色
    '#F59E0B', // 橙色
    '#8B5CF6', // 紫色
    '#06B6D4', // 青色
    '#EC4899', // 粉色
    '#84CC16', // 黄绿
  ];

  const renderTrendCard = (title, subtitle, seriesList, minYear = null, options = {}) => {
    if (!seriesList?.length) return <p className="salary-muted">暂无可用数据</p>;
    const merged = buildWideSeries(seriesList, minYear);

    // 计算每个系列在 minYear 之后是否有数据
    const seriesWithData = seriesList.filter((series) => {
      if (!minYear) return true;
      return series.points?.some((pt) => pt.year >= minYear && pt.median != null);
    });

    // Y轴范围配置
    const { yMin, yMax } = options;
    const yDomain = yMin != null && yMax != null ? [yMin, yMax] : undefined;

    return (
      <div className="salary-trend-card">
        <div className="salary-chart-header">
          <div>
            <p className="salary-eyebrow">Trend</p>
            <h3 className="salary-chart-title">{title}</h3>
            <p className="salary-chart-subtitle">{subtitle}</p>
          </div>
        </div>
        <div className="salary-trend-body">
          <ResponsiveContainer>
            <LineChart data={merged} margin={{ top: 18, right: 16, left: 0, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="year" tickMargin={10} tick={{ fontSize: 12 }} />
              <YAxis
                domain={yDomain}
                tickFormatter={moneyTick}
                tick={{ fontSize: 12 }}
              />
              <Tooltip
                formatter={(value, name) => [formatMoneyShort(value), name]}
                labelFormatter={(label) => `${label} 年`}
              />
              {seriesWithData.map((series, idx) => (
                <Line
                  key={series.name}
                  type="monotone"
                  dataKey={series.name}
                  name={series.name}
                  stroke={HIGH_CONTRAST_COLORS[idx % HIGH_CONTRAST_COLORS.length]}
                  strokeWidth={2.2}
                  dot={false}
                  activeDot={{ r: 4 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="salary-trend-legend">
          {seriesWithData.map((series, idx) => (
            <div className="salary-trend-legend-item" key={series.name}>
              <span
                className="salary-trend-legend-dot"
                style={{ background: HIGH_CONTRAST_COLORS[idx % HIGH_CONTRAST_COLORS.length] }}
              />
              <span className="salary-trend-legend-label">{series.name}</span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  // 聚类指标展示组件
  const clusterMetrics = timeline?.cluster_metrics;

  const renderClusterMetrics = () => {
    if (!clusterMetrics) return <p className="salary-muted">暂无聚类指标数据。请先运行 generate_salary_insights.py 生成。</p>;

    const formatPct = (v, digits = 3) => {
      if (v === null || v === undefined || Number.isNaN(Number(v))) return '-';
      return Number(v).toFixed(digits);
    };

    const formatDateTime = (v) => {
      if (!v) return '-';
      const d = new Date(v);
      if (Number.isNaN(d.getTime())) return v;
      return d.toLocaleString('zh-CN');
    };

    return (
      <div className="salary-metrics">
        {/* 汇总指标 */}
        <div className="salary-metrics-section">
          <div className="salary-metrics-section-title">聚类质量评估</div>
          <div className="salary-metrics-grid">
            <div className="salary-metrics-item">
              <span className="salary-metrics-label">质量评级</span>
              <span className="salary-metrics-value">{clusterMetrics.quality_assessment || '-'}</span>
            </div>
            <div className="salary-metrics-item">
              <span className="salary-metrics-label">平均轮廓系数</span>
              <span className="salary-metrics-value">{formatPct(clusterMetrics.avg_silhouette_score)}</span>
            </div>
            <div className="salary-metrics-item">
              <span className="salary-metrics-label">平均 DB 指数</span>
              <span className="salary-metrics-value">{formatPct(clusterMetrics.avg_davies_bouldin_index)}</span>
            </div>
            <div className="salary-metrics-item">
              <span className="salary-metrics-label">覆盖年份数</span>
              <span className="salary-metrics-value">{clusterMetrics.total_years || '-'}</span>
            </div>
          </div>
        </div>

        {/* 各年指标 */}
        {clusterMetrics.yearly_metrics?.length > 0 && (
          <div className="salary-metrics-section">
            <div className="salary-metrics-section-title">各年份聚类指标</div>
            <div className="salary-metrics-table">
              <table>
                <thead>
                  <tr>
                    <th>年份</th>
                    <th>聚类数</th>
                    <th>样本量</th>
                    <th>轮廓系数</th>
                    <th>DB 指数</th>
                    <th>惯性</th>
                  </tr>
                </thead>
                <tbody>
                  {clusterMetrics.yearly_metrics.map((m) => (
                    <tr key={m.year || 'latest'}>
                      <td>{m.year || 'latest'}</td>
                      <td>{m.n_clusters}</td>
                      <td>{m.n_samples?.toLocaleString()}</td>
                      <td>{formatPct(m.silhouette_score)}</td>
                      <td>{formatPct(m.davies_bouldin_index)}</td>
                      <td>{m.inertia?.toFixed(1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* 指标解释 */}
        {clusterMetrics.interpretation && (
          <div className="salary-metrics-section">
            <div className="salary-metrics-section-title">指标说明</div>
            <div className="salary-metrics-interp">
              {Object.entries(clusterMetrics.interpretation).map(([key, desc]) => (
                <div key={key} className="salary-metrics-interp-item">
                  <strong>{key}:</strong> {desc}
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="salary-metrics-footer">
          生成时间: {formatDateTime(clusterMetrics.generated_at)}
        </div>
      </div>
    );
  };

  return (
    <div className="salary-page">
      <section className="salary-hero">
        <div className="salary-hero-content">
          <p className="salary-hero-kicker">Module 02</p>
          <h1 className="salary-hero-title">
            薪资全景
            <span className="salary-hero-highlight"> · Value Spectrum</span>
          </h1>
          <p className="salary-hero-subtitle">
            结合 2016-2025 年 Stack Overflow 调查数据，抽取关键年份切片（每 5 年）和 15 年纵向走势，
            用中位数弱化极值，辅助跨地区、角色、经验的相对对标。
          </p>
          <div className="salary-hero-meta">
            <span>当前快照 {snapshot?.year || '--'} 年</span>
            <span>样本 {snapshot?.total_samples?.toLocaleString?.() || '--'}</span>
          </div>
        </div>
        <div className="salary-hero-badge">
          <div className="salary-badge-label">核心锚点</div>
          <div className="salary-badge-value">{headline}</div>
          <div className="salary-badge-meta">以中位数衡量真实市场，弱化极值</div>
        </div>
      </section>

      <section className="salary-year-switcher">
        <div className="salary-year-info">
          <p className="salary-eyebrow">Milestones</p>
          <h3 className="salary-chart-title">每 5 年一张快照</h3>
          <p className="salary-chart-subtitle">
            一键切换 2016 / 2021 / 2025 三个时期，对比市场结构与薪资曲线。
          </p>
        </div>
        <div className="salary-year-pills">
          {snapshotYears.map((year) => (
            <button
              key={year}
              type="button"
              className={`salary-year-pill ${selectedYear === year ? 'is-active' : ''}`}
              onClick={() => setSelectedYear(year)}
            >
              {year}
            </button>
          ))}
        </div>
      </section>

      <section className="salary-overview">
        <div className="salary-stats-grid">
          <div className="salary-stat-card">
            <p className="salary-stat-label">样本量</p>
            <h3 className="salary-stat-value">
              {snapshot?.total_samples?.toLocaleString?.() || '--'}
            </h3>
            <p className="salary-stat-desc">过滤空值后的薪资样本数</p>
          </div>
          <div className="salary-stat-card">
            <p className="salary-stat-label">P25 · P50 · P75</p>
            <h3 className="salary-stat-value">
              {overview
                ? `${formatMoneyShort(overview.p25)} / ${formatMoneyShort(
                    overview.median,
                  )} / ${formatMoneyShort(overview.p75)}`
                : '--'}
            </h3>
            <p className="salary-stat-desc">弱化极值的三分位数</p>
          </div>
          <div className="salary-stat-card">
            <p className="salary-stat-label">Top 10%</p>
            <h3 className="salary-stat-value">
              {overview ? formatMoneyShort(overview.p90) : '--'}
            </h3>
            <p className="salary-stat-desc">高分位天花板，结合地区/角色再看</p>
          </div>
          <div className="salary-stat-card">
            <p className="salary-stat-label">均值</p>
            <h3 className="salary-stat-value">
              {overview ? formatMoneyShort(overview.mean) : '--'}
            </h3>
            <p className="salary-stat-desc">均值受极值影响，慎用</p>
          </div>
        </div>
      </section>

      <section className="salary-charts">
        <div className="salary-chart-card">
          <div className="salary-chart-header">
            <div>
              <p className="salary-eyebrow">Geo · Region</p>
              <h3 className="salary-chart-title">地区视角 · 切片</h3>
              <p className="salary-chart-subtitle">
                以中位数排序，仅保留样本量 ≥ 50 的地区，展示 P50 / P75。
              </p>
            </div>
          </div>
          <div className="salary-chart-body">
            {loading && renderLoader()}
            {error && renderError()}
            {!loading && !error && (
              <ResponsiveContainer>
                <BarChart
                  layout="vertical"
                  data={countries}
                  margin={{ top: 8, right: 12, bottom: 8, left: 12 }}
                >
                  <CartesianGrid strokeDasharray="3 3" horizontal />
                  <XAxis
                    type="number"
                    tickFormatter={moneyTick}
                    tick={{ fontSize: 12 }}
                  />
                  <YAxis
                    dataKey="country"
                    type="category"
                    width={120}
                    tick={{ fontSize: 12 }}
                  />
                  <Tooltip formatter={(value) => formatMoneyShort(value)} />
                  <Legend />
                  <Bar dataKey="median" name="P50 中位" fill="#0F62FE" barSize={16} radius={[8, 8, 8, 8]} />
                  <Bar dataKey="p75" name="P75" fill="#A5B4FC" barSize={16} radius={[8, 8, 8, 8]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="salary-chart-card">
          <div className="salary-chart-header">
            <div>
              <p className="salary-eyebrow">Experience · Buckets</p>
              <h3 className="salary-chart-title">经验梯度 · 切片</h3>
              <p className="salary-chart-subtitle">以经验区间聚合，查看每段的 P50 / 平均值。</p>
            </div>
          </div>
          <div className="salary-chart-body">
            {loading && renderLoader()}
            {error && renderError()}
            {!loading && !error && (
              <ResponsiveContainer>
                <ComposedChart data={expBuckets} margin={{ top: 8, right: 12, bottom: 8, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="label" tick={{ fontSize: 12 }} />
                  <YAxis tickFormatter={moneyTick} tick={{ fontSize: 12 }} />
                  <Tooltip formatter={(value, key) => [formatMoneyShort(value), key]} />
                  <Legend />
                  <Bar dataKey="average" name="均值" fill="#E5E7EB" barSize={22} radius={[6, 6, 6, 6]} />
                  <Line
                    type="monotone"
                    dataKey="median"
                    name="P50 中位"
                    stroke="#0F62FE"
                    strokeWidth={2.6}
                    dot={{ r: 4 }}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="salary-chart-card">
          <div className="salary-chart-header">
            <div>
              <p className="salary-eyebrow">Role · Benchmark</p>
              <h3 className="salary-chart-title">角色基准 · 切片</h3>
              <p className="salary-chart-subtitle">
                统计样本 ≥ 120 的高频角色，按中位数排序，可用于“换赛道”预期对齐。
              </p>
            </div>
          </div>
          <div className="salary-chart-body">
            {loading && renderLoader()}
            {error && renderError()}
            {!loading && !error && (
              <ResponsiveContainer>
                <BarChart
                  layout="vertical"
                  data={roleBenchmarks}
                  margin={{ top: 8, right: 16, bottom: 8, left: 12 }}
                >
                  <CartesianGrid strokeDasharray="3 3" horizontal />
                  <XAxis
                    type="number"
                    tickFormatter={moneyTick}
                    tick={{ fontSize: 12 }}
                  />
                  <YAxis
                    dataKey="role"
                    type="category"
                    width={180}
                    tick={{ fontSize: 12 }}
                  />
                  <Tooltip
                    formatter={(value, key) =>
                      [formatMoneyShort(value), key === 'median' ? 'P50 中位' : 'P75']
                    }
                  />
                  <Legend />
                  <Bar
                    dataKey="median"
                    name="P50 中位"
                    fill="#111111"
                    radius={[8, 8, 8, 8]}
                    barSize={16}
                  />
                  <Bar
                    dataKey="p75"
                    name="P75"
                    fill="#52525B"
                    radius={[8, 8, 8, 8]}
                    barSize={16}
                  />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="salary-chart-card">
          <div className="salary-chart-header">
            <div>
              <p className="salary-eyebrow">Mood · Satisfaction</p>
              <h3 className="salary-chart-title">满意度 · 薪酬映射</h3>
              <p className="salary-chart-subtitle">
                满意度越高，对应的薪酬中位数也越高，提示“提升技能与环境匹配度”能带来溢价。
              </p>
            </div>
          </div>
          <div className="salary-satisfaction-grid">
            {loading && renderLoader()}
            {error && renderError()}
            {!loading &&
              !error &&
              satisfactionBands.map((band) => (
                <div className="salary-sat-card" key={band.band}>
                  <p className="salary-sat-label">{band.band}</p>
                  <h4 className="salary-sat-value">
                    {formatMoneyShort(band.median)}
                  </h4>
                  <p className="salary-sat-desc">
                    样本 {band.count.toLocaleString()}
                  </p>
                </div>
              ))}
          </div>
        </div>

        <div className="salary-chart-card salary-cluster-card">
          <div className="salary-chart-header">
            <div>
              <p className="salary-eyebrow">ML · Clustering</p>
              <h3 className="salary-chart-title">经验 × 薪酬 聚类剖面</h3>
              <p className="salary-chart-subtitle">
                预先跑 K-Means 对经验与薪酬做聚类，定位市场上的高薪/核心人群，展示聚类中心与主导角色、地区。
              </p>
            </div>
          </div>
          <div className="salary-cluster-grid">
            <div className="salary-cluster-list">
              {loading && renderLoader()}
              {error && renderError()}
              {!loading &&
                !error &&
                clusterSeries.map((c) => (
                  <div className="salary-cluster-item" key={c.cluster_id}>
                    <div className="salary-cluster-title">
                      <span
                        className="salary-cluster-dot"
                        style={{ background: c.color }}
                      />
                      <div>
                        <p className="salary-cluster-name">{c.label}</p>
                        <p className="salary-cluster-meta">
                          样本 {c.size} · 经验 {c.center_exp?.toFixed?.(1) || '--'} yrs
                        </p>
                      </div>
                    </div>
                    <p className="salary-cluster-pay">
                      中心薪酬 {formatMoneyShort(c.center_comp)}
                    </p>
                    <p className="salary-cluster-desc">
                      高频角色：{c.dominant_role || '未知'} · 高频地区：{c.dominant_country || '未知'}
                    </p>
                  </div>
                ))}
            </div>
          </div>
        </div>
      </section>

      <section className="salary-trend-section">
        <div className="salary-chart-card">
          <div className="salary-chart-header">
            <div>
              <p className="salary-eyebrow">Longitudinal · 15Y</p>
              <h3 className="salary-chart-title">15 年整体薪酬走势</h3>
              <p className="salary-chart-subtitle">
                纵向观察 2012-2025（数据覆盖 2016-2025 核心年份），看中位数与分位数的长期变化。
              </p>
            </div>
          </div>
          <div className="salary-overall-grid">
            <div className="salary-overall-chart">
              {loading && renderLoader()}
              {error && renderError()}
              {!loading && !error && (
                <ResponsiveContainer>
                  <LineChart data={overallTrend} margin={{ top: 18, right: 16, left: 0, bottom: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="year" tickMargin={10} tick={{ fontSize: 12 }} />
                    <YAxis tickFormatter={moneyTick} tick={{ fontSize: 12 }} />
                    <Tooltip
                      formatter={(value, key) => [formatMoneyShort(value), key.toUpperCase()]}
                      labelFormatter={(label) => `${label} 年`}
                    />
                    {SALARY_TREND_LINES.map((line, idx) => (
                      <Line
                        key={line.dataKey}
                        type="monotone"
                        dataKey={line.dataKey}
                        name={line.name}
                        stroke={TREND_COLORS[idx % TREND_COLORS.length]}
                        strokeWidth={line.strokeWidth}
                        dot={idx === 0 ? { r: 3 } : false}
                        activeDot={{ r: 4 }}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
            <aside className="salary-overall-sidebar">
              <div className="salary-sidebar-header">
                <span className="salary-sidebar-title">分位数曲线</span>
                <span className="salary-sidebar-hint">纵向趋势对比</span>
              </div>
              <div className="salary-sidebar-items">
                {SALARY_TREND_LINES.map((line, idx) => (
                  <div className="salary-sidebar-item" key={line.dataKey}>
                    <span
                      className="salary-sidebar-dot"
                      style={{ background: TREND_COLORS[idx % TREND_COLORS.length] }}
                    />
                    <span className="salary-sidebar-label">{line.name}</span>
                  </div>
                ))}
              </div>
            </aside>
          </div>
        </div>

        <div className="salary-trend-grid">
          {renderTrendCard('地区中位数走势', '选择样本量 Top 地区，查看跨年薪酬曲线。', countryTrends)}
          {renderTrendCard('角色中位数走势', '核心角色薪酬中位数，对齐"换赛道"预期。', roleTrends, 2019, { yMin: 27778, yMax: 97222 })}
          {renderTrendCard('经验梯度走势', '不同经验梯度的薪酬中位数随年份的变化。', experienceTrends)}
        </div>
      </section>

      {/* 算法指标展示 */}
      <section className="salary-metrics-section">
        <details className="salary-details">
          <summary>查看算法指标（KMeans 聚类质量）</summary>
          {renderClusterMetrics()}
        </details>
      </section>
    </div>
  );
};

export default SalaryAnalysis;
