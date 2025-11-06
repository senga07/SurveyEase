import React, { useState, useEffect } from 'react';
import { ChatLogSummary, ChatLogDetail } from '../types';
import { ApiService } from '../services/api';
import MessageBubble from './MessageBubble';
import { Message } from '../types';
import './ChatHistory.css';

interface ChatHistoryProps {
  onBack: () => void;
}

const ChatHistory: React.FC<ChatHistoryProps> = ({ onBack }) => {
  const [history, setHistory] = useState<ChatLogSummary[]>([]);
  const [selectedLog, setSelectedLog] = useState<ChatLogDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      setLoading(true);
      const historyList = await ApiService.getChatHistory();
      setHistory(historyList);
    } catch (error) {
      console.error('加载历史记录失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleViewDetail = async (conversation_id: string) => {
    try {
      setLoadingDetail(true);
      const detail = await ApiService.getChatLogDetail(conversation_id);
      if (detail) {
        setSelectedLog(detail);
      }
    } catch (error) {
      console.error('加载历史记录详情失败:', error);
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleBackToList = () => {
    setSelectedLog(null);
  };

  const formatDateTime = (timestamp: string) => {
    try {
      // timestamp 格式为 yyyymmddHHmmss
      const year = timestamp.substring(0, 4);
      const month = timestamp.substring(4, 6);
      const day = timestamp.substring(6, 8);
      const hour = timestamp.substring(8, 10);
      const minute = timestamp.substring(10, 12);
      const second = timestamp.substring(12, 14);
      return `${year}-${month}-${day} ${hour}:${minute}:${second}`;
    } catch (error) {
      return timestamp;
    }
  };

  // 将历史记录消息转换为 Message 格式用于显示
  const convertMessagesToDisplay = (messages: ChatLogDetail['messages']): Message[] => {
    return messages.map((msg, index) => ({
      id: `${index}-${msg.timestamp}`,
      content: msg.content,
      sender: msg.type === 'HumanMessage' ? 'user' : 'assistant',
      timestamp: new Date(msg.timestamp || new Date().toISOString())
    }));
  };

  if (selectedLog) {
    const displayMessages = convertMessagesToDisplay(selectedLog.messages);
    return (
      <div className="chat-history">
        <div className="chat-history-header">
          <h3>历史记录详情</h3>
          <button onClick={handleBackToList} className="back-button">
            返回列表
          </button>
        </div>
        <div className="chat-history-info">
          <span>会话ID: {selectedLog.conversation_id}</span>
          <span>时间: {formatDateTime(selectedLog.timestamp)}</span>
          <span>消息数: {selectedLog.message_count}</span>
        </div>
        
        <div className="messages-container">
          {displayMessages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="chat-history">
      <div className="chat-history-header">
        <h3>历史记录</h3>
        <button onClick={onBack} className="back-button">
          返回首页
        </button>
      </div>

      {loading ? (
        <div className="loading-section">
          <p>正在加载历史记录...</p>
        </div>
      ) : history.length === 0 ? (
        <div className="no-history">
          <p>暂无历史记录</p>
        </div>
      ) : (
        <div className="history-list">
          {history.map((item) => (
            <div key={item.conversation_id} className="history-item">
              <div className="history-item-info">
                <div className="history-item-header">
                  <span className="history-item-id">会话ID: {item.conversation_id}</span>
                  <span className="history-item-time">{formatDateTime(item.timestamp)}</span>
                </div>
                <div className="history-item-meta">
                  <span>消息数: {item.message_count}</span>
                </div>
              </div>
              <button
                onClick={() => handleViewDetail(item.conversation_id)}
                className="view-detail-button"
                disabled={loadingDetail}
              >
                {loadingDetail ? '加载中...' : '查看详情'}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ChatHistory;

