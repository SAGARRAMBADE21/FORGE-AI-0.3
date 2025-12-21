"""Middleware generator."""

import logging

logger = logging.getLogger(__name__)


class MiddlewareGenerator:
    """Generate Express middleware."""

    def generate_error_handler(self) -> str:
        """Generate error handler middleware."""
        return '''import { Request, Response, NextFunction } from 'express';

export interface AppError extends Error {
  statusCode?: number;
  code?: string;
  details?: any;
}

export class HttpError extends Error implements AppError {
  statusCode: number;
  code: string;

  constructor(statusCode: number, message: string, code?: string) {
    super(message);
    this.statusCode = statusCode;
    this.code = code || 'ERROR';
    this.name = 'HttpError';
  }
}

export class NotFoundError extends HttpError {
  constructor(resource: string = 'Resource') {
    super(404, `${resource} not found`, 'NOT_FOUND');
  }
}

export class ValidationError extends HttpError {
  details: any;

  constructor(message: string, details?: any) {
    super(400, message, 'VALIDATION_ERROR');
    this.details = details;
  }
}

export class UnauthorizedError extends HttpError {
  constructor(message: string = 'Unauthorized') {
    super(401, message, 'UNAUTHORIZED');
  }
}

export class ForbiddenError extends HttpError {
  constructor(message: string = 'Forbidden') {
    super(403, message, 'FORBIDDEN');
  }
}

export const errorHandler = (
  err: AppError,
  req: Request,
  res: Response,
  _next: NextFunction
): void => {
  const statusCode = err.statusCode || 500;
  const code = err.code || 'INTERNAL_ERROR';

  // Log error
  if (statusCode >= 500) {
    console.error('Server error:', err);
  } else {
    console.warn('Client error:', err.message);
  }

  res.status(statusCode).json({
    success: false,
    error: {
      message: err.message,
      code,
      ...(process.env.NODE_ENV === 'development' && { stack: err.stack }),
      ...((err as any).details && { details: (err as any).details }),
    },
  });
};
'''

    def generate_request_logger(self) -> str:
        """Generate request logger middleware."""
        return '''import { Request, Response, NextFunction } from 'express';

export interface RequestLogOptions {
  skip?: (req: Request) => boolean;
  format?: 'simple' | 'detailed';
}

export const requestLogger = (options: RequestLogOptions = {}) => {
  return (req: Request, res: Response, next: NextFunction): void => {
    // Skip if configured
    if (options.skip?.(req)) {
      next();
      return;
    }

    const start = Date.now();

    // Log on response finish
    res.on('finish', () => {
      const duration = Date.now() - start;
      const { method, originalUrl } = req;
      const { statusCode } = res;

      if (options.format === 'detailed') {
        console.log(JSON.stringify({
          timestamp: new Date().toISOString(),
          method,
          url: originalUrl,
          status: statusCode,
          duration,
          userAgent: req.get('user-agent'),
          ip: req.ip,
        }));
      } else {
        const statusColor = statusCode >= 500 ? '\\x1b[31m' : 
                           statusCode >= 400 ? '\\x1b[33m' : 
                           '\\x1b[32m';
        console.log(
          `${method} ${originalUrl} ${statusColor}${statusCode}\\x1b[0m ${duration}ms`
        );
      }
    });

    next();
  };
};
'''

    def generate_validation(self) -> str:
        """Generate validation middleware."""
        return '''import { Request, Response, NextFunction } from 'express';
import { ZodSchema, ZodError } from 'zod';

export interface ValidationSchemas {
  body?: ZodSchema;
  query?: ZodSchema;
  params?: ZodSchema;
}

export const validate = (schemas: ValidationSchemas | ZodSchema) => {
  return (req: Request, res: Response, next: NextFunction): void => {
    try {
      // Handle single schema (body only)
      if ('parse' in schemas) {
        schemas.parse(req.body);
        next();
        return;
      }

      // Handle multiple schemas
      const { body, query, params } = schemas;

      if (body) {
        req.body = body.parse(req.body);
      }

      if (query) {
        req.query = query.parse(req.query) as any;
      }

      if (params) {
        req.params = params.parse(req.params) as any;
      }

      next();
    } catch (error) {
      if (error instanceof ZodError) {
        res.status(400).json({
          success: false,
          error: {
            message: 'Validation failed',
            code: 'VALIDATION_ERROR',
            details: error.errors.map((e) => ({
              path: e.path.join('.'),
              message: e.message,
            })),
          },
        });
        return;
      }
      next(error);
    }
  };
};
'''

    def generate_rate_limiter(self) -> str:
        """Generate rate limiter middleware."""
        return '''import { Request, Response, NextFunction } from 'express';

interface RateLimitOptions {
  windowMs?: number;
  max?: number;
  message?: string;
  keyGenerator?: (req: Request) => string;
}

interface RateLimitStore {
  [key: string]: {
    count: number;
    resetTime: number;
  };
}

const store: RateLimitStore = {};

export const rateLimit = (options: RateLimitOptions = {}) => {
  const {
    windowMs = 60 * 1000, // 1 minute
    max = 100,
    message = 'Too many requests, please try again later',
    keyGenerator = (req) => req.ip || 'unknown',
  } = options;

  // Clean up expired entries periodically
  setInterval(() => {
    const now = Date.now();
    for (const key in store) {
      if (store[key].resetTime < now) {
        delete store[key];
      }
    }
  }, windowMs);

  return (req: Request, res: Response, next: NextFunction): void => {
    const key = keyGenerator(req);
    const now = Date.now();

    if (!store[key] || store[key].resetTime < now) {
      store[key] = {
        count: 1,
        resetTime: now + windowMs,
      };
      next();
      return;
    }

    store[key].count++;

    // Set rate limit headers
    res.setHeader('X-RateLimit-Limit', max);
    res.setHeader('X-RateLimit-Remaining', Math.max(0, max - store[key].count));
    res.setHeader('X-RateLimit-Reset', store[key].resetTime);

    if (store[key].count > max) {
      res.status(429).json({
        success: false,
        error: {
          message,
          code: 'RATE_LIMIT_EXCEEDED',
        },
      });
      return;
    }

    next();
  };
};
'''

    def generate_cors(self) -> str:
        """Generate CORS middleware."""
        return '''import { Request, Response, NextFunction } from 'express';

export interface CorsOptions {
  origin?: string | string[] | boolean | ((origin: string) => boolean);
  methods?: string[];
  allowedHeaders?: string[];
  exposedHeaders?: string[];
  credentials?: boolean;
  maxAge?: number;
}

export const cors = (options: CorsOptions = {}) => {
  const {
    origin = '*',
    methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
    allowedHeaders = ['Content-Type', 'Authorization'],
    exposedHeaders = [],
    credentials = true,
    maxAge = 86400,
  } = options;

  return (req: Request, res: Response, next: NextFunction): void => {
    const requestOrigin = req.get('origin') || '';

    // Determine allowed origin
    let allowedOrigin: string = '*';
    
    if (typeof origin === 'boolean') {
      allowedOrigin = origin ? requestOrigin : '';
    } else if (typeof origin === 'string') {
      allowedOrigin = origin;
    } else if (Array.isArray(origin)) {
      allowedOrigin = origin.includes(requestOrigin) ? requestOrigin : '';
    } else if (typeof origin === 'function') {
      allowedOrigin = origin(requestOrigin) ? requestOrigin : '';
    }

    // Set CORS headers
    res.setHeader('Access-Control-Allow-Origin', allowedOrigin);
    res.setHeader('Access-Control-Allow-Methods', methods.join(', '));
    res.setHeader('Access-Control-Allow-Headers', allowedHeaders.join(', '));
    
    if (exposedHeaders.length) {
      res.setHeader('Access-Control-Expose-Headers', exposedHeaders.join(', '));
    }
    
    if (credentials) {
      res.setHeader('Access-Control-Allow-Credentials', 'true');
    }
    
    res.setHeader('Access-Control-Max-Age', maxAge.toString());

    // Handle preflight
    if (req.method === 'OPTIONS') {
      res.status(204).end();
      return;
    }

    next();
  };
};
'''

    def generate_index(self) -> str:
        """Generate middleware index."""
        return '''export * from './errorHandler';
export * from './auth';
export * from './validate';
export * from './logger';
export * from './rateLimit';
export * from './cors';
'''