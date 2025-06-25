// This is a mock authentication service that can be easily upgraded to use JWT
// When ready to switch to real JWT auth, update the implementation to make API calls
// and handle real JWT tokens
import { User } from '../contexts/AuthContext';

interface LoginResponse {
  user: User;
  token: string;
  expiresIn: number;
}

// Helper function to generate avatar URL from name
const getAvatarUrl = (name: string) => {
  const colors = [
    'FFAD08', 'EDD70A', '73B06F', '0C9F9D', '4058B8',
    '8F3985', 'EF476F', 'FFD166', '06D6A0', '118AB2'
  ];
  const color = colors[Math.floor(Math.random() * colors.length)];
  const initials = name.split(' ').map(n => n[0]).join('').toUpperCase();
  return `https://ui-avatars.com/api/?name=${encodeURIComponent(initials)}&background=${color}&color=fff&size=128`;
};

// Mock user database
const mockUsers: User[] = [
  {
    id: '1',
    email: 'admin@example.com',
    name: 'Admin User',
    role: 'admin',
    title: 'System Administrator',
    department: 'IT',
    lastLogin: new Date().toISOString(),
    avatar: 'https://randomuser.me/api/portraits/men/32.jpg'
  },
  {
    id: '2',
    email: 'doctor@example.com',
    name: 'Dr. Sarah Johnson',
    role: 'doctor',
    title: 'Senior Physician',
    department: 'Cardiology',
    lastLogin: new Date(Date.now() - 86400000).toISOString(), // 1 day ago
    avatar: 'https://randomuser.me/api/portraits/women/44.jpg'
  },
  {
    id: '3',
    email: 'nurse@example.com',
    name: 'Nurse Jane Smith',
    role: 'nurse',
    title: 'Head Nurse',
    department: 'Emergency',
    lastLogin: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
    avatar: 'https://randomuser.me/api/portraits/women/68.jpg'
  },
  {
    id: '4',
    email: 'user@example.com',
    name: 'John Doe',
    role: 'user',
    title: 'Medical Assistant',
    department: 'Pediatrics',
    lastLogin: new Date(Date.now() - 7200000).toISOString(), // 2 hours ago
    avatar: 'https://randomuser.me/api/portraits/men/22.jpg'
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
        let user = mockUsers.find(u => u.email === email);
        
        if (!user) {
          // For demo purposes, create a new user if not found
          if (email.endsWith('@example.com')) {
            const name = email.split('@')[0].split('.')
              .map(part => part.charAt(0).toUpperCase() + part.slice(1))
              .join(' ');
            user = {
              id: (mockUsers.length + 1).toString(),
              email,
              name,
              role: 'user',
              title: 'Staff',
              department: 'General',
              lastLogin: new Date().toISOString(),
              avatar: getAvatarUrl(name)
            };
            mockUsers.push(user);
          } else {
            reject(new Error('Invalid credentials'));
            return;
          }
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
