// src/components/DimensionCard.jsx
import React, { useEffect, useMemo, useState } from 'react';
import { fetchTrends } from '../api/trends';
import { TrendChart } from './TrendChart';

/**
 * props:
 * - dimension: 'language' | 'database' | ...
 * - title: 卡片标题
 * - subtitle: 卡片小说明
 */
export function DimensionCard({ dimension, title, subtitle }) {
  const [trend, setTrend] = useState(null);
  const [mode, setMode] = useState('have'); // 'have' | 'want'
  const [selectedItems, setSelectedItems] = useState([]);
  const [allItems, setAllItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // 初次加载：取这个维度的 Top N item 及其趋势
  useEffect(() => {
    let cancelled = false;

    (async () => {
      setLoading(true);
      setError('');
      try {
        const data = await fetchTrends(dimension, [], 24);
        if (cancelled) return;

        setTrend(data);

        const itemNames = (data.items || []).map((it) => it.item);
        setAllItems(itemNames);

        // 初始默认选择前 3 个
        setSelectedItems(itemNames.slice(0, 3));
      } catch (e) {
        console.error('[DimensionCard] fetch error', e);
        if (!cancelled) {
          setError(e.message || '加载失败');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [dimension]);

  // 切换 have / want
  const handleModeToggle = (nextMode) => {
    setMode(nextMode);
  };

  // 勾选 / 取消勾选某个 item
  const handleItemToggle = (item) => {
    setSelectedItems((prev) =>
      prev.includes(item) ? prev.filter((x) => x !== item) : [...prev, item],
    );
  };

  const prettyModeLabel = useMemo(
    () =>
      mode === 'have'
        ? '在职使用占比（Current Usage）'
        : '未来一年想用占比（Future Interest）',
    [mode],
  );

  return (
    <section className="dimension-card">
      <div className="dimension-card-header">
        <div>
          <h2 className="dimension-title">{title}</h2>
          <p className="dimension-subtitle">{subtitle}</p>
        </div>

        {/* 模式切换：类似 iOS 的 segmented control */}
        <div className="mode-toggle" aria-label="趋势类型切换">
          <button
            type="button"
            className={`mode-toggle-btn ${
              mode === 'have' ? 'mode-toggle-btn-active' : ''
            }`}
            onClick={() => handleModeToggle('have')}
          >
            在职使用
          </button>
          <button
            type="button"
            className={`mode-toggle-btn ${
              mode === 'want' ? 'mode-toggle-btn-active' : ''
            }`}
            onClick={() => handleModeToggle('want')}
          >
            未来想用
          </button>
        </div>
      </div>

      <p className="dimension-mode-label">{prettyModeLabel}</p>

      <div className="dimension-body">
        {/* 左侧：图表 */}
        <div className="dimension-chart-wrapper">
          {loading && <div className="pill pill-soft">加载中…</div>}
          {error && !loading && (
            <div className="pill pill-error">加载失败：{error}</div>
          )}
          {!loading && !error && (
            <TrendChart
              trend={trend}
              mode={mode}
              selectedItems={selectedItems}
            />
          )}
        </div>

        {/* 右侧：item 选择 */}
        <aside className="dimension-sidebar">
          <div className="sidebar-header">
            <span className="sidebar-title">技术项筛选</span>
            <button
              type="button"
              className="sidebar-clear-btn"
              onClick={() => setSelectedItems([])}
            >
              清空
            </button>
          </div>
          <div className="sidebar-subtitle">
            勾选后在图中叠加该技术的趋势曲线。
          </div>

          <div className="sidebar-items">
            {allItems.length === 0 && (
              <div className="sidebar-empty">无可用技术项</div>
            )}
            {allItems.map((item) => (
              <label
                key={item}
                className={`sidebar-item ${
                  selectedItems.includes(item)
                    ? 'sidebar-item-selected'
                    : ''
                }`}
              >
                <input
                  type="checkbox"
                  checked={selectedItems.includes(item)}
                  onChange={() => handleItemToggle(item)}
                />
                <span className="sidebar-item-label">{item}</span>
              </label>
            ))}
          </div>
        </aside>
      </div>
    </section>
  );
}
