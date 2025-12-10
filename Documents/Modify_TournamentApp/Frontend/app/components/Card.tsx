/**
 * Card Component
 * Phase 9, Epic 9.4 - Frontend Boilerplate Scaffolding
 * 
 * Reusable card container with variants.
 */

import React from 'react';

interface CardProps {
  children: React.ReactNode;
  variant?: 'default' | 'flat' | 'bordered' | 'hoverable';
  className?: string;
  padding?: 'none' | 'sm' | 'md' | 'lg';
  as?: 'div' | 'article' | 'section';
}

export default function Card({
  children,
  variant = 'default',
  className = '',
  padding = 'md',
  as: Component = 'div',
}: CardProps) {
  const baseClasses = 'rounded-lg transition-shadow';

  const variantClasses = {
    default: 'bg-white shadow-sm border border-neutral-200',
    flat: 'bg-neutral-50',
    bordered: 'bg-white border-2 border-neutral-300',
    hoverable:
      'bg-white shadow-sm border border-neutral-200 hover:shadow-md hover:border-brand-primary-300 cursor-pointer',
  };

  const paddingClasses = {
    none: '',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
  };

  return (
    <Component
      className={`${baseClasses} ${variantClasses[variant]} ${paddingClasses[padding]} ${className}`}
    >
      {children}
    </Component>
  );
}

interface CardHeaderProps {
  children: React.ReactNode;
  className?: string;
}

export function CardHeader({ children, className = '' }: CardHeaderProps) {
  return <div className={`mb-4 ${className}`}>{children}</div>;
}

interface CardTitleProps {
  children: React.ReactNode;
  className?: string;
  as?: 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6';
}

export function CardTitle({ children, className = '', as: Component = 'h3' }: CardTitleProps) {
  return <Component className={`text-lg font-semibold text-neutral-900 ${className}`}>{children}</Component>;
}

interface CardDescriptionProps {
  children: React.ReactNode;
  className?: string;
}

export function CardDescription({ children, className = '' }: CardDescriptionProps) {
  return <p className={`text-sm text-neutral-600 mt-1 ${className}`}>{children}</p>;
}

interface CardContentProps {
  children: React.ReactNode;
  className?: string;
}

export function CardContent({ children, className = '' }: CardContentProps) {
  return <div className={className}>{children}</div>;
}

interface CardFooterProps {
  children: React.ReactNode;
  className?: string;
}

export function CardFooter({ children, className = '' }: CardFooterProps) {
  return <div className={`mt-6 pt-4 border-t border-neutral-200 ${className}`}>{children}</div>;
}
