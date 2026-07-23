import React, { createContext, useContext, useState, useEffect } from 'react';
import type { User, AuthState } from '../types';
import { getMeApi, loginApi, registerApi } from '../services/authService';

interface AuthContextType extends AuthState {
  login: (username: string, password: string) => Promise<void>;
  register: (data: { email: string; username: string; password: string; full_name?: string }) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('access_token'));
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    async function loadUser() {
      if (token) {
        try {
          const userData = await getMeApi();
          setUser(userData);
        } catch {
          localStorage.removeItem('access_token');
          setToken(null);
          setUser(null);
        }
      }
      setIsLoading(false);
    }
    loadUser();
  }, [token]);

  const login = async (username: string, password: string) => {
    const res = await loginApi(username, password);
    localStorage.setItem('access_token', res.access_token);
    setToken(res.access_token);
    const userData = await getMeApi();
    setUser(userData);
  };

  const register = async (data: { email: string; username: string; password: string; full_name?: string }) => {
    await registerApi(data);
    await login(data.username, data.password);
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
