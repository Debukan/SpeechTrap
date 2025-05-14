import { getApiBaseUrl, isDev } from './config';
import axios from 'axios';

interface RequestOptions {
  method?: string;
  headers?: Record<string, string>;
  body?: any;
  token?: string;
  credentials?: RequestCredentials;
}

interface ApiResponse<T> {
  data: T | null;
  error: string | null;
  status: number;
}

/**
 * Выполняет запрос к API с обработкой ошибок
 * @param endpoint - путь к API без начального слэша
 * @param options - настройки запроса
 */
export async function apiRequest<T>(endpoint: string, options: RequestOptions = {}): Promise<ApiResponse<T>> {
  const apiBaseUrl = getApiBaseUrl();
  const url = `${apiBaseUrl}/${endpoint.startsWith('/') ? endpoint.substring(1) : endpoint}`;
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    ...options.headers,
  };

  if (options.token) {
    headers['Authorization'] = `Bearer ${options.token}`;
  }

  try {
    if (isDev()) {
      console.log(`API Request: ${options.method || 'GET'} ${url}`, options.body);
    }
    const response = await fetch(url, {
      method: options.method || 'GET',
      headers,
      body: options.body ? JSON.stringify(options.body) : undefined,
      credentials: 'same-origin',
    });

    if (isDev()) {
      console.log(`Response status: ${response.status}`);
    }
    
    let data = null;
    let error = null;
    
    try {
      if (response.status !== 204) {
        const responseText = await response.text();
        if (isDev()) {
          console.log(`Response text: ${responseText}`);
        }
        
        try {
          data = responseText ? JSON.parse(responseText) : null;
        } catch (e) {
          if (isDev()) {
            console.error('Error parsing JSON:', e);
          }
          error = `Некорректный формат ответа: ${responseText.substring(0, 100)}`;
        }
      }
    } catch (e) {
      if (isDev()) {
        console.error('Error reading response:', e);
      }
      error = 'Ошибка при обработке ответа сервера';
    }

    if (!response.ok) {
      error = (data && data.detail) || `Ошибка запроса (${response.status})`;
        
      if (response.status === 422) {
        if (isDev()) {
          console.error('Validation error details:', data);
        }
        error = 'Ошибка валидации данных. Проверьте правильность введённых данных.';
      } else if (response.status === 405) {
        error = 'Метод не разрешён. Проверьте API эндпоинт.';
      }
    }

    return {
      data: response.ok ? data : null,
      error,
      status: response.status,
    };
  } catch (e: any) {
    if (isDev()) {
      console.error('API request error:', e);
    }
    return {
      data: null,
      error: e.message === 'Failed to fetch' 
        ? 'Не удалось подключиться к серверу. Проверьте соединение и доступность сервера.'
        : e.message,
      status: 0,
    };
  }
}

const setAuthToken = (token: string) => {
  if (token) {
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  }
};

const clearAuthToken = () => {
  delete axios.defaults.headers.common['Authorization'];
};

/**
 * API клиент с методами для работы с пользователями
 */
export const api = {
  setAuthToken,
  clearAuthToken,
  auth: {
    login: (email: string, password: string) => 
      apiRequest<{ access_token: string, token_type: string }>('api/users/login', {
        method: 'POST',
        body: { email, password },
      }),
    
    register: (name: string, email: string, password: string) => 
      apiRequest('api/users/register', {
        method: 'POST',
        body: { name, email, password },
        credentials: 'omit',
      }),
    
    logout: (token: string) => 
      apiRequest('api/users/logout', {
        method: 'POST',
        token,
      }),
    
    getProfile: (token: string) => 
      apiRequest('api/users/me', {
        token,
        credentials: 'same-origin',
      }),
    
    updateProfile: (token: string, updateData: any) => 
      apiRequest('api/users/me', {
        method: 'PUT',
        body: updateData,
        token,
      }),
  },
};
