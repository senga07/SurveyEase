import { ChatRequest, StreamData, SurveyTemplate } from '../types';

export class ApiService {
  private static baseUrl = '/api/survey';
  private static templateUrl = '/api/template';

  static async sendMessage(request: ChatRequest): Promise<ReadableStream<Uint8Array> | null> {
    try {
      const response = await fetch(`${this.baseUrl}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request)
      });

      if (response.ok) {
        return response.body;
      } else {
        console.error('API请求失败:', response.status, response.statusText);
        const errorText = await response.text();
        console.error('错误详情:', errorText);
        return null;
      }
    } catch (error) {
      console.error('发送消息失败:', error);
      return null;
    }
  }

  static async continueSurvey(request: { conversation_id: string; user_response: string; template_id: string }): Promise<ReadableStream<Uint8Array> | null> {
    try {
      const response = await fetch(`${this.baseUrl}/chat/continue`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request)
      });

      if (response.ok) {
        return response.body;
      }
      return null;
    } catch (error) {
      console.error('继续调研失败:', error);
      return null;
    }
  }

  static async processStream(
    stream: ReadableStream<Uint8Array>,
    onData: (data: StreamData) => void
  ): Promise<void> {
    const reader = stream.getReader();
    const decoder = new TextDecoder();

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              let content = line.slice(6);
              // 去掉前后的双引号
              if (content.startsWith('"') && content.endsWith('"')) {
                content = content.slice(1, -1);
              }
              const data: StreamData = { content };
              onData(data);
            } catch (e) {
              console.error('解析流式数据失败:', e);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  // 模板相关API
  static async getTemplates(): Promise<SurveyTemplate[]> {
    try {
      const response = await fetch(`${this.templateUrl}/templates`);
      console.log('API请求URL:', `${this.templateUrl}/templates`);
      console.log('API响应状态:', response.status);
      
      if (response.ok) {
        const data = await response.json();
        console.log('API响应数据:', data);
        return data;
      } else {
        const errorText = await response.text();
        console.error('API请求失败:', response.status, response.statusText, errorText);
        return [];
      }
    } catch (error) {
      console.error('获取模板列表失败:', error);
      return [];
    }
  }



  static async createTemplate(template: SurveyTemplate): Promise<boolean> {
    try {
      const response = await fetch(`${this.templateUrl}/templates`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(template)
      });
      return response.ok;
    } catch (error) {
      console.error('创建模板失败:', error);
      return false;
    }
  }

  static async updateTemplateById(templateId: string, template: SurveyTemplate): Promise<boolean> {
    try {
      const response = await fetch(`${this.templateUrl}/templates/${templateId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(template)
      });
      return response.ok;
    } catch (error) {
      console.error('更新模板失败:', error);
      return false;
    }
  }
}
