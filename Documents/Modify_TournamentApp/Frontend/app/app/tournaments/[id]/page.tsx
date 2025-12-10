/**
 * Tournament Detail Page
 * Phase 9, Epic 9.4 - Frontend Boilerplate Scaffolding
 * 
 * Tournament detail with tabs for overview, bracket, matches, leaderboard.
 * TODO: Integrate with Epic 9.2 SDK (DeltaCrownClient.tournaments.get)
 */

'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import Tabs from '../../../components/Tabs';
import Badge from '../../../components/Badge';
import LeaderboardTable from '../../../components/LeaderboardTable';
import MatchCard from '../../../components/MatchCard';
import Card, { CardContent, CardHeader, CardTitle } from '../../../components/Card';

export default function TournamentDetailPage() {
  const params = useParams();
  const tournamentId = params?.id as string;

  // TODO: Replace with SDK call
  // const tournament = await client.tournaments.get(tournamentId);
  // const leaderboard = await client.tournaments.getLeaderboard(tournamentId);
  // const matches = await client.tournaments.getMatches(tournamentId);

  const mockTournament = {
    id: tournamentId,
    name: 'Summer Championship 2025',
    gameTitle: 'League of Legends',
    format: 'Single Elimination',
    status: 'in-progress' as const,
    description: 'Join us for the biggest summer tournament of the year! Compete against the best players for glory and prizes.',
    participantCount: 64,
    maxParticipants: 64,
    prizePool: '$10,000',
    tournamentStart: 'Jun 15, 2025',
    registrationEnd: 'Jun 10, 2025',
  };

  const mockLeaderboard = [
    { rank: 1, playerName: 'ProGamer123', score: 450, wins: 9, losses: 0, advancementStatus: 'advance' as const },
    { rank: 2, playerName: 'ElitePlayer99', score: 430, wins: 8, losses: 1, advancementStatus: 'advance' as const },
    { rank: 3, playerName: 'DarkHorse', score: 410, wins: 8, losses: 1, advancementStatus: 'advance' as const },
    { rank: 4, playerName: 'Challenger', score: 390, wins: 7, losses: 2, advancementStatus: 'undecided' as const },
    { rank: 5, playerName: 'Underdog', score: 370, wins: 6, losses: 3, advancementStatus: 'undecided' as const },
  ];

  const mockMatches = [
    {
      matchId: 'M5001',
      participant1: { id: 'P1', name: 'ProGamer123', score: 2 },
      participant2: { id: 'P2', name: 'ElitePlayer99', score: 1 },
      status: 'completed' as const,
      round: 'Semifinals',
      bracketPosition: 'Upper Bracket',
    },
    {
      matchId: 'M5002',
      participant1: { id: 'P3', name: 'DarkHorse', score: undefined },
      participant2: { id: 'P4', name: 'Challenger', score: undefined },
      status: 'scheduled' as const,
      scheduledTime: 'Today, 3:00 PM',
      round: 'Semifinals',
      bracketPosition: 'Upper Bracket',
    },
  ];

  const tabs = [
    {
      id: 'overview',
      label: 'Overview',
      content: (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Tournament Details</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <dt className="text-sm font-medium text-neutral-500">Game</dt>
                  <dd className="mt-1 text-base font-semibold text-neutral-900">{mockTournament.gameTitle}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-neutral-500">Format</dt>
                  <dd className="mt-1 text-base font-semibold text-neutral-900">{mockTournament.format}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-neutral-500">Prize Pool</dt>
                  <dd className="mt-1 text-base font-semibold text-success">{mockTournament.prizePool}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-neutral-500">Participants</dt>
                  <dd className="mt-1 text-base font-semibold text-neutral-900">
                    {mockTournament.participantCount} / {mockTournament.maxParticipants}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-neutral-500">Start Date</dt>
                  <dd className="mt-1 text-base font-semibold text-neutral-900">{mockTournament.tournamentStart}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-neutral-500">Status</dt>
                  <dd className="mt-1">
                    <Badge variant="warning" size="md">In Progress</Badge>
                  </dd>
                </div>
              </dl>
              <div className="mt-6 pt-6 border-t border-neutral-200">
                <h4 className="text-sm font-medium text-neutral-500 mb-2">Description</h4>
                <p className="text-neutral-700">{mockTournament.description}</p>
              </div>
            </CardContent>
          </Card>
        </div>
      ),
    },
    {
      id: 'leaderboard',
      label: 'Leaderboard',
      content: <LeaderboardTable entries={mockLeaderboard} showAdvancement />,
    },
    {
      id: 'matches',
      label: 'Matches',
      content: (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {mockMatches.map((match) => (
            <MatchCard key={match.matchId} {...match} />
          ))}
        </div>
      ),
    },
    {
      id: 'bracket',
      label: 'Bracket',
      content: (
        <Card>
          <CardContent className="text-center py-12">
            <p className="text-neutral-500">Bracket visualization coming soon...</p>
          </CardContent>
        </Card>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <div className="flex items-center gap-3 mb-2">
          <h1 className="text-3xl font-bold text-neutral-900">{mockTournament.name}</h1>
          <Badge variant="warning" size="md">In Progress</Badge>
        </div>
        <p className="text-neutral-600">{mockTournament.gameTitle} • {mockTournament.format}</p>
      </div>

      {/* Tabs */}
      <Tabs tabs={tabs} defaultTab="overview" />
    </div>
  );
}
