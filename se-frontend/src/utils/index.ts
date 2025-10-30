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

/**
 * 将文本中的变量占位符和系统字符串转换为高亮的HTML元素
 * @param text 包含变量占位符和系统字符串的文本
 * @returns 包含高亮变量的HTML字符串
 */
export const highlightVariables = (text: string): string => {
  if (!text) return '';
  
  let result = text;
  
  // 先处理系统字符串 (END, FINISH) - 仅匹配大写
  const systemStringPattern = /\b(END|FINISH)\b/g;
  result = result.replace(systemStringPattern, (match) => {
    return `<span class="system-variable-highlight">${match}</span>`;
  });
  
  // 再处理 {{变量名}} 格式的占位符
  const variablePattern = /\{\{([^}]+)\}\}/g;
  result = result.replace(variablePattern, (_, variableName) => {
    return `<span class="variable-highlight">{{${variableName}}}</span>`;
  });
  
  return result;
};

/**
 * 将包含变量高亮的HTML字符串转换为React元素
 * @param htmlString 包含变量高亮的HTML字符串
 * @returns React元素
 */
export const renderHighlightedText = (htmlString: string) => {
  return { __html: htmlString };
};
