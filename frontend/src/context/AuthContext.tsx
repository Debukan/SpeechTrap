import React, { createContext, useContext, useState, useEffect } from 'react';
import { getApiBaseUrl } from '../utils/config';
import { api } from '../utils/api';
import { isDev } from '../utils/config';

interface User {
  id: number;
  name: string;
  email: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (token: string, userData: User) => Promise<void>;
  logout: () => void;
  updatePassword: (currentPassword: string, newPassword: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(!!token);

  useEffect(() => {
    if (token) {
      api.setAuthToken(token);
    } else {
      api.clearAuthToken();
    }
  }, [token]);

  useEffect(() => {
    // Проверка токена при загрузке приложения
    const checkAuth = async () => {
      const storedToken = localStorage.getItem('token');
      if (!storedToken) {
        setIsAuthenticated(false);
        setUser(null);
        return;
      }

      try {
        api.setAuthToken(storedToken);

        // Запрос данных пользователя с использованием токена
        const result = await api.auth.getProfile(storedToken);

        if (result.error) {
          throw new Error(result.error);
        }

        setUser(result.data as User);
        setToken(storedToken);
        setIsAuthenticated(true);
      } catch (error) {
        if (isDev()) {
          console.error('Ошибка аутентификации:', error);
        }
        localStorage.removeItem('token');
        api.clearAuthToken();
        setToken(null);
        setUser(null);
        setIsAuthenticated(false);
      }
    };

    checkAuth();
  }, []);

  const login = async (newToken: string, userData: User): Promise<void> => {
    try {
      localStorage.setItem('token', newToken);
      api.setAuthToken(newToken);
      setToken(newToken);
      setUser(userData);
      setIsAuthenticated(true);
      return Promise.resolve();
    } catch (error) {
      if (isDev()) {
        console.error('Ошибка при входе:', error);
      }
      return Promise.reject(error);
    }
  };

  const logout = () => {

    if (token) {
      api.auth.logout(token).catch(error => {
        if (isDev()) {
          console.error('Ошибка при выходе:', error);
        }
      });
    }

    localStorage.removeItem('token');
    api.clearAuthToken();
    setToken(null);
    setUser(null);
    setIsAuthenticated(false);
  };

  const updatePassword = async (currentPassword: string, newPassword: string): Promise<void> => {
    if (!token) {
      throw new Error('Пользователь не авторизован');
    }

    try {
      const result = await api.auth.updateProfile(token, {
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: newPassword,
      });

      if (result.error) {
        throw new Error(result.error);
      }

      setUser(result.data as User);
      return Promise.resolve();
    } catch (error: any) {
      if (isDev()) {
        console.error('Ошибка при смене пароля:', error);
      }
      return Promise.reject(error);
    }
  };

  return (
    <AuthContext.Provider value={{
      user,
      token,
      login,
      logout,
      isAuthenticated,
      updatePassword,
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};