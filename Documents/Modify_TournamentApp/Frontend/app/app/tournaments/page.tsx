/**
 * Tournaments List Page
 * Phase 9, Epic 9.4 - Frontend Boilerplate Scaffolding
 * 
 * Tournament listing with filters.
 * TODO: Integrate with Epic 9.2 SDK (DeltaCrownClient.tournaments.list)
 */

'use client';

import React, { useState } from 'react';
import TournamentCard from '../../components/TournamentCard';
import Select from '../../components/Select';
import Input from '../../components/Input';
import EmptyState from '../../components/EmptyState';

export default function TournamentsPage() {
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  // TODO: Replace with SDK call
  // const tournaments = await client.tournaments.list({ status, search });

  const mockTournaments = [
    {
      tournamentId: 'T1001',
      name: 'Summer Championship 2025',
      gameTitle: 'League of Legends',
      format: 'Single Elimination',
      status: 'in-progress' as const,
      participantCount: 64,
      maxParticipants: 64,
      tournamentStart: 'Jun 15, 2025',
      prizePool: '$10,000',
    },
    {
      tournamentId: 'T1002',
      name: 'Weekly Open Tournament #47',
      gameTitle: 'Counter-Strike 2',
      format: 'Swiss System',
      status: 'registration-open' as const,
      participantCount: 32,
      maxParticipants: 64,
      registrationEnd: 'Jun 20, 2025',
      tournamentStart: 'Jun 22, 2025',
      prizePool: '$2,500',
    },
    {
      tournamentId: 'T1003',
      name: 'Valorant Pro Circuit Qualifier',
      gameTitle: 'Valorant',
      format: 'Double Elimination',
      status: 'registration-open' as const,
      participantCount: 16,
      maxParticipants: 32,
      registrationEnd: 'Jun 18, 2025',
      tournamentStart: 'Jun 25, 2025',
      prizePool: '$5,000',
    },
    {
      tournamentId: 'T1004',
      name: 'Spring 2025 Finals',
      gameTitle: 'Dota 2',
      format: 'Round Robin',
      status: 'completed' as const,
      participantCount: 16,
      maxParticipants: 16,
      tournamentStart: 'May 1, 2025',
      prizePool: '$15,000',
    },
  ];

  const filteredTournaments = mockTournaments.filter((t) => {
    const matchesStatus = statusFilter === 'all' || t.status === statusFilter;
    const matchesSearch = t.name.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-neutral-900">Tournaments</h1>
          <p className="text-neutral-600 mt-2">Manage all your tournaments in one place.</p>
        </div>
        <button className="btn btn-primary">
          <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
              clipRule="evenodd"
            />
          </svg>
          Create Tournament
        </button>
      </div>

      {/* Filters */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Input
          placeholder="Search tournaments..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          leftIcon={
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z"
                clipRule="evenodd"
              />
            </svg>
          }
        />
        <Select
          placeholder="Filter by status"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          options={[
            { value: 'all', label: 'All Statuses' },
            { value: 'draft', label: 'Draft' },
            { value: 'registration-open', label: 'Registration Open' },
            { value: 'in-progress', label: 'In Progress' },
            { value: 'completed', label: 'Completed' },
            { value: 'cancelled', label: 'Cancelled' },
          ]}
        />
      </div>

      {/* Tournament Grid */}
      {filteredTournaments.length === 0 ? (
        <EmptyState
          title="No tournaments found"
          description="Try adjusting your filters or create a new tournament to get started."
          action={{
            label: 'Create Tournament',
            onClick: () => console.log('Create tournament'),
          }}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredTournaments.map((tournament) => (
            <TournamentCard key={tournament.tournamentId} {...tournament} />
          ))}
        </div>
      )}
    </div>
  );
}
