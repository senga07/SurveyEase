import React, { useState, useRef, useEffect } from 'react';
import MessageBubble from './MessageBubble';
import { Message } from '../types';
import './ChatWindow.css';

interface ChatWindowProps {
  messages: Message[];
  onSendMessage: (content: string) => void;
  isLoading: boolean;
  onReset: () => void;
}

const ChatWindow: React.FC<ChatWindowProps> = ({ 
  messages, 
  onSendMessage, 
  isLoading, 
  onReset 
}) => {
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 自动滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim() && !isLoading) {
      onSendMessage(inputValue.trim());
      setInputValue('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="chat-window">
      <div className="chat-header">
        <h3>调研对话</h3>
        <button onClick={onReset} className="reset-button">
          重新开始
        </button>
      </div>
      
      <div className="messages-container">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        {isLoading && (
          <div className="loading-message">
            <div className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <span>调研助手正在思考...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      
      <form onSubmit={handleSubmit} className="input-form">
        <div className="input-container">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="请输入您的回答..."
            className="message-input"
            rows={1}
            disabled={isLoading}
          />
          <button 
            type="submit" 
            disabled={!inputValue.trim() || isLoading}
            className="send-button"
          >
            发送
          </button>
        </div>
      </form>
    </div>
  );
};

export default ChatWindow;
