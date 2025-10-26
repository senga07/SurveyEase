import { useState, useCallback } from 'react';
import { Message, SurveyTemplate } from '../types';
import { generateConversationId, createMessage } from '../utils';
import { ApiService } from '../services/api';

export const useSurvey = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [templateId, setTemplateId] = useState<string | null>(null);
  const [isFirstMessage, setIsFirstMessage] = useState(true);

  const startSurvey = useCallback(async (template?: SurveyTemplate) => {
    const newConversationId = generateConversationId();
    setConversationId(newConversationId);
    
    // 使用传入的模板或从后端获取模板
    let selectedTemplate = template;
    if (!selectedTemplate) {
      try {
        const templates = await ApiService.getTemplates();
        selectedTemplate = templates.length > 0 ? templates[0] : undefined;
      } catch (error) {
        console.error('获取模板失败:', error);
      }
    }
    
    // 存储模板ID
    if (selectedTemplate) {
      setTemplateId(selectedTemplate.id);
    }
    
    const welcomeMessage = createMessage(
      selectedTemplate?.welcome_message || "我是本次调研的负责人，让我们开始这次调研吧",
      'assistant'
    );
    setMessages([welcomeMessage]);
    
    setIsLoading(false);
  }, []);

  const sendMessage = useCallback(async (content: string) => {
    if (!conversationId || !content.trim() || !templateId) return;

    const userMessage = createMessage(content, 'user');
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      let stream;
      
      // 根据是否是第一条消息调用不同的接口
      if (isFirstMessage) {
        stream = await ApiService.sendMessage({
          conversation_id: conversationId,
          message: content,
          template_id: templateId
        });
        setIsFirstMessage(false); // 标记第一条消息已发送
      } else {
        stream = await ApiService.continueSurvey({
          conversation_id: conversationId,
          user_response: content,
          template_id: templateId
        });
      }

      if (stream) {
        let assistantMessageId = (Date.now() + 1).toString();
        let assistantContent = '';
        
        const assistantMessage = createMessage('', 'assistant', assistantMessageId);
        setMessages(prev => [...prev, assistantMessage]);

        await ApiService.processStream(stream, (data) => {
          if (data.content) {
            assistantContent = data.content;
            setMessages(prev => 
              prev.map(msg => 
                msg.id === assistantMessageId 
                  ? { ...msg, content: assistantContent }
                  : msg
              )
            );
          }
        });
      }
    } catch (error) {
      console.error('发送消息失败:', error);
    } finally {
      setIsLoading(false);
    }
  }, [conversationId, isFirstMessage, templateId]);

  const resetSurvey = useCallback(() => {
    setMessages([]);
    setConversationId(null);
    setTemplateId(null);
    setIsFirstMessage(true);
    setIsLoading(false);
  }, []);

  return {
    messages,
    isLoading,
    conversationId,
    startSurvey,
    sendMessage,
    resetSurvey
  };
};
