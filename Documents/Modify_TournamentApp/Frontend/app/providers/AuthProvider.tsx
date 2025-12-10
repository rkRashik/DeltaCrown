/**
 * Auth Provider
 * Phase 9, Epic 9.4 - Frontend Boilerplate Scaffolding
 * 
 * Provides authentication context to all components.
 * Integrates with DeltaCrown backend authentication.
 * 
 * TODO: Replace placeholder logic with actual backend integration
 */

'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';

interface User {
  id: string;
  username: string;
  email: string;
  role: 'player' | 'organizer' | 'admin' | 'staff';
  avatar?: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}

interface AuthProviderProps {
  children: React.ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Initialize auth state
  useEffect(() => {
    refreshAuth();
  }, []);

  const refreshAuth = async () => {
    setIsLoading(true);
    try {
      // TODO: Replace with actual API call
      // const response = await fetch('/api/auth/me', {
      //   credentials: 'include',
      // });
      // if (response.ok) {
      //   const userData = await response.json();
      //   setUser(userData);
      // } else {
      //   setUser(null);
      // }

      // Placeholder: Check localStorage for demo
      const storedUser = localStorage.getItem('deltacrown-user');
      if (storedUser) {
        setUser(JSON.parse(storedUser));
      } else {
        setUser(null);
      }
    } catch (error) {
      console.error('Auth refresh failed:', error);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      // TODO: Replace with actual API call
      // const response = await fetch('/api/auth/login', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({ email, password }),
      //   credentials: 'include',
      // });
      // if (!response.ok) {
      //   throw new Error('Login failed');
      // }
      // const userData = await response.json();
      // setUser(userData);
      // localStorage.setItem('deltacrown-user', JSON.stringify(userData));

      // Placeholder demo logic
      const demoUser: User = {
        id: '1',
        username: email.split('@')[0],
        email,
        role: 'organizer',
        avatar: 'https://ui-avatars.com/api/?name=' + email.split('@')[0],
      };
      setUser(demoUser);
      localStorage.setItem('deltacrown-user', JSON.stringify(demoUser));
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      // TODO: Replace with actual API call
      // await fetch('/api/auth/logout', {
      //   method: 'POST',
      //   credentials: 'include',
      // });

      // Clear local state
      setUser(null);
      localStorage.removeItem('deltacrown-user');
      localStorage.removeItem('deltacrown-token');
    } catch (error) {
      console.error('Logout failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        logout,
        refreshAuth,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
