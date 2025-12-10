/**
 * LeaderboardTable Component
 * Phase 9, Epic 9.4 - Frontend Boilerplate Scaffolding
 * 
 * Tournament leaderboard with rank indicators and advancement zones.
 * TODO: Integrate with Epic 9.2 SDK (DeltaCrownClient.tournaments.getLeaderboard)
 */

import React from 'react';
import Badge from './Badge';

interface LeaderboardEntry {
  rank: number;
  playerName: string;
  playerAvatar?: string;
  score: number;
  wins: number;
  losses: number;
  advancementStatus?: 'advance' | 'eliminate' | 'undecided';
}

interface LeaderboardTableProps {
  entries: LeaderboardEntry[];
  showAdvancement?: boolean;
  className?: string;
}

export default function LeaderboardTable({
  entries,
  showAdvancement = true,
  className = '',
}: LeaderboardTableProps) {
  const getAdvancementBadge = (status?: string) => {
    switch (status) {
      case 'advance':
        return <Badge variant="success" size="sm">Advance</Badge>;
      case 'eliminate':
        return <Badge variant="error" size="sm">Eliminated</Badge>;
      case 'undecided':
      default:
        return <Badge variant="warning" size="sm">Undecided</Badge>;
    }
  };

  const getRankBadge = (rank: number) => {
    if (rank === 1)
      return <span className="text-2xl" aria-label="1st place">🥇</span>;
    if (rank === 2)
      return <span className="text-2xl" aria-label="2nd place">🥈</span>;
    if (rank === 3)
      return <span className="text-2xl" aria-label="3rd place">🥉</span>;
    return <span className="text-lg font-bold text-neutral-600">{rank}</span>;
  };

  return (
    <div className={`overflow-x-auto rounded-lg border border-neutral-200 ${className}`}>
      <table className="w-full">
        <thead className="bg-neutral-50 border-b border-neutral-200">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-semibold text-neutral-700 uppercase tracking-wider w-16">
              Rank
            </th>
            <th className="px-6 py-3 text-left text-xs font-semibold text-neutral-700 uppercase tracking-wider">
              Player
            </th>
            <th className="px-6 py-3 text-left text-xs font-semibold text-neutral-700 uppercase tracking-wider w-24">
              Score
            </th>
            <th className="px-6 py-3 text-left text-xs font-semibold text-neutral-700 uppercase tracking-wider w-32">
              Record
            </th>
            {showAdvancement && (
              <th className="px-6 py-3 text-left text-xs font-semibold text-neutral-700 uppercase tracking-wider w-32">
                Status
              </th>
            )}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-neutral-200">
          {entries.length === 0 ? (
            <tr>
              <td colSpan={showAdvancement ? 5 : 4} className="px-6 py-12 text-center text-neutral-500">
                No leaderboard data available
              </td>
            </tr>
          ) : (
            entries.map((entry) => (
              <tr
                key={entry.rank}
                className="transition-colors hover:bg-neutral-50"
              >
                <td className="px-6 py-4 text-center">
                  {getRankBadge(entry.rank)}
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    {entry.playerAvatar ? (
                      <img
                        src={entry.playerAvatar}
                        alt={entry.playerName}
                        className="w-10 h-10 rounded-full border-2 border-neutral-200"
                      />
                    ) : (
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-brand-primary-500 to-brand-secondary-500 flex items-center justify-center">
                        <span className="text-white font-semibold text-sm">
                          {entry.playerName.charAt(0).toUpperCase()}
                        </span>
                      </div>
                    )}
                    <span className="font-medium text-neutral-900">{entry.playerName}</span>
                  </div>
                </td>
                <td className="px-6 py-4 text-lg font-bold text-brand-primary-600">
                  {entry.score}
                </td>
                <td className="px-6 py-4 text-sm text-neutral-600">
                  <span className="font-medium text-success">{entry.wins}W</span>
                  {' - '}
                  <span className="font-medium text-error">{entry.losses}L</span>
                </td>
                {showAdvancement && (
                  <td className="px-6 py-4">
                    {getAdvancementBadge(entry.advancementStatus)}
                  </td>
                )}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
