/**
 * Matches List Page
 * Phase 9, Epic 9.4 - Frontend Boilerplate Scaffolding
 * 
 * Match listing with status filters.
 * TODO: Integrate with Epic 9.2 SDK (DeltaCrownClient.matches.list)
 */

'use client';

import React, { useState } from 'react';
import MatchCard from '../../components/MatchCard';
import Select from '../../components/Select';
import EmptyState from '../../components/EmptyState';

export default function MatchesPage() {
  const [statusFilter, setStatusFilter] = useState('all');

  const mockMatches = [
    {
      matchId: 'M5001',
      participant1: { id: 'P1', name: 'Team Alpha', score: undefined },
      participant2: { id: 'P2', name: 'Team Beta', score: undefined },
      status: 'scheduled' as const,
      scheduledTime: 'Today, 3:00 PM',
      round: 'Quarterfinals',
      bracketPosition: 'Upper Bracket',
    },
    {
      matchId: 'M5002',
      participant1: { id: 'P3', name: 'ProGamer123', score: 2 },
      participant2: { id: 'P4', name: 'ElitePlayer99', score: 1 },
      status: 'completed' as const,
      round: 'Round 1',
      bracketPosition: 'Lower Bracket',
    },
    {
      matchId: 'M5003',
      participant1: { id: 'P5', name: 'DarkHorse', score: 1 },
      participant2: { id: 'P6', name: 'Challenger', score: 1 },
      status: 'in-progress' as const,
      round: 'Semifinals',
      bracketPosition: 'Upper Bracket',
    },
    {
      matchId: 'M5004',
      participant1: { id: 'P7', name: 'Underdog', score: 2 },
      participant2: { id: 'P8', name: 'FinalBoss', score: 2 },
      status: 'disputed' as const,
      round: 'Finals',
      bracketPosition: 'Grand Finals',
    },
  ];

  const filteredMatches = mockMatches.filter((m) => statusFilter === 'all' || m.status === statusFilter);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-neutral-900">Matches</h1>
        <p className="text-neutral-600 mt-2">View and manage all tournament matches.</p>
      </div>

      <Select
        placeholder="Filter by status"
        value={statusFilter}
        onChange={(e) => setStatusFilter(e.target.value)}
        options={[
          { value: 'all', label: 'All Matches' },
          { value: 'scheduled', label: 'Scheduled' },
          { value: 'in-progress', label: 'In Progress' },
          { value: 'completed', label: 'Completed' },
          { value: 'disputed', label: 'Disputed' },
        ]}
        className="max-w-xs"
      />

      {filteredMatches.length === 0 ? (
        <EmptyState title="No matches found" description="Try adjusting your filters." />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {filteredMatches.map((match) => (
            <MatchCard key={match.matchId} {...match} />
          ))}
        </div>
      )}
    </div>
  );
}
