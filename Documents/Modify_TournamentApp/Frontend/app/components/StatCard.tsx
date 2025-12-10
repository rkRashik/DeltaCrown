/**
 * StatCard Component
 * Phase 9, Epic 9.4 - Frontend Boilerplate Scaffolding
 * 
 * Dashboard stat display card with value, label, trend, and icon.
 */

import React from 'react';
import Card from './Card';

interface StatCardProps {
  label: string;
  value: string | number;
  trend?: {
    value: number;
    direction: 'up' | 'down';
  };
  icon?: React.ReactNode;
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'error';
  className?: string;
}

export default function StatCard({ label, value, trend, icon, variant = 'default', className = '' }: StatCardProps) {
  const variantClasses = {
    default: 'bg-white border-neutral-200',
    primary: 'bg-brand-primary-50 border-brand-primary-200',
    success: 'bg-green-50 border-green-200',
    warning: 'bg-yellow-50 border-yellow-200',
    error: 'bg-red-50 border-red-200',
  };

  const iconVariantClasses = {
    default: 'bg-neutral-100 text-neutral-600',
    primary: 'bg-brand-primary-100 text-brand-primary-600',
    success: 'bg-green-100 text-green-600',
    warning: 'bg-yellow-100 text-yellow-600',
    error: 'bg-red-100 text-red-600',
  };

  return (
    <Card variant="bordered" padding="md" className={`${variantClasses[variant]} ${className}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-neutral-600 mb-1">{label}</p>
          <p className="text-3xl font-bold text-neutral-900">{value}</p>
          {trend && (
            <div className="flex items-center gap-1 mt-2">
              {trend.direction === 'up' ? (
                <svg className="w-4 h-4 text-success" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M5.293 9.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L10 6.414l-3.293 3.293a1 1 0 01-1.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
              ) : (
                <svg className="w-4 h-4 text-error" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L10 13.586l3.293-3.293a1 1 0 011.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
              <span
                className={`text-sm font-medium ${trend.direction === 'up' ? 'text-success' : 'text-error'}`}
              >
                {Math.abs(trend.value)}%
              </span>
              <span className="text-sm text-neutral-500">vs last period</span>
            </div>
          )}
        </div>
        {icon && (
          <div className={`p-3 rounded-lg ${iconVariantClasses[variant]}`}>
            <div className="w-6 h-6">{icon}</div>
          </div>
        )}
      </div>
    </Card>
  );
}
