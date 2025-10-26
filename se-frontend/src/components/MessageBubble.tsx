import React from 'react';
import { Message } from '../types';
import { formatTime } from '../utils';
import './MessageBubble.css';

interface MessageBubbleProps {
  message: Message;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  return (
    <div className={`message-bubble ${message.sender}`}>
      <div className="message-content">
        <div className="message-text">
          {message.content}
        </div>
        <div className="message-time">
          {formatTime(message.timestamp)}
        </div>
      </div>
    </div>
  );
};

export default MessageBubble;
