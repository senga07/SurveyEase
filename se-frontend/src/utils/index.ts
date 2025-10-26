// 工具函数
export const formatTime = (date: Date): string => {
  return date.toLocaleTimeString('zh-CN', { 
    hour: '2-digit', 
    minute: '2-digit' 
  });
};

export const generateConversationId = (): string => {
  return 'conv_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
};

export const createMessage = (
  content: string, 
  sender: 'user' | 'assistant', 
  id?: string
) => ({
  id: id || Date.now().toString(),
  content,
  sender,
  timestamp: new Date()
});
