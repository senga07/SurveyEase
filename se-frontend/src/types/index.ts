// 共享类型定义
export interface Message {
  id: string;
  content: string;
  sender: 'user' | 'assistant';
  timestamp: Date;
}

export interface ChatRequest {
  conversation_id: string;
  message: string;
  template_id: string;
}

export interface ContinueRequest {
  conversation_id: string;
  user_response: string;
  template_id: string;
}

export interface StreamData {
  content: string;
}

export interface SurveyStep {
  id: string;
  content: string;
  type?: 'linear' | 'condition';
  condition?: string;  // 条件跳转的匹配条件
  branches?: string[]; // 简化为字符串数组，[0]为是，[1]为否
}

export interface SurveyVariable {
  key: string;
  value: string;
}

export interface SurveyTemplate {
  id: string;
  theme: string;
  system_prompt: string;
  background_knowledge?: string;
  max_turns: number;
  welcome_message: string;
  steps: SurveyStep[];
  end_message: string;
  variables?: SurveyVariable[];
  host_id?: string;
}

export interface Host {
  id: string;
  name: string;
  role: string;
}

export interface ChatLogSummary {
  conversation_id: string;
  timestamp: string;
  created_at: string;
  message_count: number;
}

export interface ChatLogDetail {
  conversation_id: string;
  timestamp: string;
  created_at: string;
  message_count: number;
  messages: Array<{
    type: string;
    content: string;
    timestamp: string;
    additional_kwargs?: any;
  }>;
}
