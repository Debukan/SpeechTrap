export const getApiBaseUrl = (): string => {
  const envUrl = process.env.REACT_APP_API_URL;
  
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
    console.error('API availability check failed:', error);
    return false;
  }
};
