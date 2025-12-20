import React, { useMemo, useRef, useState } from 'react';
import '../styles/personal-advice.css';

// ✅ 语言（2025 特供，按 Have 从高到低）
const LANGUAGE_OPTIONS = [
  'JavaScript',
  'HTML/CSS',
  'SQL',
  'Python',
  'Bash/Shell',
  'TypeScript',
  'Java',
  'C#',
  'C++',
  'PowerShell',
  'C',
  'PHP',
  'Go',
  'Rust',
  'Kotlin',
  'Lua',
  'Assembly',
  'Ruby',
  'Dart',
  'Swift',
  'R',
  'Groovy',
  'VB.NET',
  'VB6',
  'Delphi/Object Pascal',
  'Elixir',
  'Lisp',
  'MATLAB',
  'Perl',
  'GDScript',
  'MicroPython',
  'Scala',
  'F#',
  'Ada',
  'Fortran',
  'Erlang',
  'OCaml',
  'Prolog',
  'Gleam',
  'COBOL',
  'Zig',
  'Mojo',
];

// ✅ 数据库（2025 特供，按 Have 从高到低）
const DATABASE_OPTIONS = [
  'PostgreSQL',
  'MySQL',
  'SQLite',
  'Microsoft SQL Server',
  'Redis',
  'MongoDB',
  'MariaDB',
  'Oracle',
  'Amazon DynamoDB',
  'BigQuery',
  'Supabase',
  'Cloud Firestore',
  'Microsoft Access',
  'H2',
  'Firebase Realtime Database',
  'Snowflake',
  'CosmosDB',
  'Elasticsearch',
  'InfluxDB',
  'Databricks SQL',
  'DuckDB',
  'Neo4j',
  'Cassandra',
  'Pocketbase',
  'CockroachDB',
  'Valkey',
  'Clickhouse',
  'IBM Db2',
  'Amazon Redshift',
  'Datomic',
];

// ✅ Web/框架（2025 特供，按 Have 从高到低）
const WEBFRAME_OPTIONS = [
  'Node.js',
  'React',
  'jQuery',
  'Next.js',
  'Express',
  'ASP.NET Core',
  'Angular',
  'Vue.js',
  'ASP.NET',
  'FastAPI',
  'Spring',
  'Flask',
  'WordPress',
  'Django',
  'Laravel',
  'Astro',
  'AngularJS',
  'Svelte',
  'Blazor',
  'NestJS',
  'Ruby on Rails',
  'Symfony',
  'Deno',
  'Axum',
  'Fastify',
  'Phoenix',
  'Nuxt.js',
  'Drupal',
];

// ✅ 平台/工具（2025 特供，按 Have 从高到低）
const PLATFORM_OPTIONS = [
  'Docker',
  'npm',
  'Amazon Web Services (AWS)',
  'Pip',
  'Homebrew',
  'Kubernetes',
  'Microsoft Azure',
  'Google Cloud',
  'Terraform',
  'Vercel',
  'Vite',
  'Webpack',
  'Yarn',
  'pnpm',
  'Cloudflare',
  'Netlify',
  'Firebase',
  'DigitalOcean',
  'Heroku',
  'Fly.io',
  'Supabase',
  'VMware',
  'Hetzner',
  'Linode',
  'Render',
  'Vultr',
  'OVHcloud',
  'Managed Kubernetes',
  'Podman',
  'OpenShift',
  'Corepack',
  'OpenStack',
  'Colocation',
];

const SALARY_BAND_OPTIONS = [
  '暂不透露',
  '< 20 万 / 年',
  '20–30 万 / 年',
  '30–50 万 / 年',
  '50–80 万 / 年',
  '> 80 万 / 年',
];

const CAREER_TRACK_OPTIONS = [
  '前端开发',
  '后端开发',
  '全栈开发',
  '测试 / QA',
  '数据工程',
  '算法 / AI',
  '移动端开发',
  'DevOps / SRE',
  '暂未确定',
];



// =========================
// 建议区渲染：更像人话 + 图表
// =========================

const fmtMoney = (n) => {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return '-';
  try {
    return `¥${Number(n).toLocaleString('zh-CN', { maximumFractionDigits: 0 })}`;
  } catch {
    return `¥${Math.round(Number(n))}`;
  }
};

const fmtPct = (x) => {
  if (x === null || x === undefined || Number.isNaN(Number(x))) return '-';
  return `${Math.round(Number(x) * 100)}%`;
};

const renderInlineBold = (text) => {
  // 把 **bold** 变成 <strong>
  const parts = String(text || '').split(/\*\*(.*?)\*\*/g);
  return parts.map((p, idx) =>
    idx % 2 === 1 ? (
      <strong key={idx}>{p}</strong>
    ) : (
      <React.Fragment key={idx}>{p}</React.Fragment>
    )
  );
};

