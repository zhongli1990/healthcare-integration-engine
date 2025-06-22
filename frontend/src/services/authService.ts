// This is a mock authentication service that can be easily upgraded to use JWT
// When ready to switch to real JWT auth, update the implementation to make API calls
// and handle real JWT tokens

interface User {
  id: string;
  email: string;
  name: string;
  role: string;
}

interface LoginResponse {
  user: User;
  token: string;
  expiresIn: number;
}

// Mock user database
const mockUsers: User[] = [
  {
    id: '1',
    email: 'admin@example.com',
    name: 'Admin User',
    role: 'admin'
  },
  {
    id: '2',
    email: 'user@example.com',
    name: 'Regular User',
    role: 'user'
  }
];

class AuthService {
  // This will be used to store the JWT token when we upgrade
  private token: string | null = null;
  private user: User | null = null;

  // Mock login - will be replaced with real JWT auth
  async login(email: string, password: string): Promise<LoginResponse> {
    // In a real implementation, this would make an API call to /auth/login
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        const user = mockUsers.find(u => u.email === email);
        
        if (!user) {
          reject(new Error('Invalid credentials'));
          return;
        }

        // In a real implementation, we would get this from the API
        this.token = 'mock-jwt-token';
        this.user = user;
        
        // Store in localStorage to persist across page refreshes
        localStorage.setItem('auth_token', this.token);
        localStorage.setItem('user', JSON.stringify(user));
        
        resolve({
          user,
          token: this.token,
          expiresIn: 3600 // 1 hour
        });
      }, 500); // Simulate network delay
    });
  }

  // Mock logout
  async logout(): Promise<void> {
    return new Promise((resolve) => {
      setTimeout(() => {
        this.token = null;
        this.user = null;
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user');
        resolve();
      }, 200);
    });
  }

  // Check if user is authenticated
  isAuthenticated(): boolean {
    // In a real implementation, we would validate the JWT token
    return !!localStorage.getItem('auth_token');
  }

  // Get current user
  getCurrentUser(): User | null {
    if (this.user) return this.user;
    
    const userStr = localStorage.getItem('user');
    if (userStr) {
      try {
        this.user = JSON.parse(userStr);
        return this.user;
      } catch (e) {
        console.error('Failed to parse user from localStorage', e);
        return null;
      }
    }
    
    return null;
  }

  // Get auth token (for API requests)
  getAuthToken(): string | null {
    if (!this.token) {
      this.token = localStorage.getItem('auth_token');
    }
    return this.token;
  }

  // Check if user has required role
  hasRole(requiredRole: string): boolean {
    const user = this.getCurrentUser();
    return user?.role === requiredRole;
  }
}

// Export a singleton instance
export const authService = new AuthService();

// For JWT upgrade later:
// 1. Update login() to make API call to /auth/login
// 2. Store JWT token from response
// 3. Add token refresh logic
// 4. Update isAuthenticated() to validate JWT
// 5. Add interceptors to add auth header to requests
