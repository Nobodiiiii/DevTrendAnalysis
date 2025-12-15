// src/api/salary.js

const BASE_URL = 'http://localhost:8000';

async function safeFetchJson(url, options = {}) {
  const res = await fetch(url, {
    mode: 'cors',
    ...options,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status} - ${text || 'unexpected response'}`);
  }

  return res.json();
}

export async function fetchSalaryOverview() {
  const url = `${BASE_URL}/api/salary/overview`;
  return safeFetchJson(url);
}

export async function fetchSalaryOverviewByYear(year) {
  const search = year ? `?year=${encodeURIComponent(year)}` : '';
  const url = `${BASE_URL}/api/salary/overview${search}`;
  return safeFetchJson(url);
}

export async function fetchSalaryTimeline() {
  const url = `${BASE_URL}/api/salary/timeline`;
  return safeFetchJson(url);
}
