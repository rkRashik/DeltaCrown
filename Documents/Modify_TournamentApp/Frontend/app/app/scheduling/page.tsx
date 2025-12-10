/**
 * Scheduling Page
 * Phase 9, Epic 9.4 - Frontend Boilerplate Scaffolding
 * 
 * Match scheduling calendar and timeline.
 * TODO: Integrate with Epic 9.2 SDK (DeltaCrownClient.scheduling.getCalendar)
 */

'use client';

import React from 'react';
import Card, { CardHeader, CardTitle, CardContent } from '../../components/Card';
import Badge from '../../components/Badge';

export default function SchedulingPage() {
  const mockSchedule = [
    { time: '12:00 PM', match: 'Match #1001', participants: 'Team Alpha vs Team Beta', status: 'scheduled' as const },
    { time: '1:30 PM', match: 'Match #1002', participants: 'Player1 vs Player2', status: 'in-progress' as const },
    { time: '3:00 PM', match: 'Match #1003', participants: 'DarkHorse vs Challenger', status: 'scheduled' as const },
    { time: '4:30 PM', match: 'Match #1004', participants: 'Finals Match', status: 'scheduled' as const },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-neutral-900">Scheduling</h1>
        <p className="text-neutral-600 mt-2">View and manage match schedules across all tournaments.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Today's Schedule</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {mockSchedule.map((item, idx) => (
              <div key={idx} className="flex items-center gap-4 p-4 rounded-lg border border-neutral-200 hover:bg-neutral-50 transition-colors">
                <div className="text-sm font-semibold text-brand-primary-600 w-24">{item.time}</div>
                <div className="flex-1">
                  <div className="font-medium text-neutral-900">{item.match}</div>
                  <div className="text-sm text-neutral-600">{item.participants}</div>
                </div>
                <Badge variant={item.status === 'in-progress' ? 'warning' : 'info'} size="sm">
                  {item.status === 'in-progress' ? 'In Progress' : 'Scheduled'}
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
