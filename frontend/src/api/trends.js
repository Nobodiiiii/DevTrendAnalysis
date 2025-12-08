// src/api/trends.js

// 后端基础地址
const BASE_URL = 'http://localhost:8000';

/**
 * 包装过的 fetch：在网络错误时自动重试一次，并给出更清晰的错误信息。
 */
async function safeFetchJson(url, options = {}, retry = 1) {
  try {
    const res = await fetch(url, {
      // 显式标明 CORS 模式
      mode: 'cors',
      ...options,
    });

    // 有响应但状态不是 2xx：抛出包含状态码的错误
    if (!res.ok) {
      const text = await res.text();
      throw new Error(
        `HTTP ${res.status} - ${text || 'Unexpected response from server'}`,
      );
    }

    return res.json();
  } catch (err) {
    // 网络层错误（包括被 CORS 拦截）：TypeError: Failed to fetch
    if (retry > 0) {
      console.warn('[safeFetchJson] 网络错误，重试一次:', err);
      return safeFetchJson(url, options, retry - 1);
    }
    console.error('[safeFetchJson] 最终失败:', err);
    throw new Error(
      err?.message?.includes('Failed to fetch')
        ? '网络连接异常，请确认后端服务是否在线或 CORS 配置是否正确'
        : err?.message || '请求失败',
    );
  }
}

/**
 * 找到“最近的一年”：
 * 先从当前年份（如 2025）往前找，直到有数据的那一年；
 * 如果都找不到（极端情况），就使用数据中最大的年份。
 *
 * @param {Array<{item: string, points: {year: number}[]}>} items
 * @returns {number | null}
 */
function findLatestYearWithData(items = []) {
  const yearSet = new Set();

  items.forEach(({ points = [] }) => {
    points.forEach((p) => {
      if (typeof p.year === 'number') {
        yearSet.add(p.year);
      }
    });
  });

  if (yearSet.size === 0) return null;

  const currentYear = new Date().getFullYear();

  // 从当前年往前找最近有数据的年份
  for (let y = currentYear; y >= 1970; y--) {
    if (yearSet.has(y)) {
      return y;
    }
  }

  // 兜底：如果上面的循环里没找到，就直接拿已有年份里的最大值
  return Math.max(...yearSet);
}

/**
 * 按“最近的一年”的 have_ratio（使用率）从高到低排序 items。
 *
 * @param {{ dimension: string, items: Array<{ item: string, points: Array<{year:number, have_ratio:number}> }> }} data
 * @returns 同结构的已排序数据
 */
function sortItemsByLatestYearUsage(data) {
  if (!data || !Array.isArray(data.items) || data.items.length === 0) {
    return data;
  }

  const targetYear = findLatestYearWithData(data.items);
  if (targetYear == null) return data;

  const sortedItems = [...data.items].sort((a, b) => {
    const aPoint = (a.points || []).find((p) => p.year === targetYear);
    const bPoint = (b.points || []).find((p) => p.year === targetYear);

    const aRatio = aPoint?.have_ratio ?? 0;
    const bRatio = bPoint?.have_ratio ?? 0;

    // 按使用率从高到低
    return bRatio - aRatio;
  });

  return {
    ...data,
    items: sortedItems,
  };
}

/**
 * 获取某个维度的趋势，并按“最近一年最高使用率”对 items 排序。
 *
 * @param {string} dimension - 'language' | 'database' | ...
 * @param {string[]} items   - 技术项名称列表；为空则由后端返回最近一年 Top N
 * @param {number} limit     - items 为空时生效，默认 24
 */
export async function fetchTrends(dimension, items = [], limit = 24) {
  const params = new URLSearchParams();

  if (items.length > 0) {
    items.forEach((item) => params.append('items', item));
  } else {
    params.set('limit', String(limit));
  }

  const url = `${BASE_URL}/api/trends/${dimension}?${params.toString()}`;
  console.debug('[fetchTrends] →', url);

  const rawData = await safeFetchJson(url);

  // 在这里对获取到的数据进行排序后再返回
  const sorted = sortItemsByLatestYearUsage(rawData);
  console.debug('[fetchTrends] 排序后的数据最近年份为:', findLatestYearWithData(sorted.items));

  return sorted;
}
