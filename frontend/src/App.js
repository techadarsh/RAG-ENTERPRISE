import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';
import HealthBadge from './components/HealthBadge';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// SVG Icons
const SendIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
  </svg>
);

const StopIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <rect x="6" y="6" width="12" height="12" rx="2"/>
  </svg>
);

const CopyIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
  </svg>
);

const AlertIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <circle cx="12" cy="12" r="10"/>
    <line x1="12" y1="8" x2="12" y2="12"/>
    <line x1="12" y1="16" x2="12.01" y2="16"/>
  </svg>
);

// Simple UUID generator
function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    // eslint-disable-next-line 
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

function App() {
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [typingText, setTypingText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isDegraded, setIsDegraded] = useState(false);
  const messagesEndRef = useRef(null);
  const chatContainerRef = useRef(null);
  const abortControllerRef = useRef(null);
  const typingIntervalRef = useRef(null);

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Generate session ID on mount
  useEffect(() => {
    setSessionId(generateUUID());
  }, []);

  // Scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages, typingText, isTyping]);

  // Scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages, typingText, isTyping]);

  // Typing animation effect
  const typeText = (text, sources, latency_ms) => {
    setIsTyping(true);
    setTypingText('');
    let currentIndex = 0;
    
    // Clear any existing interval
    if (typingIntervalRef.current) {
      clearInterval(typingIntervalRef.current);
    }
    
    typingIntervalRef.current = setInterval(() => {
      if (currentIndex < text.length) {
        setTypingText(text.substring(0, currentIndex + 1));
        currentIndex++;
      } else {
        clearInterval(typingIntervalRef.current);
        typingIntervalRef.current = null;
        setIsTyping(false);
        setTypingText('');
        
        // Add final message with sources
        const assistantMessage = {
          role: 'assistant',
          content: text,
          sources: sources,
          latency_ms: latency_ms
        };
        setMessages(prev => [...prev, assistantMessage]);
      }
    }, 15); // Faster typing speed
  };

  // Stop typing animation
  const stopTyping = () => {
    if (typingIntervalRef.current) {
      clearInterval(typingIntervalRef.current);
      typingIntervalRef.current = null;
    }
    setIsTyping(false);
    setTypingText('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!query.trim() || isGenerating || isTyping) {
      return;
    }

    // Add user message to chat
    const userMessage = { role: 'user', content: query };
    setMessages(prev => [...prev, userMessage]);
    
    const currentQuery = query;
    setQuery(''); // Clear input immediately
    setLoading(true);
    setIsGenerating(true);
    setError(null);

    // Create AbortController for cancellation
    abortControllerRef.current = new AbortController();

    // Add placeholder assistant message immediately (for loading state)
    const placeholderMessage = {
      role: 'assistant',
      content: '',
      isLoading: true
    };
    setMessages(prev => [...prev, placeholderMessage]);

    try {
      const result = await axios.post(
        `${API_BASE_URL}/ask`,
        {
          query: currentQuery,
          session_id: sessionId
        },
        {
          signal: abortControllerRef.current.signal
        }
      );
      
      setLoading(false);
      setIsGenerating(false);
      
      // Remove placeholder message
      setMessages(prev => prev.filter(msg => !msg.isLoading));
      
      // Start typing animation
      typeText(result.data.answer, result.data.sources, result.data.latency_ms);
      
      // Update session ID if backend provided a new one
      if (result.data.session_id && result.data.session_id !== sessionId) {
        setSessionId(result.data.session_id);
      }
    } catch (err) {
      // Remove placeholder message on error
      setMessages(prev => prev.filter(msg => !msg.isLoading));
      
      // Check if it was aborted - DON'T add message here, handleStop already did
      if (axios.isCancel(err) || err.name === 'CanceledError') {
        // Do nothing - handleStop already added the cancelled message
        console.log('Request was cancelled by user');
      } else {
        // Only add error for non-cancellation errors
        setError(err.response?.data?.detail || 'An error occurred. Please try again.');
        console.error('Error:', err);
      }
      
      setLoading(false);
      setIsGenerating(false);
    } finally {
      abortControllerRef.current = null;
    }
  };

  // Handle stop/cancel
  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    
    // Stop typing animation if in progress
    stopTyping();
    
    // Remove loading placeholder
    setMessages(prev => prev.filter(msg => !msg.isLoading));
    
    // Add ONLY ONE cancelled message
    const cancelledMessage = {
      role: 'assistant',
      content: '(Request cancelled)',
      isCancelled: true
    };
    setMessages(prev => [...prev, cancelledMessage]);
    
    setLoading(false);
    setIsGenerating(false);
  };

  // Copy message to clipboard
  const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      // Could add a toast notification here
      console.log('Copied to clipboard');
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
    // Escape key to cancel
    if (e.key === 'Escape' && isGenerating) {
      handleStop();
    }
  };

  return (
    <div className="App">
      {/* Three-column layout with gutters */}
      <div className="viewport-grid">
        {/* Left gutter - Reserved for future use */}
        <div className="left-gutter">
          {/* Reserved space */}
        </div>

        {/* Center - Main chat card */}
        <div className="center-content">
          <div className="container">
            <header className="header">
              <h1> RAG Enterprise Chatbot</h1>
              <p>Ask questions about company policies, onboarding, and HR information</p>
              {sessionId && (
                <p className="session-info">Session: {sessionId.slice(0, 8)}...</p>
              )}
            </header>

            <div className="chat-container" ref={chatContainerRef}>
              {/* Degraded mode banner */}
              {isDegraded && (
                <div className="degraded-banner" role="alert">
                  <span className="degraded-icon"><AlertIcon /></span>
                  <span className="degraded-text">
                    Model is temporarily unavailable. Showing retrieved excerpts only.
                  </span>
                </div>
              )}

              {/* Message history */}
              <div className="messages-wrapper" aria-live="polite" aria-atomic="false">
                {/* Always show messages if they exist */}
                {messages.length > 0 && (
                  <div className="messages-list">
                    {messages.map((msg, index) => (
                      <div 
                        key={index} 
                        className={`message ${msg.role} ${msg.isCancelled ? 'cancelled' : ''}`}
                      >
                        <div className="message-header">
                          <span className="message-role">
                            {msg.role === 'user' ? ' You' : ' Assistant'}
                          </span>
                          <div className="message-actions">
                            {msg.latency_ms && (
                              <span className="message-latency"> {(msg.latency_ms / 1000).toFixed(1)}s</span>
                            )}
                            {msg.isLoading && (
                              <span className="typing-indicator"> thinking...</span>
                            )}
                            {/* Copy button for completed messages */}
                            {!msg.isLoading && !msg.isCancelled && msg.content && (
                              <button 
                                className="copy-button"
                                onClick={() => copyToClipboard(msg.content)}
                                aria-label="Copy message"
                                title="Copy to clipboard"
                              >
                                <CopyIcon />
                              </button>
                            )}
                          </div>
                        </div>
                        
                        {/* Show loading dots or content */}
                        {msg.isLoading ? (
                          <div className="message-content loading-dots">
                            <span></span><span></span><span></span>
                          </div>
                        ) : (
                          <div className="message-content">{msg.content}</div>
                        )}
                        
                        {msg.sources && msg.sources.length > 0 && (
                          <div className="message-sources">
                            <details>
                              <summary> {msg.sources.length} sources</summary>
                              <div className="sources-list">
                                {msg.sources.map((source, idx) => (
                                  <div key={idx} className="source-item-inline">
                                    <strong>{source.title}</strong> (score: {typeof source.score === 'string' ? source.score : source.score.toFixed(3)})
                                    <p>{source.text}</p>
                                  </div>
                                ))}
                              </div>
                            </details>
                          </div>
                        )}
                      </div>
                    ))}
                    
                    {/* Typing animation - keep it inside messages-list */}
                    {isTyping && typingText && (
                      <div className="message assistant typing">
                        <div className="message-header">
                          <span className="message-role"> Assistant</span>
                          <span className="typing-indicator"> typing...</span>
                        </div>
                        <div className="message-content">
                          {typingText}<span className="cursor">|</span>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Typing animation when no messages yet (first interaction) */}
                {messages.length === 0 && isTyping && typingText && (
                  <div className="messages-list">
                    <div className="message assistant typing">
                      <div className="message-header">
                        <span className="message-role"> Assistant</span>
                        <span className="typing-indicator"> typing...</span>
                      </div>
                      <div className="message-content">
                        {typingText}<span className="cursor">|</span>
                      </div>
                    </div>
                  </div>
                )}

                {error && (
                  <div className="error-box">
                    <h3>Error</h3>
                    <p>{error}</p>
                  </div>
                )}

                {messages.length === 0 && !loading && !error && !isTyping && (
                  <div className="welcome-message">
                    <h2>Welcome!</h2>
                    <p>Start a conversation by asking about:</p>
                    <ul>
                      <li>HR policies and benefits</li>
                      <li>Leave and PTO information</li>
                      <li>Onboarding procedures</li>
                      <li>Engineering standards</li>
                      <li>Incident management</li>
                      <li>API documentation</li>
                    </ul>
                    <p className="hint"> I remember our conversation, so feel free to ask follow-up questions!</p>
                  </div>
                )}

                {/* Invisible element for scrolling to bottom */}
                <div ref={messagesEndRef} />
              </div>

              {/* Input form at bottom */}
              <form onSubmit={handleSubmit} className="input-form">
                <div className="input-wrapper">
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={handleKeyPress}
                    placeholder="Ask a question or continue the conversation..."
                    className="query-input"
                    disabled={isGenerating || isTyping}
                    aria-label="Message input"
                  />
                  {!isGenerating ? (
                    <button 
                      type="submit" 
                      className="send-button"
                      disabled={isTyping || !query.trim()}
                      aria-label="Send message"
                    >
                      <SendIcon />
                    </button>
                  ) : (
                    <button 
                      type="button"
                      onClick={handleStop}
                      className="stop-button"
                      aria-label="Stop generating"
                      title="Press Escape to stop"
                    >
                      <span className="stop-icon"><StopIcon /></span>
                      <span className="stop-text">Stop</span>
                    </button>
                  )}
                </div>
              </form>
            </div>

            <footer className="footer">
              <p>Powered by RAG | FastAPI + Milvus + BGE Embeddings + Mistral</p>
            </footer>
          </div>
        </div>

        {/* Right gutter - Health badges */}
        <div className="right-gutter">
          <HealthBadge onDegraded={setIsDegraded} position="side" />
        </div>
      </div>
    </div>
  );
}

export default App;
