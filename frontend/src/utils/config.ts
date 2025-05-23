export const getApiBaseUrl = (): string => {
  const envUrl = import.meta.env.VITE_API_URL;
  
  if (envUrl) {
    return envUrl;
  }
  
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'http://localhost:8001';
  }
  
  return window.location.origin;
};

export const checkApiAvailability = async (): Promise<boolean> => {
  try {
    const response = await fetch(`${getApiBaseUrl()}/health`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });
    return response.ok;
  } catch (error) {
    if (isDev()) {
      console.error('API availability check failed:', error);
    }
    return false;
  }
};

export const isDev = () => {
  return import.meta.env.MODE === 'development' || import.meta.env.DEV || import.meta.env.VITE_DEV_MODE === 'true';
};