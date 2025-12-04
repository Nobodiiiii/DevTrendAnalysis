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
 * 获取某个维度的趋势。
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

  return safeFetchJson(url);
}
