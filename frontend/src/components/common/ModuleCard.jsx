import React from 'react';
import { useNavigate } from 'react-router-dom';

const ModuleCard = ({ to, eyebrow, title, description, accent }) => {
  const navigate = useNavigate();

  return (
    <button
      className="module-card"
      onClick={() => navigate(to)}
      aria-label={title}
    >
      <div className="module-card-inner">
        <div className="module-card-eyebrow">{eyebrow}</div>
        <h3 className="module-card-title">{title}</h3>
        <p className="module-card-desc">{description}</p>
        <div className="module-card-footer">
          <span className="module-card-accent">{accent}</span>
          <span className="module-card-arrow">↗</span>
        </div>
      </div>
    </button>
  );
};

export default ModuleCard;
