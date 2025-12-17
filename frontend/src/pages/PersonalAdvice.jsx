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

const PersonalAdvice = () => {
  const [techStack, setTechStack] = useState({
    languages: [],
    webframes: [],
    databases: [],
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

  // 建议区内容：留给后端填充
  const [analysisNote, setAnalysisNote] = useState('');
  const [aiSummary, setAiSummary] = useState('');

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

    // 技术栈三块都要有选择
    if (!techStack.languages?.length) missing.push('语言/基础能力掌握情况');
    if (!techStack.databases?.length) missing.push('数据库掌握情况');
    if (!techStack.webframes?.length) missing.push('Web/框架/平台掌握情况');

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

      // TODO: 替换为你的真实后端接口
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
      setAnalysisNote(data?.analysisNote ?? '');
      setAiSummary(data?.aiSummary ?? '');

      setHasGenerated(true);
      // showToast('已提交生成请求', 'success'); // 如果你想成功也提示
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
            <div className="advice-suggestion-text">
              {!hasGenerated || !analysisNote?.trim() ? emptyHint : analysisNote}
            </div>
          </div>

          <div className="advice-card advice-suggestion-card">
            <div className="advice-card-header">
              <div>
                <div className="advice-eyebrow">Suggestion · AI Advice</div>
                <h3 className="advice-card-title">AI 建议</h3>
              </div>
            </div>
            <div className="advice-suggestion-text">
              {!hasGenerated || !aiSummary?.trim() ? emptyHint : aiSummary}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default PersonalAdvice;
