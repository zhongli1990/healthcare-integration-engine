import { useState, useEffect } from 'react';

interface User {
  id: string;
  email: string;
  name: string;
}

export const useAuth = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Mock authentication - always return as authenticated for development
  useEffect(() => {
    const mockUser = {
      id: '1',
      email: 'dev@example.com',
      name: 'Developer'
    };
    
    setUser(mockUser);
    setIsAuthenticated(true);
    setLoading(false);
  }, []);

  // Mock login - always succeeds for development
  const login = async (email: string, _password: string) => {
    const mockUser = {
      id: '1',
      email,
      name: email.split('@')[0] || 'User'
    };
    
    setUser(mockUser);
    setIsAuthenticated(true);
    return { success: true };
  };

  // Mock logout
  const logout = async () => {
    setUser(null);
    setIsAuthenticated(false);
    return { success: true };
  };

  return {
    user,
    loading,
    isAuthenticated,
    login,
    logout
  };
};
