"""Authentication code generator."""

import logging
from core.types import AuthRequirements, AuthStrategy
from synthesis.auth_planner import AuthPlan

logger = logging.getLogger(__name__)


class AuthGenerator:
    """Generate authentication implementation."""

    def generate_middleware(self, auth: AuthRequirements, plan: AuthPlan) -> str:
        """Generate auth middleware."""
        if auth.strategy == AuthStrategy.JWT:
            return self._generate_jwt_middleware(auth)
        elif auth.strategy == AuthStrategy.SESSION:
            return self._generate_session_middleware(auth)
        else:
            return self._generate_jwt_middleware(auth)

    def generate_service(self, auth: AuthRequirements, plan: AuthPlan) -> str:
        """Generate auth service."""
        imports = '''import { PrismaClient, User } from '@prisma/client';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import { UserRepository } from '../repositories/user.repository';
'''

        types = '''
export interface AuthResult {
  user: Omit<User, 'passwordHash'>;
  accessToken: string;
  refreshToken?: string;
}

export interface TokenPayload {
  userId: string;
  email: string;
  role: string;
}

export interface RegisterInput {
  email: string;
  password: string;
  name?: string;
}

export interface LoginInput {
  email: string;
  password: string;
}
'''

        service = f'''
export class AuthService {{
  private readonly jwtSecret: string;
  private readonly jwtExpiresIn: string;
  private readonly refreshExpiresIn: string;

  constructor(private userRepository: UserRepository) {{
    this.jwtSecret = process.env.JWT_SECRET || 'change-me-in-production';
    this.jwtExpiresIn = process.env.JWT_EXPIRES_IN || '15m';
    this.refreshExpiresIn = process.env.JWT_REFRESH_EXPIRES_IN || '7d';
  }}

  async register(input: RegisterInput): Promise<AuthResult> {{
    // Check if user exists
    const existing = await this.userRepository.findByEmail(input.email);
    if (existing) {{
      throw new Error('User already exists');
    }}

    // Hash password
    const passwordHash = await bcrypt.hash(input.password, 12);

    // Create user
    const user = await this.userRepository.create({{
      email: input.email,
      passwordHash,
      name: input.name,
      role: 'user',
    }});

    // Generate tokens
    const tokens = this.generateTokens(user);

    return {{
      user: this.sanitizeUser(user),
      ...tokens,
    }};
  }}

  async login(input: LoginInput): Promise<AuthResult> {{
    // Find user
    const user = await this.userRepository.findByEmail(input.email);
    if (!user) {{
      throw new Error('Invalid credentials');
    }}

    // Verify password
    const valid = await bcrypt.compare(input.password, user.passwordHash || '');
    if (!valid) {{
      throw new Error('Invalid credentials');
    }}

    // Generate tokens
    const tokens = this.generateTokens(user);

    return {{
      user: this.sanitizeUser(user),
      ...tokens,
    }};
  }}

  async refreshToken(refreshToken: string): Promise<AuthResult> {{
    try {{
      const payload = jwt.verify(refreshToken, this.jwtSecret) as TokenPayload & {{ type: string }};
      
      if (payload.type !== 'refresh') {{
        throw new Error('Invalid token type');
      }}

      const user = await this.userRepository.findById(payload.userId);
      if (!user) {{
        throw new Error('User not found');
      }}

      const tokens = this.generateTokens(user);

      return {{
        user: this.sanitizeUser(user),
        ...tokens,
      }};
    }} catch (error) {{
      throw new Error('Invalid refresh token');
    }}
  }}

  async validateToken(token: string): Promise<TokenPayload | null> {{
    try {{
      const payload = jwt.verify(token, this.jwtSecret) as TokenPayload;
      return payload;
    }} catch {{
      return null;
    }}
  }}

  async getCurrentUser(userId: string): Promise<Omit<User, 'passwordHash'>> {{
    const user = await this.userRepository.findById(userId);
    if (!user) {{
      throw new Error('User not found');
    }}
    return this.sanitizeUser(user);
  }}

  async changePassword(userId: string, oldPassword: string, newPassword: string): Promise<void> {{
    const user = await this.userRepository.findById(userId);
    if (!user) {{
      throw new Error('User not found');
    }}

    const valid = await bcrypt.compare(oldPassword, user.passwordHash || '');
    if (!valid) {{
      throw new Error('Invalid current password');
    }}

    const passwordHash = await bcrypt.hash(newPassword, 12);
    await this.userRepository.update(userId, {{ passwordHash }});
  }}

  private generateTokens(user: User): {{ accessToken: string; refreshToken: string }} {{
    const payload: TokenPayload = {{
      userId: user.id,
      email: user.email,
      role: user.role || 'user',
    }};

    const accessToken = jwt.sign(payload, this.jwtSecret, {{
      expiresIn: this.jwtExpiresIn,
    }});

    const refreshToken = jwt.sign(
      {{ ...payload, type: 'refresh' }},
      this.jwtSecret,
      {{ expiresIn: this.refreshExpiresIn }}
    );

    return {{ accessToken, refreshToken }};
  }}

  private sanitizeUser(user: User): Omit<User, 'passwordHash'> {{
    const {{ passwordHash, ...sanitized }} = user;
    return sanitized;
  }}
}}
'''

        return imports + types + service

    def generate_controller(self, auth: AuthRequirements, plan: AuthPlan) -> str:
        """Generate auth controller."""
        return '''import { Request, Response, NextFunction } from 'express';
import { AuthService, RegisterInput, LoginInput } from '../services/auth.service';

export class AuthController {
  constructor(private authService: AuthService) {}

  register = async (req: Request, res: Response, next: NextFunction) => {
    try {
      const input: RegisterInput = req.body;
      const result = await this.authService.register(input);
      res.status(201).json({ success: true, data: result });
    } catch (error) {
      if ((error as Error).message === 'User already exists') {
        res.status(409).json({ success: false, error: { message: 'User already exists' } });
        return;
      }
      next(error);
    }
  };

  login = async (req: Request, res: Response, next: NextFunction) => {
    try {
      const input: LoginInput = req.body;
      const result = await this.authService.login(input);
      res.json({ success: true, data: result });
    } catch (error) {
      if ((error as Error).message === 'Invalid credentials') {
        res.status(401).json({ success: false, error: { message: 'Invalid credentials' } });
        return;
      }
      next(error);
    }
  };

  refresh = async (req: Request, res: Response, next: NextFunction) => {
    try {
      const { refreshToken } = req.body;
      const result = await this.authService.refreshToken(refreshToken);
      res.json({ success: true, data: result });
    } catch (error) {
      res.status(401).json({ success: false, error: { message: 'Invalid refresh token' } });
    }
  };

  me = async (req: Request, res: Response, next: NextFunction) => {
    try {
      const userId = (req as any).user?.userId;
      if (!userId) {
        res.status(401).json({ success: false, error: { message: 'Unauthorized' } });
        return;
      }
      const user = await this.authService.getCurrentUser(userId);
      res.json({ success: true, data: user });
    } catch (error) {
      next(error);
    }
  };

  logout = async (req: Request, res: Response, next: NextFunction) => {
    try {
      // For JWT, logout is typically handled client-side
      // Could implement token blacklisting here if needed
      res.json({ success: true, message: 'Logged out successfully' });
    } catch (error) {
      next(error);
    }
  };

  changePassword = async (req: Request, res: Response, next: NextFunction) => {
    try {
      const userId = (req as any).user?.userId;
      const { oldPassword, newPassword } = req.body;
      await this.authService.changePassword(userId, oldPassword, newPassword);
      res.json({ success: true, message: 'Password changed successfully' });
    } catch (error) {
      if ((error as Error).message === 'Invalid current password') {
        res.status(400).json({ success: false, error: { message: 'Invalid current password' } });
        return;
      }
      next(error);
    }
  };
}
'''

    def _generate_jwt_middleware(self, auth: AuthRequirements) -> str:
        """Generate JWT authentication middleware."""
        return '''import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';

export interface AuthenticatedRequest extends Request {
  user?: {
    userId: string;
    email: string;
    role: string;
  };
}

export const authenticate = (
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
) => {
  try {
    const authHeader = req.headers.authorization;
    
    if (!authHeader?.startsWith('Bearer ')) {
      res.status(401).json({
        success: false,
        error: { message: 'No token provided', code: 'NO_TOKEN' },
      });
      return;
    }

    const token = authHeader.substring(7);
    const secret = process.env.JWT_SECRET || 'change-me';
    
    const payload = jwt.verify(token, secret) as {
      userId: string;
      email: string;
      role: string;
    };

    req.user = payload;
    next();
  } catch (error) {
    res.status(401).json({
      success: false,
      error: { message: 'Invalid token', code: 'INVALID_TOKEN' },
    });
  }
};

export const authorize = (...roles: string[]) => {
  return (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
    if (!req.user) {
      res.status(401).json({
        success: false,
        error: { message: 'Not authenticated', code: 'NOT_AUTHENTICATED' },
      });
      return;
    }

    if (roles.length && !roles.includes(req.user.role)) {
      res.status(403).json({
        success: false,
        error: { message: 'Insufficient permissions', code: 'FORBIDDEN' },
      });
      return;
    }

    next();
  };
};

export const optionalAuth = (
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
) => {
  try {
    const authHeader = req.headers.authorization;
    
    if (authHeader?.startsWith('Bearer ')) {
      const token = authHeader.substring(7);
      const secret = process.env.JWT_SECRET || 'change-me';
      const payload = jwt.verify(token, secret) as any;
      req.user = payload;
    }
  } catch {
    // Ignore errors for optional auth
  }
  
  next();
};
'''

    def _generate_session_middleware(self, auth: AuthRequirements) -> str:
        """Generate session-based auth middleware."""
        return '''import { Request, Response, NextFunction } from 'express';
import session from 'express-session';

declare module 'express-session' {
  interface SessionData {
    userId?: string;
    email?: string;
    role?: string;
  }
}

export const sessionConfig = session({
  secret: process.env.SESSION_SECRET || 'change-me',
  resave: false,
  saveUninitialized: false,
  cookie: {
    secure: process.env.NODE_ENV === 'production',
    httpOnly: true,
    maxAge: 7 * 24 * 60 * 60 * 1000, // 7 days
  },
});

export const authenticate = (
  req: Request,
  res: Response,
  next: NextFunction
) => {
  if (!req.session.userId) {
    res.status(401).json({
      success: false,
      error: { message: 'Not authenticated' },
    });
    return;
  }
  next();
};

export const authorize = (...roles: string[]) => {
  return (req: Request, res: Response, next: NextFunction) => {
    if (!req.session.userId) {
      res.status(401).json({
        success: false,
        error: { message: 'Not authenticated' },
      });
      return;
    }

    if (roles.length && !roles.includes(req.session.role || '')) {
      res.status(403).json({
        success: false,
        error: { message: 'Insufficient permissions' },
      });
      return;
    }

    next();
  };
};
'''