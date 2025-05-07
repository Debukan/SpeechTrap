import axios from 'axios';

// Настройка глобального перехватчика для всех запросов Axios
axios.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    } else {
      console.log('No token available for request:', config.url);
    }
    return config;
  },
  (error) => {
    console.error('Request error in interceptor:', error);
    return Promise.reject(error);
  },
);

// Добавляем интерцептор ответов для отладки
axios.interceptors.response.use(
  (response) => {
    console.log('Response from:', response.config.url, ', status:', response.status);
    return response;
  },
  (error) => {
    if (error.response) {
      console.error('Error response:', error.response.status, error.response.data);
    }
    return Promise.reject(error);
  },
);

export default axios;
