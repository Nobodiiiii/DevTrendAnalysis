// src/components/TrendChart.jsx
import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  ResponsiveContainer,
} from 'recharts';

/**
 * trend: 后端返回的 { dimension, items: [{ item, points: [...] }] }
 * mode: 'have' | 'want'
 * selectedItems: 被选中的 item 名称数组
 */
export function TrendChart({ trend, mode, selectedItems }) {
  if (!trend || !trend.items || trend.items.length === 0) {
    return <div className="chart-empty">暂无数据</div>;
  }

  // 收集所有年份
  const yearSet = new Set();
  trend.items.forEach((it) => {
    it.points.forEach((p) => yearSet.add(p.year));
  });
  const years = Array.from(yearSet).sort((a, b) => a - b);

  // 构建 Recharts 数据结构
  const data = years.map((year) => {
    const row = { year };

    selectedItems.forEach((name) => {
      const itemTrend = trend.items.find((it) => it.item === name);
      if (!itemTrend) return;

      const point = itemTrend.points.find((p) => p.year === year);
      if (!point) return;

      const value = mode === 'have' ? point.have_ratio : point.want_ratio;
      row[name] = value;
    });

    return row;
  });

  const seriesNames = selectedItems.filter((name) =>
    data.some((row) => row[name] != null),
  );

  if (seriesNames.length === 0) {
    return <div className="chart-empty">请选择至少一个技术项</div>;
  }

  const palette = [
    '#007AFF',
    '#34C759',
    '#FF9500',
    '#FF2D55',
    '#5856D6',
    '#FFCC00',
    '#5AC8FA',
    '#AF52DE',
    '#FF3B30',
    '#00C7BE',
  ];

  return (
    <div className="chart-container chart-container-large">
      <ResponsiveContainer>
        <LineChart
          data={data}
          margin={{ top: 24, right: 16, left: 0, bottom: 12 }}
        >
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="year"
            tickMargin={10}
            tick={{ fontSize: 12 }}
          />
          <YAxis
            domain={[0, 1]}
            tickFormatter={(v) => `${Math.round(v * 100)}%`}
            tick={{ fontSize: 12 }}
          />
          <Tooltip
            formatter={(value) => `${(value * 100).toFixed(1)}%`}
            labelFormatter={(year) => `Year ${year}`}
          />
          <Legend verticalAlign="top" height={32} />

          {seriesNames.map((name, idx) => (
            <Line
              key={name}
              type="monotone"
              dataKey={name}
              stroke={palette[idx % palette.length]}
              strokeWidth={2.6}
              dot={false}
              isAnimationActive={true}
              animationDuration={650}
              animationEasing="ease-out"
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
