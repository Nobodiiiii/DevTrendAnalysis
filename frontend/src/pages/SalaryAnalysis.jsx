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

const formatMoneyShort = (value) => {
  if (value == null || Number.isNaN(value)) return '-';
  if (value >= 1_000_000) {
    const n = (value / 1_000_000).toFixed(1);
    return `${n.endsWith('.0') ? n.slice(0, -2) : n}m`;
  }
  if (value >= 1_000) {
    const n = (value / 1_000).toFixed(1);
    return `${n.endsWith('.0') ? n.slice(0, -2) : n}k`;
  }
  return value.toLocaleString();
};

const moneyTick = (value) => `${formatMoneyShort(value)}`;

const formatDateTime = (value) => {
  if (!value) return '--';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
};

const clusterPalette = ['#0F62FE', '#2DD4BF', '#F97316', '#8B5CF6', '#16A34A'];
const trendPalette = ['#0F62FE', '#16A34A', '#F97316', '#8B5CF6', '#06B6D4', '#F43F5E'];

const buildWideSeries = (seriesList) => {
  const map = {};
  seriesList.forEach((series) => {
    series.points.forEach((pt) => {
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

  const renderTrendCard = (title, subtitle, seriesList) => {
    if (!seriesList?.length) return <p className="salary-muted">暂无可用数据</p>;
    const merged = buildWideSeries(seriesList);
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
            <LineChart data={merged} margin={{ top: 10, right: 16, left: 4, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="year" tick={{ fontSize: 12 }} />
              <YAxis tickFormatter={moneyTick} tick={{ fontSize: 12 }} />
              <Tooltip
                formatter={(value, name) => [formatMoneyShort(value), name]}
                labelFormatter={(label) => `${label} 年`}
              />
              <Legend />
              {seriesList.map((series, idx) => (
                <Line
                  key={series.name}
                  type="monotone"
                  dataKey={series.name}
                  name={series.name}
                  stroke={trendPalette[idx % trendPalette.length]}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    );
  };

  return (
    <div className="salary-page">
      <section className="salary-hero">
        <div className="salary-hero-inner">
          <p className="salary-hero-kicker">Module 02</p>
          <h1 className="salary-hero-title">
            薪资全景
            <span className="salary-hero-highlight"> · 2016-2025 多年演进</span>
          </h1>
          <p className="salary-hero-subtitle">
            结合 2016-2025 年 Stack Overflow 调查数据，抽取关键年份切片（每 5 年）和 15 年纵向走势，
            用中位数弱化极值，辅助跨地区、角色、经验的相对对标。
          </p>
          <div className="salary-hero-meta">
            <span>当前快照 {snapshot?.year || '--'} 年</span>
            <span>样本 {snapshot?.total_samples?.toLocaleString?.() || '--'}</span>
            <span>中位薪资 {overview ? formatMoneyShort(overview.median) : '--'}</span>
            <span>缓存时间 {formatDateTime(snapshot?.updated_at)}</span>
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
            <p className="salary-stat-desc">弱化极值的三分位数，更适合做谈判基准</p>
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
        {snapshot?.currency_note && (
          <div className="salary-note">
            <strong>数据预处理：</strong> 已统一去除敏感地区（如 Taiwan），并将分位数、聚类结果写入缓存，接口免二次计算。
            <br />
            {snapshot.currency_note}
          </div>
        )}
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
            <div className="salary-cluster-chart">
              {loading && renderLoader()}
              {error && renderError()}
              {!loading && !error && (
                <ResponsiveContainer>
                  <ScatterChart margin={{ top: 8, right: 12, bottom: 12, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="center_exp"
                      name="经验"
                      unit=" yrs"
                      tick={{ fontSize: 12 }}
                    />
                    <YAxis
                      dataKey="center_comp"
                      name="薪酬中心"
                      tickFormatter={moneyTick}
                      tick={{ fontSize: 12 }}
                    />
                    <ZAxis dataKey="size" range={[80, 320]} name="样本量" />
                    <Tooltip
                      formatter={(value, key, payload) => {
                        const c = payload?.payload;
                        if (key === 'center_comp') return [formatMoneyShort(value), '薪酬中心'];
                        if (key === 'center_exp') return [`${value.toFixed(1)} yrs`, '经验'];
                        if (key === 'size') return [c?.size, '样本量'];
                        return [value, key];
                      }}
                      labelFormatter={() => '聚类中心'}
                    />
                    <Legend />
                    {clusterSeries.map((c) => (
                      <Scatter
                        key={c.cluster_id}
                        name={c.label}
                        data={[c]}
                        fill={c.color}
                      />
                    ))}
                  </ScatterChart>
                </ResponsiveContainer>
              )}
            </div>
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
          <div className="salary-chart-body">
            {loading && renderLoader()}
            {error && renderError()}
            {!loading && !error && (
              <ResponsiveContainer>
                <LineChart data={overallTrend} margin={{ top: 10, right: 16, left: 4, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="year" tick={{ fontSize: 12 }} />
                  <YAxis tickFormatter={moneyTick} tick={{ fontSize: 12 }} />
                  <Tooltip
                    formatter={(value, key) => [formatMoneyShort(value), key.toUpperCase()]}
                    labelFormatter={(label) => `${label} 年`}
                  />
                  <Legend />
                  <Line type="monotone" dataKey="median" name="P50 中位" stroke="#0F62FE" strokeWidth={2} />
                  <Line type="monotone" dataKey="p75" name="P75" stroke="#16A34A" strokeWidth={1.5} dot={false} />
                  <Line type="monotone" dataKey="p25" name="P25" stroke="#F97316" strokeWidth={1.5} dot={false} />
                  <Line type="monotone" dataKey="p90" name="P90" stroke="#8B5CF6" strokeWidth={1.5} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="salary-trend-grid">
          {renderTrendCard('地区中位数走势', '选择样本量 Top 地区，查看跨年薪酬曲线。', countryTrends)}
          {renderTrendCard('角色中位数走势', '核心角色的跨年薪酬中位数，辅助“换赛道”预期对齐。', roleTrends)}
          {renderTrendCard('经验梯度走势', '不同经验梯度的薪酬中位数随年份的变化。', experienceTrends)}
        </div>
      </section>
    </div>
  );
};

export default SalaryAnalysis;
