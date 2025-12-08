import React, { useState } from 'react';
import '../styles/personal-advice.css';

const LANGUAGE_OPTIONS = [
  'TypeScript',
  'JavaScript',
  'Python',
  'Java',
  'Go',
  'Rust',
  'C#',
  'Kotlin',
  'Swift',
  'C++',
];

const WEBFRAME_OPTIONS = [
  'React',
  'Next.js',
  'Vue',
  'Nuxt',
  'SvelteKit',
  'Angular',
  'SolidJS',
  'jQuery（遗留）',
];

const DATABASE_OPTIONS = [
  'PostgresSQL',
  'MySQL',
  'MariaDB',
  'MongoDB',
  'Redis',
  'Elasticsearch',
  'ClickHouse',
  'SQLite',
  'DynamoDB',
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

  // 是否展示“建议区”
  const [showSuggestions, setShowSuggestions] = useState(false);

  const handleTechToggle = (group, value) => {
    setTechStack((prev) => {
      const current = prev[group] || [];
      const exists = current.includes(value);
      return {
        ...prev,
        [group]: exists
          ? current.filter((v) => v !== value)
          : [...current, value],
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

  // 未来接后端的地方
  const handleGenerateFromBackend = () => {
    // TODO: 调用后端接口生成建议，然后 setAnalysisNote / setAiSummary
  };

  const handleGenerateClick = () => {
    handleGenerateFromBackend();
    setShowSuggestions(true);
  };

  const isStudentActive = profileType === 'student';
  const isProfessionalActive = profileType === 'professional';

  return (
    <div className="advice-page">
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
                <h3 className="advice-card-title">主力编程语言</h3>
              </div>
              <span className="advice-chip">
                已选 {techStack.languages.length} 项
              </span>
            </div>
            <p className="advice-card-subtitle">
              选择你在真实项目中<strong>写过 3 个以上中大型需求</strong>的语言。
            </p>
            <div className="advice-options-grid">
              {LANGUAGE_OPTIONS.map((lang) => {
                const checked = techStack.languages.includes(lang);
                return (
                  <label
                    key={lang}
                    className={
                      'advice-option-pill ' +
                      (checked ? 'advice-option-pill-active' : '')
                    }
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

          {/* Web 框架 */}
          <div className="advice-card">
            <div className="advice-card-header">
              <div>
                <div className="advice-eyebrow">Stack · Web Framework</div>
                <h3 className="advice-card-title">Web 框架与前端栈</h3>
              </div>
              <span className="advice-chip">
                已选 {techStack.webframes.length} 项
              </span>
            </div>
            <p className="advice-card-subtitle">
              选择你可以独立完成一个典型业务页面 / 模块的 Web 技术栈。
            </p>
            <div className="advice-options-grid">
              {WEBFRAME_OPTIONS.map((fw) => {
                const checked = techStack.webframes.includes(fw);
                return (
                  <label
                    key={fw}
                    className={
                      'advice-option-pill ' +
                      (checked ? 'advice-option-pill-active' : '')
                    }
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

          {/* 数据库 */}
          <div className="advice-card">
            <div className="advice-card-header">
              <div>
                <div className="advice-eyebrow">Stack · Database</div>
                <h3 className="advice-card-title">数据库与数据存储</h3>
              </div>
              <span className="advice-chip">
                已选 {techStack.databases.length} 项
              </span>
            </div>
            <p className="advice-card-subtitle">
              选择你能独立完成建表、索引、基础查询和简单调优的数据库。
            </p>
            <div className="advice-options-grid">
              {DATABASE_OPTIONS.map((db) => {
                const checked = techStack.databases.includes(db);
                return (
                  <label
                    key={db}
                    className={
                      'advice-option-pill ' +
                      (checked ? 'advice-option-pill-active' : '')
                    }
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
        </div>
      </section>

      {/* 3. 身份与预期（新的薪资 & 角色模块） */}
      <section className="advice-section">
        <div className="advice-section-header">
          <h2>身份与预期</h2>
          <p>
            先确认你当前处在<strong>学生</strong>还是<strong>在职从业者</strong>阶段。点击卡片以选择。
          </p>
        </div>

        <div className="advice-role-grid">
          {/* 学生卡片 */}
          <div
            className={
              'advice-card advice-role-card ' +
              (isStudentActive
                ? 'advice-role-card-selected'
                : isProfessionalActive
                ? 'advice-role-card-dimmed'
                : '')
            }
            onClick={() => setProfileType('student')}
          >
            <div className="advice-card-header">
              <div>
                <div className="advice-eyebrow">Profile · Student</div>
                <h3 className="advice-card-title">我是学生 / 准毕业生</h3>
              </div>
              <div className="advice-role-pill">
                {isStudentActive ? '已选择' : '点击选择'}
              </div>
            </div>
            <p className="advice-card-subtitle">
              适用于在校生、应届生或正在准备转专业读研读博的同学。填写你对未来一份工作的直觉预期即可。
            </p>

            <div
              className="advice-role-fields"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="advice-field">
                <label>年龄</label>
                <input
                  type="number"
                  min="14"
                  max="80"
                  placeholder="例如：22"
                  value={studentProfile.age}
                  onChange={(e) =>
                    handleStudentChange('age', e.target.value)
                  }
                  disabled={!isStudentActive}
                />
              </div>

              <div className="advice-field">
                <label>期望薪资区间（第一份工作）</label>
                <select
                  value={studentProfile.expectedSalaryBand}
                  onChange={(e) =>
                    handleStudentChange('expectedSalaryBand', e.target.value)
                  }
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
                  onChange={(e) =>
                    handleStudentChange('expectedTrack', e.target.value)
                  }
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
              (isProfessionalActive
                ? 'advice-role-card-selected'
                : isStudentActive
                ? 'advice-role-card-dimmed'
                : '')
            }
            onClick={() => setProfileType('professional')}
          >
            <div className="advice-card-header">
              <div>
                <div className="advice-eyebrow">Profile · Professional</div>
                <h3 className="advice-card-title">我是从业者 / 在职工程师</h3>
              </div>
              <div className="advice-role-pill">
                {isProfessionalActive ? '已选择' : '点击选择'}
              </div>
            </div>
            <p className="advice-card-subtitle">
              适用于已经有正式工作经验的同学，包括实习转正、社招、技术管理等角色。
              更关注的是当前所在档位与进步空间。
            </p>

            <div
              className="advice-role-fields"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="advice-field">
                <label>工作年份</label>
                <input
                  type="number"
                  min="0"
                  max="50"
                  placeholder="例如：3"
                  value={proProfile.years}
                  onChange={(e) =>
                    handleProChange('years', e.target.value)
                  }
                  disabled={!isProfessionalActive}
                />
              </div>

              <div className="advice-field">
                <label>当前薪资区间</label>
                <select
                  value={proProfile.salaryBand}
                  onChange={(e) =>
                    handleProChange('salaryBand', e.target.value)
                  }
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

      {/* 4. 其他补充（新问题） */}
      <section className="advice-section">
        <div className="advice-section-header">
          <h2>额外内容</h2>
          <p>
            这一部分用于描述你对数据使用的态度，以及补充任何你觉得重要但前面没覆盖到的信息。
          </p>
        </div>

        <div className="advice-other-grid">
          <div className="advice-card">
            <h3 className="advice-card-title">你是否愿意分享你的数据？</h3>
            <div className="advice-field">
              <label>用于匿名统计</label>
              <select
                value={otherInfo.consentShare}
                onChange={(e) =>
                  handleOtherChange('consentShare', e.target.value)
                }
              >
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
              <select
                value={otherInfo.isTruthful}
                onChange={(e) =>
                  handleOtherChange('isTruthful', e.target.value)
                }
              >
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
              <label>任何你希望让系统知道的额外信息</label>
              <textarea
                rows={3}
                value={otherInfo.note}
                onChange={(e) =>
                  handleOtherChange('note', e.target.value)
                }
              />
            </div>
          </div>
        </div>
      </section>

      {/* 底部：生成建议按钮 */}
      <section className="advice-section advice-generate-section">
        <button
          type="button"
          className="advice-generate-button"
          onClick={handleGenerateClick}
        >
          生成建议
        </button>
        <p className="advice-generate-hint">
          点击后将根据你填写的信息生成建议，并在下方展示「建议区」。
        </p>
      </section>

      {/* 5. 建议区：数据分析建议 + AI 总结（点击按钮后展示） */}
      {showSuggestions && (
        <section className="advice-section advice-section-bottom">
          <div className="advice-section-header">
            <h2>建议区 · Data & AI</h2>
            <p>
              左侧为数据分析建议，右侧为 AI 总结输出区域。内容将由后端服务生成，这里仅保留展示与编辑框架。
            </p>
          </div>

          <div className="advice-suggestions-grid">
            <div className="advice-card advice-suggestion-card">
              <div className="advice-card-header">
                <div>
                  <div className="advice-eyebrow">Suggestion · Data View</div>
                  <h3 className="advice-card-title">数据分析建议</h3>
                </div>
              </div>
              <textarea
                className="advice-suggestion-textarea"
                rows={6}
                value={analysisNote}
                onChange={(e) => setAnalysisNote(e.target.value)}
              />
            </div>

            <div className="advice-card advice-suggestion-card">
              <div className="advice-card-header">
                <div>
                  <div className="advice-eyebrow">Suggestion · AI Summary</div>
                  <h3 className="advice-card-title">AI 总结区</h3>
                </div>
                <button
                  type="button"
                  className="advice-ai-button"
                  onClick={handleGenerateFromBackend}
                >
                  重新生成
                </button>
              </div>
              <textarea
                className="advice-suggestion-textarea"
                rows={6}
                value={aiSummary}
                onChange={(e) => setAiSummary(e.target.value)}
              />
            </div>
          </div>
        </section>
      )}
    </div>
  );
};

export default PersonalAdvice;
