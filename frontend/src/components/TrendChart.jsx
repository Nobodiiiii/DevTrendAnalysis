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
 * 30 个冷色系苹果风蓝色，从深到浅排序
 */
export const TREND_COLORS = [
  // 蓝 / 青（冷色优先，适合作为默认系列）
  '#0F62FE', // deep blue
  '#60A5FA', // light blue
  '#0EA5E9', // cyan-blue
  '#38BDF8', // sky cyan
  '#06B6D4', // cyan
  '#14B8A6', // teal

  // 绿系
  '#10B981', // emerald
  '#22C55E', // green
  '#4ADE80', // light green
  '#A3E635', // lime

  // 黄 / 橙
  '#EAB308', // yellow
  '#FACC15', // bright yellow
  '#F59E0B', // amber
  '#FDBA74', // light amber
  '#F97316', // orange
  '#FB923C', // light orange

  // 红 / 玫红
  '#EF4444', // red
  '#F87171', // soft red
  '#F43F5E', // rose
  '#FB7185', // light rose

  // 品红 / 紫 / 靛蓝（靠后更“点缀感”）
  '#EC4899', // pink
  '#E879F9', // fuchsia
  '#8B5CF6', // violet
  '#6366F1', // indigo
];


/**
 * 自定义 Tooltip，苹果风小卡片样式
 */
function CustomTooltip({ active, payload, label }) {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip-header">
        <span className="chart-tooltip-title">年份 {label}</span>
      </div>
      <div className="chart-tooltip-body">
        {payload.map((entry) => (
          <div className="chart-tooltip-row" key={entry.dataKey}>
            <span
              className="chart-tooltip-dot"
              style={{ background: entry.color }}
            />
            <span className="chart-tooltip-name">{entry.dataKey}</span>
            <span className="chart-tooltip-value">
              {(entry.value * 100).toFixed(1)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * trend: 后端返回的 { dimension, items: [{ item, points: [...] }] }
 * mode: 'have' | 'want'
 * selectedItems: 被选中的 item 名称数组
 * colorMap: { [itemName]: color }，在外面一开始就分配好的颜色
 */
export function TrendChart({ trend, mode, selectedItems, colorMap = {} }) {
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

  // 动态 Y 轴：比当前最高点略高一点（上浮 8%，最多到 100%）
  let maxValue = 0;
  data.forEach((row) => {
    seriesNames.forEach((name) => {
      const v = row[name];
      if (typeof v === 'number' && v > maxValue) {
        maxValue = v;
      }
    });
  });
  const yMax = maxValue === 0 ? 1 : Math.min(1, maxValue * 1.08);

  // 孤立点处理：前一年和后一年都没有数据时绘制点
  const isolatedPoints = new Set();
  if (data.length > 0) {
    seriesNames.forEach((name) => {
      for (let i = 0; i < data.length; i += 1) {
        const current = data[i][name];
        if (typeof current !== 'number') continue;

        const prev = i > 0 ? data[i - 1][name] : null;
        const next = i < data.length - 1 ? data[i + 1][name] : null;

        const hasPrev = typeof prev === 'number';
        const hasNext = typeof next === 'number';

        if (!hasPrev && !hasNext) {
          const year = data[i].year;
          isolatedPoints.add(`${name}::${year}`);
        }
      }
    });
  }

  const renderIsolatedDot = (props, color) => {
    const { cx, cy, payload, dataKey } = props;
    if (cx == null || cy == null) return null;

    const key = `${dataKey}::${payload.year}`;
    if (!isolatedPoints.has(key)) return null;

    return (
      <circle
        cx={cx}
        cy={cy}
        r={3.2}
        fill={color}
        stroke="#ffffff"
        strokeWidth={1.2}
      />
    );
  };

  return (
    <div className="chart-container chart-container-large">
      <div className="chart-inner-glass">
        <ResponsiveContainer>
          <LineChart
            data={data}
            margin={{ top: 18, right: 16, left: 0, bottom: 10 }}
          >
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="year"
              tickMargin={10}
              tick={{ fontSize: 12 }}
            />
            <YAxis
              domain={[0, yMax]}
              tickFormatter={(v) => `${Math.round(v * 100)}%`}
              tick={{ fontSize: 12 }}
            />
            <Tooltip content={<CustomTooltip />} />
            {/* 保留 Legend，只是透明 */}
            <Legend
              verticalAlign="top"
              height={32}
              iconType="circle"
              wrapperStyle={{
                paddingTop: 4,
                opacity: 0,
                pointerEvents: 'none',
              }}
            />

            {seriesNames.map((name) => {
              // 使用在一开始分配好的颜色；如果不存在就用一个兜底色
              const fallbackColor = TREND_COLORS[0];
              const color = colorMap[name] || fallbackColor;

              return (
                <Line
                  key={name}
                  type="monotone"
                  dataKey={name}
                  stroke={color}
                  strokeWidth={2.6}
                  dot={(props) => renderIsolatedDot(props, color)}
                  isAnimationActive
                  animationDuration={650}
                  animationEasing="ease-out"
                  connectNulls={false}
                />
              );
            })}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
