import { ChatRequest, StreamData, SurveyTemplate, Host, ChatLogSummary, ChatLogDetail } from '../types';

export class ApiService {
  private static baseUrl = '/api/survey';
  private static templateUrl = '/api/template';
  private static hostUrl = '/api/host';

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
              let content = line.slice(6).trim();
              // 使用 JSON.parse 正确解析 JSON 字符串，这样 \n 会被正确解析为换行符
              if (content) {
                content = JSON.parse(content);
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

  // 主持人相关API
  static async getHosts(): Promise<Host[]> {
    try {
      const response = await fetch(`${this.hostUrl}/hosts`);
      if (response.ok) {
        const data = await response.json();
        return data;
      } else {
        console.error('获取主持人列表失败:', response.status, response.statusText);
        return [];
      }
    } catch (error) {
      console.error('获取主持人列表失败:', error);
      return [];
    }
  }

  static async createHost(host: Host): Promise<boolean> {
    try {
      const response = await fetch(`${this.hostUrl}/hosts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(host)
      });
      return response.ok;
    } catch (error) {
      console.error('创建主持人失败:', error);
      return false;
    }
  }

  static async updateHostById(hostId: string, host: Host): Promise<boolean> {
    try {
      const response = await fetch(`${this.hostUrl}/hosts/${hostId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(host)
      });
      return response.ok;
    } catch (error) {
      console.error('更新主持人失败:', error);
      return false;
    }
  }

  static async deleteHostById(hostId: string): Promise<boolean> {
    try {
      const response = await fetch(`${this.hostUrl}/hosts/${hostId}`, {
        method: 'DELETE'
      });
      return response.ok;
    } catch (error) {
      console.error('删除主持人失败:', error);
      return false;
    }
  }

  // 历史记录相关API
  static async getChatHistory(): Promise<ChatLogSummary[]> {
    try {
      const response = await fetch(`${this.baseUrl}/chat/history`);
      if (response.ok) {
        const data = await response.json();
        return data;
      } else {
        console.error('获取历史记录列表失败:', response.status, response.statusText);
        return [];
      }
    } catch (error) {
      console.error('获取历史记录列表失败:', error);
      return [];
    }
  }

  static async getChatLogDetail(conversation_id: string): Promise<ChatLogDetail | null> {
    try {
      const response = await fetch(`${this.baseUrl}/chat/history/${encodeURIComponent(conversation_id)}`);
      if (response.ok) {
        const data = await response.json();
        if (data.error) {
          console.error('获取历史记录详情失败:', data.error);
          return null;
        }
        return data;
      } else {
        console.error('获取历史记录详情失败:', response.status, response.statusText);
        return null;
      }
    } catch (error) {
      console.error('获取历史记录详情失败:', error);
      return null;
    }
  }
}
