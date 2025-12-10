/**
 * Dashboard Page
 * Phase 9, Epic 9.4 - Frontend Boilerplate Scaffolding
 * 
 * Main dashboard with stats, recent tournaments, and recent matches.
 * TODO: Integrate with Epic 9.2 SDK (DeltaCrownClient)
 */

'use client';

import React from 'react';
import StatCard from '../components/StatCard';
import TournamentCard from '../components/TournamentCard';
import MatchCard from '../components/MatchCard';
import { CardHeader, CardTitle } from '../components/Card';

export default function DashboardPage() {
  // TODO: Replace with actual SDK calls
  // import { DeltaCrownClient } from '@deltacrown/sdk';
  // const client = new DeltaCrownClient({ apiKey: process.env.NEXT_PUBLIC_API_KEY });
  // const stats = await client.analytics.getOrganizer Dashboard();
  // const tournaments = await client.tournaments.list({ limit: 3, status: 'active' });
  // const matches = await client.matches.list({ limit: 5, status: 'pending' });

  const mockStats = {
    activeTournaments: 12,
    totalParticipants: 487,
    pendingMatches: 24,
    revenue: '$12,450',
  };

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
  ];

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
      participant1: { id: 'P5', name: 'DarkHorse', score: undefined },
      participant2: { id: 'P6', name: 'Challenger', score: undefined },
      status: 'in-progress' as const,
      round: 'Semifinals',
      bracketPosition: 'Upper Bracket',
    },
  ];

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-neutral-900">Dashboard</h1>
        <p className="text-neutral-600 mt-2">Welcome back! Here's what's happening with your tournaments.</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          label="Active Tournaments"
          value={mockStats.activeTournaments}
          trend={{ value: 12, direction: 'up' }}
          variant="primary"
          icon={
            <svg fill="currentColor" viewBox="0 0 20 20">
              <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
              <path
                fillRule="evenodd"
                d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z"
                clipRule="evenodd"
              />
            </svg>
          }
        />

        <StatCard
          label="Total Participants"
          value={mockStats.totalParticipants}
          trend={{ value: 8, direction: 'up' }}
          variant="success"
          icon={
            <svg fill="currentColor" viewBox="0 0 20 20">
              <path d="M9 6a3 3 0 11-6 0 3 3 0 016 0zM17 6a3 3 0 11-6 0 3 3 0 016 0zM12.93 17c.046-.327.07-.66.07-1a6.97 6.97 0 00-1.5-4.33A5 5 0 0119 16v1h-6.07zM6 11a5 5 0 015 5v1H1v-1a5 5 0 015-5z" />
            </svg>
          }
        />

        <StatCard
          label="Pending Matches"
          value={mockStats.pendingMatches}
          variant="warning"
          icon={
            <svg fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z"
                clipRule="evenodd"
              />
            </svg>
          }
        />

        <StatCard
          label="Total Revenue"
          value={mockStats.revenue}
          trend={{ value: 23, direction: 'up' }}
          variant="success"
          icon={
            <svg fill="currentColor" viewBox="0 0 20 20">
              <path d="M8.433 7.418c.155-.103.346-.196.567-.267v1.698a2.305 2.305 0 01-.567-.267C8.07 8.34 8 8.114 8 8c0-.114.07-.34.433-.582zM11 12.849v-1.698c.22.071.412.164.567.267.364.243.433.468.433.582 0 .114-.07.34-.433.582a2.305 2.305 0 01-.567.267z" />
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-13a1 1 0 10-2 0v.092a4.535 4.535 0 00-1.676.662C6.602 6.234 6 7.009 6 8c0 .99.602 1.765 1.324 2.246.48.32 1.054.545 1.676.662v1.941c-.391-.127-.68-.317-.843-.504a1 1 0 10-1.51 1.31c.562.649 1.413 1.076 2.353 1.253V15a1 1 0 102 0v-.092a4.535 4.535 0 001.676-.662C13.398 13.766 14 12.991 14 12c0-.99-.602-1.765-1.324-2.246A4.535 4.535 0 0011 9.092V7.151c.391.127.68.317.843.504a1 1 0 101.511-1.31c-.563-.649-1.413-1.076-2.354-1.253V5z"
                clipRule="evenodd"
              />
            </svg>
          }
        />
      </div>

      {/* Active Tournaments */}
      <div>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Active Tournaments</CardTitle>
            <a
              href="/tournaments"
              className="text-sm font-medium text-brand-primary-600 hover:text-brand-primary-700 transition-colors"
            >
              View All →
            </a>
          </div>
        </CardHeader>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {mockTournaments.map((tournament) => (
            <TournamentCard key={tournament.tournamentId} {...tournament} />
          ))}
        </div>
      </div>

      {/* Recent Matches */}
      <div>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Recent Matches</CardTitle>
            <a
              href="/matches"
              className="text-sm font-medium text-brand-primary-600 hover:text-brand-primary-700 transition-colors"
            >
              View All →
            </a>
          </div>
        </CardHeader>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {mockMatches.map((match) => (
            <MatchCard key={match.matchId} {...match} />
          ))}
        </div>
      </div>
    </div>
  );
}
