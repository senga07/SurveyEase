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
}

export interface SurveyVariable {
  key: string;
  value: string;
}

export interface SurveyTemplate {
  id: string;
  theme: string;
  system_prompt: string;
  max_turns: number;
  welcome_message: string;
  steps: SurveyStep[];
  end_message: string;
  variables?: SurveyVariable[];
}
