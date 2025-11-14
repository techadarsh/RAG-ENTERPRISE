import React, { useEffect, useState } from 'react';
import './HealthBadge.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Health Icon SVG
const HealthIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
  </svg>
);

function HealthBadge({ onDegraded, position = 'bottom' }) {
  const [deps, setDeps] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let active = true;
    
    const fetchHealth = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/health/deps`);
        const data = await response.json();
        
        if (active) {
          setDeps(data);
          setIsLoading(false);
          
          // Notify parent if LLM is degraded
          if (onDegraded) {
            onDegraded(data?.ollama !== 'ok');
          }
        }
      } catch (error) {
        console.error('Health check failed:', error);
        if (active) {
          setIsLoading(false);
          // On error, assume degraded
          if (onDegraded) {
            onDegraded(true);
          }
        }
      }
    };

    // Fetch immediately
    fetchHealth();
    
    // Poll every 15 seconds (reduced from 5s for better performance)
    const intervalId = setInterval(fetchHealth, 15000);

    return () => {
      active = false;
      clearInterval(intervalId);
    };
  }, [onDegraded]);

  const StatusDot = ({ status }) => {
    const isOk = status === 'ok';
    const isUnavailable = status === 'unavailable' || status === 'not_loaded';
    
    return (
      <div className="status-indicator">
        <span className={`status-dot ${isOk ? 'status-ok' : isUnavailable ? 'status-warn' : 'status-fail'}`} />
        <span className={`status-text ${isOk ? 'text-ok' : isUnavailable ? 'text-warn' : 'text-fail'}`}>
          {isOk ? 'ok' : isUnavailable ? 'n/a' : 'fail'}
        </span>
      </div>
    );
  };

  if (isLoading) {
    return (
      <aside className={`health-badge-container ${position}`}>
        <div className="health-header">
          <span className="health-icon"><HealthIcon /></span>
          <span className="health-title">System</span>
        </div>
        <div className="health-items">
          <div className="health-item">
            <span className="health-label">Loading...</span>
          </div>
        </div>
      </aside>
    );
  }

  // Group services by category
  const coreServices = [
    { key: 'backend', label: 'Backend' },
    { key: 'milvus', label: 'Milvus' },
    { key: 'ollama', label: 'LLM' },
  ];

  const supportServices = [
    { key: 'embeddings', label: 'Embeddings' },
    { key: 'redis', label: 'Redis' },
    { key: 'etcd', label: 'Etcd' },
    { key: 'minio', label: 'Minio' },
  ];

  return (
    <aside className={`health-badge-container ${position}`}>
      <div className="health-header">
        <span className="health-icon"><HealthIcon /></span>
        <span className="health-title">System Health</span>
      </div>
      
      {/* Core Services */}
      <div className="health-section">
        <div className="health-section-title">Core</div>
        <div className="health-items">
          {coreServices.map(service => (
            <div key={service.key} className="health-item">
              <span className="health-label">{service.label}</span>
              <StatusDot status={deps?.[service.key]} />
            </div>
          ))}
        </div>
      </div>

      {/* Support Services */}
      <div className="health-section">
        <div className="health-section-title">Support</div>
        <div className="health-items">
          {supportServices.map(service => (
            <div key={service.key} className="health-item">
              <span className="health-label">{service.label}</span>
              <StatusDot status={deps?.[service.key]} />
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}

export default HealthBadge;