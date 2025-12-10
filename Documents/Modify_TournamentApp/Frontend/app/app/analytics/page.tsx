/**
 * Analytics Dashboard Page
 * Phase 9, Epic 9.4 - Frontend Boilerplate Scaffolding
 * 
 * Analytics and reporting for tournament performance.
 * TODO: Integrate with Epic 9.2 SDK (DeltaCrownClient.analytics.getMetrics)
 */

'use client';

import React from 'react';
import StatCard from '../../components/StatCard';
import Card, { CardHeader, CardTitle, CardContent } from '../../components/Card';

export default function AnalyticsPage() {
  const mockMetrics = {
    totalTournaments: 47,
    totalParticipants: 1247,
    completionRate: 94,
    avgParticipants: 26.5,
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-neutral-900">Analytics</h1>
        <p className="text-neutral-600 mt-2">Track performance and insights across your tournaments.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          label="Total Tournaments"
          value={mockMetrics.totalTournaments}
          trend={{ value: 15, direction: 'up' }}
          variant="primary"
          icon={
            <svg fill="currentColor" viewBox="0 0 20 20">
              <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
              <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" />
            </svg>
          }
        />
        <StatCard
          label="Total Participants"
          value={mockMetrics.totalParticipants}
          trend={{ value: 22, direction: 'up' }}
          variant="success"
          icon={
            <svg fill="currentColor" viewBox="0 0 20 20">
              <path d="M9 6a3 3 0 11-6 0 3 3 0 016 0zM17 6a3 3 0 11-6 0 3 3 0 016 0zM12.93 17c.046-.327.07-.66.07-1a6.97 6.97 0 00-1.5-4.33A5 5 0 0119 16v1h-6.07zM6 11a5 5 0 015 5v1H1v-1a5 5 0 015-5z" />
            </svg>
          }
        />
        <StatCard
          label="Completion Rate"
          value={`${mockMetrics.completionRate}%`}
          trend={{ value: 3, direction: 'up' }}
          variant="success"
          icon={
            <svg fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
          }
        />
        <StatCard
          label="Avg Participants"
          value={mockMetrics.avgParticipants}
          variant="primary"
          icon={
            <svg fill="currentColor" viewBox="0 0 20 20">
              <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
            </svg>
          }
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Performance Overview</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-neutral-500 text-center py-12">Chart visualization coming soon...</p>
        </CardContent>
      </Card>
    </div>
  );
}
