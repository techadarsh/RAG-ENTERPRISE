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
  const [useSSE, setUseSSE] = useState(true); // Try SSE first, fallback to polling

  useEffect(() => {
    let active = true;
    let eventSource = null;
    let fallbackInterval = null;

    const updateHealth = (data) => {
      if (active) {
        setDeps(data);
        setIsLoading(false);
        
        // Notify parent if LLM is degraded
        if (onDegraded) {
          onDegraded(data?.ollama !== 'ok');
        }
      }
    };

    const fetchHealth = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/health/deps`);
        const data = await response.json();
        updateHealth(data);
      } catch (error) {
        console.error('Health check failed:', error);
        if (active) {
          setIsLoading(false);
          if (onDegraded) {
            onDegraded(true);
          }
        }
      }
    };

    // Try Server-Sent Events first (more efficient)
    if (useSSE) {
      try {
        eventSource = new EventSource(`${API_BASE_URL}/health/stream`);
        
        eventSource.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            updateHealth(data);
          } catch (e) {
            console.error('Failed to parse SSE data:', e);
          }
        };
        
        eventSource.onerror = (error) => {
          console.warn('SSE connection failed, falling back to polling:', error);
          eventSource.close();
          setUseSSE(false); // Fallback to polling
        };
        
      } catch (error) {
        console.warn('SSE not supported, using polling:', error);
        setUseSSE(false);
      }
    }

    // Fallback: Traditional polling (only if SSE fails)
    if (!useSSE) {
      fetchHealth(); // Immediate fetch
      fallbackInterval = setInterval(fetchHealth, 15000);
    }

    return () => {
      active = false;
      if (eventSource) {
        eventSource.close();
      }
      if (fallbackInterval) {
        clearInterval(fallbackInterval);
      }
    };
  }, [onDegraded, useSSE]);

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