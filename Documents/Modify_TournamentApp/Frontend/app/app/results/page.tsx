/**
 * Results Inbox Page
 * Phase 9, Epic 9.4 - Frontend Boilerplate Scaffolding
 * 
 * Pending match results for review and approval.
 * TODO: Integrate with Epic 9.2 SDK (DeltaCrownClient.results.getPending)
 */

'use client';

import React from 'react';
import Card from '../../components/Card';
import Badge from '../../components/Badge';
import Button from '../../components/Button';

export default function ResultsPage() {
  const mockResults = [
    {
      id: 'R1',
      match: 'Match #5001',
      tournament: 'Summer Championship',
      submittedBy: 'Team Alpha',
      submittedAt: '5 minutes ago',
      score: '2-1',
      status: 'pending' as const,
    },
    {
      id: 'R2',
      match: 'Match #5002',
      tournament: 'Weekly Open #47',
      submittedBy: 'ProGamer123',
      submittedAt: '15 minutes ago',
      score: '2-0',
      status: 'disputed' as const,
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-3xl font-bold text-neutral-900">Results Inbox</h1>
          <Badge variant="error" size="lg">{mockResults.length}</Badge>
        </div>
        <p className="text-neutral-600 mt-2">Review and approve pending match results.</p>
      </div>

      <div className="space-y-4">
        {mockResults.map((result) => (
          <Card key={result.id} variant="bordered" padding="md">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="text-lg font-semibold text-neutral-900">{result.match}</h3>
                  <Badge variant={result.status === 'disputed' ? 'error' : 'warning'} size="sm">
                    {result.status === 'disputed' ? 'Disputed' : 'Pending Review'}
                  </Badge>
                </div>
                <p className="text-sm text-neutral-600 mb-1">{result.tournament}</p>
                <div className="flex items-center gap-4 text-sm text-neutral-500">
                  <span>Submitted by: <strong>{result.submittedBy}</strong></span>
                  <span>•</span>
                  <span>{result.submittedAt}</span>
                  <span>•</span>
                  <span className="font-semibold text-brand-primary-600">{result.score}</span>
                </div>
              </div>
              <div className="flex gap-2">
                <Button variant="success" size="sm">Approve</Button>
                <Button variant="danger" size="sm">Reject</Button>
                <Button variant="secondary" size="sm">View Details</Button>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