const RichTextBlock = ({ text }) => {
  const lines = String(text || '').split(/\n/).filter((l) => l !== null && l !== undefined);
  const nodes = [];
  let list = [];

  const flushList = () => {
    if (!list.length) return;
    nodes.push(
      <ul className="advice-rt-list" key={`ul-${nodes.length}`}>
        {list.map((it, idx) => (
          <li key={idx}>{renderInlineBold(it)}</li>
        ))}
      </ul>
    );
    list = [];
  };

  lines.forEach((raw, idx) => {
    const line = raw.trimEnd();

    if (!line) {
      flushList();
      nodes.push(<div className="advice-rt-spacer" key={`sp-${idx}`} />);
      return;
    }

    // 标题：**xxx**
    const head = line.match(/^\*\*(.+?)\*\*$/);
    if (head) {
      flushList();
      nodes.push(
        <h4 className="advice-rt-h" key={`h-${idx}`}>
          {head[1]}
        </h4>
      );
      return;
    }

    // 列表：- xxx
    if (line.startsWith('- ')) {
      list.push(line.slice(2).trim());
      return;
    }

    flushList();
    nodes.push(
      <p className="advice-rt-p" key={`p-${idx}`}>
        {renderInlineBold(line)}
      </p>
    );
  });

  flushList();
  return <div className="advice-rt">{nodes}</div>;
};

const SalaryPercentileChart = ({ salary }) => {
  if (!salary) return null;
  const p25 = Number(salary.p25);
  const p50 = Number(salary.p50);
  const p75 = Number(salary.p75);
  const p90 = Number(salary.p90);
  if (![p25, p50, p75, p90].every((v) => Number.isFinite(v))) return null;

  // 计算用户薪资区间（如果有）
  const userBand = salary.userSalaryBand;
  const userLo = userBand?.loCny;
  const userHi = userBand?.hiCny;

  const min = Math.min(p25, p50, p75, p90, userLo || p25, userHi || p25);
  const max = Math.max(p25, p50, p75, p90, userLo || p90, userHi || p90);
  const pad = (max - min) * 0.08;
  const domainMin = min - pad;
  const domainMax = max + pad;

  const x = (v, w) => {
    const t = (v - domainMin) / (domainMax - domainMin || 1);
    return Math.max(0, Math.min(w, t * w));
  };

  const W = 520;
  const H = 70;
  const y = 34;

  // 映射口径到友好文字
  const getLevelText = (level) => {
    if (level.includes('L1')) return '精准对标';
    if (level.includes('L2')) return '较精准';
    if (level.includes('L3')) return '宽泛对标';
    if (level.includes('L4')) return '粗略对标';
    return '口径未知';
  };

  return (
    <div className="advice-viz-card">
      <div className="advice-viz-head">
        <div>
          <div className="advice-eyebrow">Salary · Percentiles</div>
          <h3 className="advice-card-title">薪资分布（同类人群参考）</h3>
          <div className="advice-viz-subtitle">
            可信度 {salary.confidence} · {getLevelText(salary.level)} · {salary.fx}
            <br />
            P 表示百分位数：P50 意为有 50% 的人薪资低于此值，P75 则表示超过 75% 的人。
          </div>
        </div>
        <div className="advice-viz-meta">
          <span className="advice-viz-pill">P50 {fmtMoney(p50)}</span>
          <span className="advice-viz-pill">P75 {fmtMoney(p75)}</span>
        </div>
      </div>

      <svg viewBox={`0 0 ${W} ${H}`} className="advice-salary-chart" role="img" aria-label="Salary percentiles">
        {/* baseline */}
        <line x1="20" y1={y} x2={W - 20} y2={y} className="advice-salary-line" />

        {/* 用户薪资区间高亮（如果有任一边界） */}
        {(userLo !== null || userHi !== null) && (
          <rect
            x={20 + x(userLo !== null ? userLo : domainMin, W - 40)}
            y={y - 10}
            width={Math.max(2, x(userHi !== null ? userHi : domainMax, W - 40) - x(userLo !== null ? userLo : domainMin, W - 40))}
            height="20"
            rx="4"
            className="advice-salary-user-range"
            opacity="0.15"
          />
        )}

        {/* range bar P25-P90 */}
        <rect
          x={20 + x(p25, W - 40)}
          y={y - 6}
          width={Math.max(2, x(p90, W - 40) - x(p25, W - 40))}
          height="12"
          rx="6"
          className="advice-salary-range"
        />

        {/* markers */}
        {[{ v: p25, k: 'P25' }, { v: p50, k: 'P50' }, { v: p75, k: 'P75' }, { v: p90, k: 'P90' }].map((it) => (
          <g key={it.k} transform={`translate(${20 + x(it.v, W - 40)}, ${y})`}>
            <circle r="6" className={it.k === 'P50' ? 'advice-salary-dot advice-salary-dot-mid' : 'advice-salary-dot'} />
            <text y="-14" textAnchor="middle" className="advice-salary-label">
              {it.k}
            </text>
            <text y="22" textAnchor="middle" className="advice-salary-value">
              {fmtMoney(it.v)}
            </text>
          </g>
        ))}

        {/* 用户薪资区间标记（分别渲染左右边界，出界时渲染到顶端） */}
        {userLo !== null && (
          <line
            x1={userLo < domainMin ? 20 : 20 + x(userLo, W - 40)}
            y1={y - 10}
            x2={userLo < domainMin ? 20 : 20 + x(userLo, W - 40)}
            y2={y + 10}
            stroke="rgba(59, 130, 246, 0.6)"
            strokeWidth="2"
            strokeDasharray="2,2"
          />
        )}
        {userHi !== null && (
          <line
            x1={userHi > domainMax ? W - 20 : 20 + x(userHi, W - 40)}
            y1={y - 10}
            x2={userHi > domainMax ? W - 20 : 20 + x(userHi, W - 40)}
            y2={y + 10}
            stroke="rgba(59, 130, 246, 0.6)"
            strokeWidth="2"
            strokeDasharray="2,2"
          />
        )}
        {(userLo !== null || userHi !== null) && (() => {
          // 计算"你的区间"文字位置：取实际边界的中间位置
          const loX = userLo !== null ? (userLo < domainMin ? 20 : 20 + x(userLo, W - 40)) : 20;
          const hiX = userHi !== null ? (userHi > domainMax ? W - 20 : 20 + x(userHi, W - 40)) : W - 20;
          const midX = (loX + hiX) / 2;
          return (
            <text
              x={midX}
              y={y - 16}
              textAnchor="middle"
              className="advice-salary-user-label"
              fill="rgba(59, 130, 246, 1)"
              fontSize="11"
              fontWeight="600"
            >
              你的区间
            </text>
          );
        })()}
      </svg>
    </div>
  );
};

const TechRecoBars = ({ title, items }) => {
  if (!items?.length) return null;

  return (
    <div className="advice-tech-reco-category">
      <div className="advice-tech-reco-category-title">{title}</div>
      {items.map((it) => {
        const want = Number(it.want);
        const have = Number(it.have);
        const gap = Number(it.gap);

        return (
          <div className="advice-tech-reco-item" key={it.tech}>
            <div className="advice-tech-reco-item-head">
              <span className="advice-tech-reco-tech">{it.tech}</span>
              {gap > 0 && <span className="advice-tech-reco-gap">gap+{fmtPct(gap)}</span>}
            </div>
            <div className="advice-tech-reco-item-detail">
              Want {fmtPct(want)} · Have {fmtPct(have)}
            </div>
          </div>
        );
      })}
    </div>
  );
};

// 进阶建议组件
const AdvancementCard = ({ advancement }) => {
  if (!advancement || !advancement.available) return null;

  const { currentLevel, targetLevel, language, database, webframe, platform } = advancement;

  const hasItems = language?.length > 0 || database?.length > 0 || webframe?.length > 0 || platform?.length > 0;
  if (!hasItems) return null;

  const renderItems = (items, category) => {
    if (!items?.length) return null;
    return (
      <div className="advice-adv-category">
        <div className="advice-adv-category-title">{category}</div>
        {items.map((item) => (
          <div className="advice-adv-item" key={item.tech}>
            <div className="advice-adv-item-head">
              <span className="advice-adv-tech">{item.tech}</span>
              <span className="advice-adv-lift">+{fmtPct(item.lift)}</span>
            </div>
            <div className="advice-adv-item-detail">
              进阶人群 {fmtPct(item.targetHave)} vs 当前 {fmtPct(item.currentHave)}
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="advice-viz-card advice-adv-card">
      <div className="advice-viz-head">
        <div>
          <div className="advice-eyebrow">Advancement · Career Path</div>
          <h3 className="advice-card-title">想提薪？这些技术值得学</h3>
          <div className="advice-viz-subtitle">
            从 <strong>{currentLevel} 年</strong> 进阶到 <strong>{targetLevel} 年</strong>，这些技术在进阶人群中更普及
          </div>
        </div>
      </div>

      <div className="advice-adv-grid">
        {renderItems(language, '语言')}
        {renderItems(database, '数据库')}
        {renderItems(webframe, '框架')}
        {renderItems(platform, '平台/工具')}
      </div>
    </div>
  );
};

// 高薪vs低薪技术差异组件
const SalaryTierTechCard = ({ salaryTierTech }) => {
  if (!salaryTierTech || !salaryTierTech.available) return null;

  const { language, database, webframe, platform } = salaryTierTech;

  const hasMissingItems =
    language?.missing?.length > 0 ||
    database?.missing?.length > 0 ||
    webframe?.missing?.length > 0 ||
    platform?.missing?.length > 0;

  if (!hasMissingItems) return null;

  const renderMissingItems = (items, category) => {
    if (!items?.length) return null;
    return (
      <div className="advice-salary-tier-category">
        <div className="advice-salary-tier-category-title">{category}</div>
        {items.map((item) => (
          <div className="advice-salary-tier-item" key={item.tech}>
            <div className="advice-salary-tier-item-head">
              <span className="advice-salary-tier-tech">{item.tech}</span>
              <span className="advice-salary-tier-diff">+{fmtPct(item.diff)}</span>
            </div>
            <div className="advice-salary-tier-item-detail">
              高薪 {fmtPct(item.highHave)} vs 低薪 {fmtPct(item.lowHave)}
            </div>
          </div>
        ))}
      </div>
    );
  };

  const renderHasItems = (items, category) => {
    if (!items?.length) return null;
    return (
      <div className="advice-salary-tier-has">
        <span className="advice-salary-tier-has-label">{category}已掌握：</span>
        {items.map((item, idx) => (
          <span key={item.tech} className="advice-salary-tier-has-tech">
            {item.tech}
            {idx < items.length - 1 ? '、' : ''}
          </span>
        ))}
      </div>
    );
  };

  const hasUserItems =
    language?.has?.length > 0 ||
    database?.has?.length > 0 ||
    webframe?.has?.length > 0 ||
    platform?.has?.length > 0;

  return (
    <div className="advice-viz-card advice-salary-tier-card">
      <div className="advice-viz-head">
        <div>
          <div className="advice-eyebrow">Salary Tier · High vs Low</div>
          <h3 className="advice-card-title">高薪人群的技术密码</h3>
          <div className="advice-viz-subtitle">
            以下技术在 <strong>高薪人群（&gt;P75）</strong> 中的普及率显著高于 <strong>低薪人群（&lt;P25）</strong>
          </div>
        </div>
      </div>

      <div className="advice-salary-tier-grid">
        {renderMissingItems(language?.missing, '语言')}
        {renderMissingItems(database?.missing, '数据库')}
        {renderMissingItems(webframe?.missing, '框架')}
        {renderMissingItems(platform?.missing, '平台/工具')}
      </div>

      {hasUserItems && (
        <div className="advice-salary-tier-has-section">
          <div className="advice-salary-tier-has-title">你已掌握的高薪技术</div>
          {renderHasItems(language?.has, '语言')}
          {renderHasItems(database?.has, '数据库')}
          {renderHasItems(webframe?.has, '框架')}
          {renderHasItems(platform?.has, '平台/工具')}
        </div>
      )}
    </div>
  );
};

const AdviceDataView = ({ analysisText, adviceData }) => {
  const salary = adviceData?.salary || null;
  const tech = adviceData?.tech || null;
  const advancement = adviceData?.advancement || null;
  const salaryTierTech = adviceData?.salaryTierTech || null;

  // 如果没有结构化数据，就退回文本
  if (!salary && !tech) {
    return <RichTextBlock text={analysisText} />;
  }

  // 映射口径到友好文字
  const getLevelText = (level) => {
    if (level.includes('T1')) return '精准';
    if (level.includes('T2')) return '较精准';
    if (level.includes('T3')) return '宽泛';
    if (level.includes('T4')) return '粗略';
    return '未知';
  };

  return (
    <div className="advice-output">
      {salary ? <SalaryPercentileChart salary={salary} /> : null}

      {/* 进阶建议 */}
      <AdvancementCard advancement={advancement} />

      {/* 高薪vs低薪技术差异 */}
      <SalaryTierTechCard salaryTierTech={salaryTierTech} />

      {/* 技术栈建议（市场需求信号） */}
      {tech ? (
        <div className="advice-viz-card advice-tech-card">
          <div className="advice-viz-head">
            <div>
              <div className="advice-eyebrow">Stack · Market Signals</div>
              <h3 className="advice-card-title">技术栈建议（市场需求信号）</h3>
              <div className="advice-viz-subtitle">
                <strong>Want</strong> 想用占比 · <strong>Have</strong> 在用占比 · <strong>Gap</strong> 需求缺口 = Want - Have
                <br />
                对标精准度：语言 {getLevelText(tech.cohort?.levels?.language)} · 数据库 {getLevelText(tech.cohort?.levels?.database)} · 框架 {getLevelText(tech.cohort?.levels?.webframe)} · 平台 {getLevelText(tech.cohort?.levels?.platform)}
              </div>
            </div>
          </div>

          <div className="advice-tech-reco-grid">
            <div className="advice-tech-reco-col">
              <div className="advice-tech-reco-col-title">语言</div>
              <TechRecoBars title="主流地基（更稳）" items={tech.language?.mainstream} />
              <TechRecoBars title="潜力加分（更亮）" items={tech.language?.gap} />
            </div>
            <div className="advice-tech-reco-col">
              <div className="advice-tech-reco-col-title">数据库</div>
              <TechRecoBars title="主流地基（更稳）" items={tech.database?.mainstream} />
              <TechRecoBars title="潜力加分（更亮）" items={tech.database?.gap} />
            </div>
            <div className="advice-tech-reco-col">
              <div className="advice-tech-reco-col-title">框架</div>
              <TechRecoBars title="主流地基（更稳）" items={tech.webframe?.mainstream} />
              <TechRecoBars title="潜力加分（更亮）" items={tech.webframe?.gap} />
            </div>
            <div className="advice-tech-reco-col">
              <div className="advice-tech-reco-col-title">平台/工具</div>
              <TechRecoBars title="主流地基（更稳）" items={tech.platform?.mainstream} />
              <TechRecoBars title="潜力加分（更亮）" items={tech.platform?.gap} />
            </div>
          </div>
        </div>
      ) : null}

      <details className="advice-details">
        <summary>查看完整分析文本</summary>
        <RichTextBlock text={analysisText} />
      </details>
    </div>
  );
};

const AdviceChecklist = ({ text }) => {
  const items = String(text || '')
    .split(/\n/)
    .map((l) => l.trim())
    .filter((l) => l.startsWith('- '))
    .map((l) => l.slice(2).trim());

  if (!items.length) return <RichTextBlock text={text} />;

  return (
    <div className="advice-checklist">
      {items.map((it, idx) => (
        <label className="advice-checkitem" key={idx}>
          <input type="checkbox" />
          <span>{renderInlineBold(it)}</span>
        </label>
      ))}
    </div>
  );
};

const PersonalAdvice = () => {
  const [techStack, setTechStack] = useState({
    languages: [],
    webframes: [],
    databases: [],
    platforms: [],
  });

  // 身份与预期信息
  const [profileType, setProfileType] = useState(''); // 'student' | 'professional'

  const [studentProfile, setStudentProfile] = useState({
    age: '',
    expectedSalaryBand: '',
    expectedTrack: '',
  });

  const [proProfile, setProProfile] = useState({
    years: '',
    salaryBand: '',
    track: '',
  });

  // 其他补充信息
  const [otherInfo, setOtherInfo] = useState({
    consentShare: '',
    isTruthful: '',
    note: '',
  });

  // 建议区内容：后端返回的数据
  const [adviceData, setAdviceData] = useState(null);

  const [hasGenerated, setHasGenerated] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generateError, setGenerateError] = useState('');

  // ✅ toast（本地实现，不依赖第三方库）
  const [toast, setToast] = useState({ open: false, message: '', type: 'error' });
  const toastTimerRef = useRef(null);

  const showToast = (message, type = 'error', duration = 2400) => {
    if (toastTimerRef.current) {
      clearTimeout(toastTimerRef.current);
      toastTimerRef.current = null;
    }
    setToast({ open: true, message, type });
    toastTimerRef.current = setTimeout(() => {
      setToast((prev) => ({ ...prev, open: false }));
    }, duration);
  };

  const emptyHint = useMemo(() => '点击右上方生成建议按钮生成。', []);

  // ✅ 文本生成函数：将后端返回的数据转换为用户友好的文本
  const generateAnalysisText = useMemo(() => {
    if (!adviceData) return '';

    const { userProfile, salary, tech } = adviceData;
    const lines = [];

    // 1. 用户画像
    lines.push('**你现在的画像（用来做对标和建议）**');
    lines.push(`- 方向：${userProfile.devtypeFamily}（由你选择的岗位方向映射）`);
    lines.push(`- 经验：${userProfile.workexpBin} 年（按区间归档）`);
    lines.push('');

    // 2. 薪资对标
    lines.push('**薪资对标（市场参考）**');
    if (!salary) {
      lines.push('- 暂时没拿到薪资基准数据（可能是数据未生成或口径命中失败）。');
    } else {
      lines.push(
        `- 同类人群年薪大致在 **${fmtMoney(salary.p25)}（P25）— ${fmtMoney(salary.p90)}（P90）** 之间；` +
        `中位数 P50 约 **${fmtMoney(salary.p50)}**。`
      );
      lines.push(
        `- 参考口径：样本 n=${salary.n}（可信度：${salary.confidence}），对标粒度=${salary.level}，汇率口径=${salary.fx}。`
      );

      if (salary.isMarketRef) {
        lines.push('- 你当前为学生：这里对标的是"入门在职人群"的市场分布，用来帮你定预期（不是对你当下收入的判断）。');
      }

      if (salary.userSalaryBand) {
        const band = salary.userSalaryBand;
        lines.push(`- 你填写的薪资区间：**${band.text}**`);

        if (band.loCny !== null || band.hiCny !== null) {
          const loUsd = band.loUsd;
          const hiUsd = band.hiUsd;
          const p25Usd = salary.p25Usd;
          const p50Usd = salary.p50Usd;
          const p75Usd = salary.p75Usd;

          let hint = '';
          if (hiUsd !== null && hiUsd <= p25Usd) {
            hint = '整体偏保守（上沿都低于 P25）。';
          } else if (loUsd !== null && loUsd >= p75Usd) {
            hint = '整体偏进取（下沿已接近/高于 P75）。';
          } else if (loUsd !== null && hiUsd !== null) {
            if (hiUsd <= p50Usd) {
              hint = '大概率落在 P50 以下。';
            } else if (loUsd >= p50Usd) {
              hint = '大概率落在 P50 以上。';
            } else {
              hint = '和 P50/P75 有重叠：更看项目深度、匹配度和面试发挥。';
            }
          }

          if (hint) {
            lines.push(`- 这档预期怎么看：${hint}`);
          }
        }
      }
    }

    lines.push('');
    lines.push('**技术栈怎么补（更像面试官能听懂的说法）**');
    lines.push('- 先把"主流地基"补齐：让你能更稳定地拿到面试机会、也更容易做出可讲的项目。');
    lines.push('- 再选 1 个"潜力加分"深挖：让你的简历有亮点，但不至于太分散。');

    // 3. 技术栈建议
    const hasAnyRecos =
      tech.language.mainstream.length > 0 || tech.language.gap.length > 0 ||
      tech.database.mainstream.length > 0 || tech.database.gap.length > 0 ||
      tech.webframe.mainstream.length > 0 || tech.webframe.gap.length > 0 ||
      tech.platform?.mainstream?.length > 0 || tech.platform?.gap?.length > 0;

    if (!hasAnyRecos) {
      lines.push('');
      lines.push('- 你已选的栈覆盖度很高，或者同类样本很分散：建议直接对齐目标岗位 JD，补齐 **1 个主栈 + 1 个数据库 + 1 个框架 + 1 个平台/工具** 的"可讲闭环项目"。');
    }

    // 已选技术的普及度
    const hasChosen = tech.language.chosen.length > 0 || tech.database.chosen.length > 0 || tech.webframe.chosen.length > 0 || tech.platform?.chosen?.length > 0;
    if (hasChosen) {
      lines.push('');
      lines.push('**你已选技术在同类人群中的普及度（参考）**');
      if (tech.language.chosen.length > 0) {
        lines.push('语言：');
        tech.language.chosen.forEach(item => {
          lines.push(`- ${item.tech}（在该统计口径中 have≈${fmtPct(item.have)}）`);
        });
      }
      if (tech.database.chosen.length > 0) {
        lines.push('数据库：');
        tech.database.chosen.forEach(item => {
          lines.push(`- ${item.tech}（在该统计口径中 have≈${fmtPct(item.have)}）`);
        });
      }
      if (tech.webframe.chosen.length > 0) {
        lines.push('框架：');
        tech.webframe.chosen.forEach(item => {
          lines.push(`- ${item.tech}（在该统计口径中 have≈${fmtPct(item.have)}）`);
        });
      }
      if (tech.platform?.chosen?.length > 0) {
        lines.push('平台/工具：');
        tech.platform.chosen.forEach(item => {
          lines.push(`- ${item.tech}（在该统计口径中 have≈${fmtPct(item.have)}）`);
        });
      }
    }

    return lines.join('\n');
  }, [adviceData]);

  const generateAiSummary = useMemo(() => {
    if (!adviceData) return '';

    const { salary } = adviceData;
    const lines = [];

    lines.push('**下一步建议（直接照做版）**');

    if (salary) {
      lines.push(`- 薪资目标：先把预期对齐到 **P50（约 ${fmtMoney(salary.p50)}/年）**，有强项目再冲 **P75（约 ${fmtMoney(salary.p75)}/年）**。`);
    }

    lines.push('- 项目打法：用 1 个主项目把"选型 → 方案 → 结果"讲完整（最好能量化：性能/成本/转化/稳定性）。');
    lines.push('- 技术策略：主流地基选 2–3 个稳住面试，通过后再用 1 个加分项拉开差距。');
    lines.push('- 面试表达：用 STAR（背景-任务-行动-结果）把故事讲短讲清，避免只堆技术名词。');

    return lines.join('\n');
  }, [adviceData]);

  const handleTechToggle = (group, value) => {
    setTechStack((prev) => {
      const current = prev[group] || [];
      const exists = current.includes(value);
      return {
        ...prev,
        [group]: exists ? current.filter((v) => v !== value) : [...current, value],
      };
    });
  };

  const handleStudentChange = (field, value) => {
    setStudentProfile((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleProChange = (field, value) => {
    setProProfile((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleOtherChange = (field, value) => {
    setOtherInfo((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const isStudentActive = profileType === 'student';
  const isProfessionalActive = profileType === 'professional';

  // ✅ 校验 payload 各部分不为空：为空则 toast 提示
  const validateBeforeGenerate = () => {
    const missing = [];

    // 技术栈四块都要有选择
    if (!techStack.languages?.length) missing.push('语言/基础能力掌握情况');
    if (!techStack.databases?.length) missing.push('数据库掌握情况');
    if (!techStack.webframes?.length) missing.push('Web/框架掌握情况');
    if (!techStack.platforms?.length) missing.push('平台/工具/云服务掌握情况');

    // 身份必须选
    if (!profileType) {
      missing.push('身份选择');
    } else if (profileType === 'student') {
      if (!String(studentProfile.age || '').trim()) missing.push('学生-年龄');
      if (!String(studentProfile.expectedSalaryBand || '').trim()) missing.push('学生-期望薪资区间');
      if (!String(studentProfile.expectedTrack || '').trim()) missing.push('学生-期望方向');
    } else if (profileType === 'professional') {
      if (!String(proProfile.years || '').trim()) missing.push('从业者-工作年份');
      if (!String(proProfile.salaryBand || '').trim()) missing.push('从业者-当前薪资区间');
      if (!String(proProfile.track || '').trim()) missing.push('从业者-方向');
    }

    // 额外内容（note 允许为空；其他两项建议必填）
    if (!String(otherInfo.consentShare || '').trim()) missing.push('是否愿意分享数据');
    if (!String(otherInfo.isTruthful || '').trim()) missing.push('信息真实程度');

    if (missing.length > 0) {
      showToast(`请先填写：${missing[0]}`);
      return false;
    }
    return true;
  };

  // ✅ 预留：调用后端接口生成建议（带校验）
  const handleGenerateFromBackend = async () => {
    // 1) 校验 payload
    if (!validateBeforeGenerate()) return;

    // 2) 再进入生成逻辑
    setIsGenerating(true);
    setGenerateError('');

    try {
      const payload = {
        techStack,
        profileType,
        studentProfile,
        proProfile,
        otherInfo,
      };

      const resp = await fetch('/api/advises/personal-advice/generate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
      });

      console.log(payload);

      if (!resp.ok) {
        const errText = await resp.text().catch(() => '');
        throw new Error(errText || 'Request failed');
      }
      const data = await resp.json();
      setAdviceData(data);

      setHasGenerated(true);
    } catch (err) {
      setGenerateError('生成失败，请稍后重试。');
      showToast('生成失败，请稍后重试。');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="advice-page">
      {/* toast */}
      <div
        className={[
          'advice-toast',
          toast.open ? 'advice-toast-show' : '',
          toast.type === 'success' ? 'advice-toast-success' : 'advice-toast-error',
        ].join(' ')}
        role="status"
        aria-live="polite"
      >
        {toast.message}
      </div>

      {/* 1. 介绍区域 */}
      <section className="advice-hero">
        <div className="advice-hero-card">
          <p className="advice-hero-kicker">Module 03</p>
          <h1 className="advice-hero-title">
            个人建议
            <span className="advice-hero-highlight"> · Personal Guidance</span>
          </h1>
          <p className="advice-hero-subtitle">
            这一页不是一个「打分表」，而是帮你把当下的技术栈、薪资期望和职业目标整理成一张可以对话的画像。
            填写完成后，建议区将由后端服务生成更个性化的路线和提示。
          </p>
          <div className="advice-hero-meta">
            <span>用途：职业定位 & 薪资对齐</span>
            <span>输入：当前技术栈 + 个人偏好</span>
            <span>输出：下一步路线与沟通语言</span>
          </div>
        </div>
      </section>

      {/* 2. 技术问卷区 */}
      <section className="advice-section">
        <div className="advice-section-header">
          <h2>技术栈自画像</h2>
          <p>
            从<strong>已经比较熟悉、敢在简历和面试中拿出来讲</strong>的技术开始勾选，只要足够代表你现在的技术形象即可。
          </p>
        </div>

        <div className="advice-tech-grid">
          {/* 语言 */}
          <div className="advice-card">
            <div className="advice-card-header">
              <div>
                <div className="advice-eyebrow">Stack · Language</div>
                <h3 className="advice-card-title">主力语言 / 基础能力</h3>
              </div>
              <span className="advice-chip">已选 {techStack.languages.length} 项</span>
            </div>
            <p className="advice-card-subtitle">按顺序勾选你当前最常用/最有把握的项。</p>
            <div className="advice-options-grid">
              {LANGUAGE_OPTIONS.map((lang) => {
                const checked = techStack.languages.includes(lang);
                return (
                  <label
                    key={lang}
                    className={`advice-option-pill ${checked ? 'advice-option-pill-active' : ''}`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => handleTechToggle('languages', lang)}
                    />
                    <span>{lang}</span>
                  </label>
                );
              })}
            </div>
          </div>

          {/* 数据库 */}
          <div className="advice-card">
            <div className="advice-card-header">
              <div>
                <div className="advice-eyebrow">Stack · Database</div>
                <h3 className="advice-card-title">数据库与数据存储</h3>
              </div>
              <span className="advice-chip">已选 {techStack.databases.length} 项</span>
            </div>
            <p className="advice-card-subtitle">选择你能独立完成基本建模、查询、索引或落库方案的数据库。</p>
            <div className="advice-options-grid">
              {DATABASE_OPTIONS.map((db) => {
                const checked = techStack.databases.includes(db);
                return (
                  <label
                    key={db}
                    className={`advice-option-pill ${checked ? 'advice-option-pill-active' : ''}`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => handleTechToggle('databases', db)}
                    />
                    <span>{db}</span>
                  </label>
                );
              })}
            </div>
          </div>

          {/* Web/框架 */}
          <div className="advice-card">
            <div className="advice-card-header">
              <div>
                <div className="advice-eyebrow">Stack · Framework</div>
                <h3 className="advice-card-title">Web / 框架 / 平台</h3>
              </div>
              <span className="advice-chip">已选 {techStack.webframes.length} 项</span>
            </div>
            <p className="advice-card-subtitle">选择你能独立完成一个典型业务模块/接口/页面的框架或平台。</p>
            <div className="advice-options-grid">
              {WEBFRAME_OPTIONS.map((fw) => {
                const checked = techStack.webframes.includes(fw);
                return (
                  <label
                    key={fw}
                    className={`advice-option-pill ${checked ? 'advice-option-pill-active' : ''}`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => handleTechToggle('webframes', fw)}
                    />
                    <span>{fw}</span>
                  </label>
                );
              })}
            </div>
          </div>

          {/* 平台/工具 */}
          <div className="advice-card">
            <div className="advice-card-header">
              <div>
                <div className="advice-eyebrow">Stack · Platform</div>
                <h3 className="advice-card-title">平台 / 工具 / 云服务</h3>
              </div>
              <span className="advice-chip">已选 {techStack.platforms.length} 项</span>
            </div>
            <p className="advice-card-subtitle">选择你能独立完成部署、配置或日常使用的平台与工具。</p>
            <div className="advice-options-grid">
              {PLATFORM_OPTIONS.map((p) => {
                const checked = techStack.platforms.includes(p);
                return (
                  <label
                    key={p}
                    className={`advice-option-pill ${checked ? 'advice-option-pill-active' : ''}`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => handleTechToggle('platforms', p)}
                    />
                    <span>{p}</span>
                  </label>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      {/* 3. 身份与预期 */}
      <section className="advice-section">
        <div className="advice-section-header">
          <h2>身份与预期</h2>
          <p>先确认你当前处在学生还是在职阶段。点击卡片以选择。</p>
        </div>

        <div className="advice-role-grid">
          {/* 学生卡片 */}
          <div
            className={
              'advice-card advice-role-card ' +
              (isStudentActive ? 'advice-role-card-selected' : isProfessionalActive ? 'advice-role-card-dimmed' : '')
            }
            onClick={() => setProfileType('student')}
          >
            <div className="advice-card-header">
              <div>
                <div className="advice-eyebrow">Profile · Student</div>
                <h3 className="advice-card-title">我是学生 / 准毕业生</h3>
              </div>
              <div className="advice-role-pill">{isStudentActive ? '已选择' : '点击选择'}</div>
            </div>

            <div className="advice-role-fields" onClick={(e) => e.stopPropagation()}>
              <div className="advice-field">
                <label>年龄</label>
                <input
                  type="number"
                  min="14"
                  max="80"
                  placeholder="例如：22"
                  value={studentProfile.age}
                  onChange={(e) => handleStudentChange('age', e.target.value)}
                  disabled={!isStudentActive}
                />
              </div>

              <div className="advice-field">
                <label>期望薪资区间（第一份工作）</label>
                <select
                  value={studentProfile.expectedSalaryBand}
                  onChange={(e) => handleStudentChange('expectedSalaryBand', e.target.value)}
                  disabled={!isStudentActive}
                >
                  <option value="">请选择</option>
                  {SALARY_BAND_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              </div>

              <div className="advice-field">
                <label>期望的主要发展方向</label>
                <select
                  value={studentProfile.expectedTrack}
                  onChange={(e) => handleStudentChange('expectedTrack', e.target.value)}
                  disabled={!isStudentActive}
                >
                  <option value="">请选择</option>
                  {CAREER_TRACK_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* 从业者卡片 */}
          <div
            className={
              'advice-card advice-role-card ' +
              (isProfessionalActive ? 'advice-role-card-selected' : isStudentActive ? 'advice-role-card-dimmed' : '')
            }
            onClick={() => setProfileType('professional')}
          >
            <div className="advice-card-header">
              <div>
                <div className="advice-eyebrow">Profile · Professional</div>
                <h3 className="advice-card-title">我是从业者 / 在职工程师</h3>
              </div>
              <div className="advice-role-pill">{isProfessionalActive ? '已选择' : '点击选择'}</div>
            </div>

            <div className="advice-role-fields" onClick={(e) => e.stopPropagation()}>
              <div className="advice-field">
                <label>工作年份</label>
                <input
                  type="number"
                  min="0"
                  max="50"
                  placeholder="例如：3"
                  value={proProfile.years}
                  onChange={(e) => handleProChange('years', e.target.value)}
                  disabled={!isProfessionalActive}
                />
              </div>

              <div className="advice-field">
                <label>当前薪资区间</label>
                <select
                  value={proProfile.salaryBand}
                  onChange={(e) => handleProChange('salaryBand', e.target.value)}
                  disabled={!isProfessionalActive}
                >
                  <option value="">请选择</option>
                  {SALARY_BAND_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              </div>

              <div className="advice-field">
                <label>当前 / 期望的工作方向</label>
                <select
                  value={proProfile.track}
                  onChange={(e) => handleProChange('track', e.target.value)}
                  disabled={!isProfessionalActive}
                >
                  <option value="">请选择</option>
                  {CAREER_TRACK_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 4. 其他补充 */}
      <section className="advice-section">
        <div className="advice-section-header">
          <h2>额外内容</h2>
          <p>用于描述你对数据使用的态度，以及补充任何你觉得重要但前面没覆盖到的信息。</p>
        </div>

        <div className="advice-other-grid">
          <div className="advice-card">
            <h3 className="advice-card-title">你是否愿意分享你的数据？</h3>
            <div className="advice-field">
              <label>用于匿名统计</label>
              <select value={otherInfo.consentShare} onChange={(e) => handleOtherChange('consentShare', e.target.value)}>
                <option value="">请选择</option>
                <option value="yes">是，我愿意匿名分享</option>
                <option value="no">否，只用于本次建议</option>
              </select>
            </div>
          </div>

          <div className="advice-card">
            <h3 className="advice-card-title">你填写的信息是否真实？</h3>
            <div className="advice-field">
              <label>反映你当前真实情况的程度</label>
              <select value={otherInfo.isTruthful} onChange={(e) => handleOtherChange('isTruthful', e.target.value)}>
                <option value="">请选择</option>
                <option value="true">基本真实，有少量估计</option>
                <option value="partial">部分为估计或理想状态</option>
                <option value="unspecified">我只是想看看这么填会有什么结果</option>
              </select>
            </div>
          </div>

          <div className="advice-card">
            <h3 className="advice-card-title">补充信息</h3>
            <div className="advice-field">
              <label>任何你希望让系统知道的额外信息（可选）</label>
              <textarea rows={3} value={otherInfo.note} onChange={(e) => handleOtherChange('note', e.target.value)} />
            </div>
          </div>
        </div>
      </section>

      {/* 5. 建议区：文本展示（非输入框） */}
      <section className="advice-section advice-section-bottom">
        <div className="advice-section-header advice-section-header-with-action">
          <div className="advice-section-header-text">
            <h2>建议区 · Data & AI</h2>
            <p>内容将由后端服务生成；未生成时会显示提示文案。</p>
            {generateError ? <p className="advice-generate-error">{generateError}</p> : null}
          </div>

          <button
            type="button"
            className="advice-generate-button advice-generate-button-inline"
            onClick={handleGenerateFromBackend}
            disabled={isGenerating}
            aria-busy={isGenerating}
          >
            {isGenerating ? '生成中...' : '生成建议'}
          </button>
        </div>

        <div className="advice-suggestions-grid">
          <div className="advice-card advice-suggestion-card">
            <div className="advice-card-header">
              <div>
                <div className="advice-eyebrow">Suggestion · Data View</div>
                <h3 className="advice-card-title">数据分析建议</h3>
              </div>
            </div>
            <div className="advice-suggestion-body">
              {!hasGenerated || !generateAnalysisText ? emptyHint : <AdviceDataView analysisText={generateAnalysisText} adviceData={adviceData} />}
            </div>
          </div>

          <div className="advice-card advice-suggestion-card">
            <div className="advice-card-header">
              <div>
                <div className="advice-eyebrow">Suggestion · AI Advice</div>
                <h3 className="advice-card-title">AI 建议</h3>
              </div>
            </div>
            <div className="advice-suggestion-body">
              {!hasGenerated || !generateAiSummary ? emptyHint : <AdviceChecklist text={generateAiSummary} />}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default PersonalAdvice;
