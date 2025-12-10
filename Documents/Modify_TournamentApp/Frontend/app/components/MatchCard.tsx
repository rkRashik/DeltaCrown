/**
 * MatchCard Component
 * Phase 9, Epic 9.4 - Frontend Boilerplate Scaffolding
 * 
 * Match display card for participants, scores, status, and scheduled time.
 * TODO: Integrate with Epic 9.2 SDK (DeltaCrownClient.matches.get)
 */

import React from 'react';
import Link from 'next/link';
import Card from './Card';
import Badge from './Badge';

interface Participant {
  id: string;
  name: string;
  avatar?: string;
  score?: number;
}

interface MatchCardProps {
  matchId: string;
  participant1: Participant;
  participant2: Participant;
  status: 'scheduled' | 'in-progress' | 'completed' | 'disputed';
  scheduledTime?: string;
  round?: string;
  bracketPosition?: string;
  onClick?: () => void;
  className?: string;
}

export default function MatchCard({
  matchId,
  participant1,
  participant2,
  status,
  scheduledTime,
  round,
  bracketPosition,
  onClick,
  className = '',
}: MatchCardProps) {
  const getStatusBadge = (matchStatus: string) => {
    switch (matchStatus) {
      case 'scheduled':
        return <Badge variant="info" size="sm">Scheduled</Badge>;
      case 'in-progress':
        return <Badge variant="warning" size="sm">In Progress</Badge>;
      case 'completed':
        return <Badge variant="success" size="sm">Completed</Badge>;
      case 'disputed':
        return <Badge variant="error" size="sm">Disputed</Badge>;
      default:
        return <Badge variant="default" size="sm">{matchStatus}</Badge>;
    }
  };

  const renderParticipant = (participant: Participant, isWinner: boolean) => (
    <div className={`flex items-center gap-3 p-3 rounded-lg ${isWinner ? 'bg-brand-primary-50' : 'bg-neutral-50'}`}>
      {participant.avatar ? (
        <img
          src={participant.avatar}
          alt={participant.name}
          className="w-10 h-10 rounded-full border-2 border-neutral-200"
        />
      ) : (
        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-brand-primary-500 to-brand-secondary-500 flex items-center justify-center flex-shrink-0">
          <span className="text-white font-semibold text-sm">
            {participant.name.charAt(0).toUpperCase()}
          </span>
        </div>
      )}
      <span className={`font-medium flex-1 truncate ${isWinner ? 'text-brand-primary-700' : 'text-neutral-900'}`}>
        {participant.name}
      </span>
      {participant.score !== undefined && (
        <span className={`text-2xl font-bold ${isWinner ? 'text-brand-primary-600' : 'text-neutral-600'}`}>
          {participant.score}
        </span>
      )}
    </div>
  );

  const winner =
    status === 'completed' && participant1.score !== undefined && participant2.score !== undefined
      ? participant1.score > participant2.score
        ? participant1.id
        : participant2.id
      : null;

  const CardWrapper = onClick ? 'div' : Link;
  const wrapperProps = onClick
    ? { onClick, className: 'cursor-pointer' }
    : { href: `/matches/${matchId}` };

  return (
    <CardWrapper {...wrapperProps}>
      <Card variant="hoverable" padding="md" className={className}>
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            {getStatusBadge(status)}
            {round && (
              <span className="text-sm text-neutral-600">
                {round}
              </span>
            )}
            {bracketPosition && (
              <span className="text-sm text-neutral-500">
                • {bracketPosition}
              </span>
            )}
          </div>
          {scheduledTime && (
            <div className="flex items-center gap-1 text-sm text-neutral-600">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"
                  clipRule="evenodd"
                />
              </svg>
              <span>{scheduledTime}</span>
            </div>
          )}
        </div>

        {/* Participants */}
        <div className="space-y-2">
          {renderParticipant(participant1, winner === participant1.id)}
          <div className="flex items-center justify-center text-neutral-400">
            <span className="text-sm font-medium">VS</span>
          </div>
          {renderParticipant(participant2, winner === participant2.id)}
        </div>

        {/* Footer */}
        <div className="mt-4 pt-4 border-t border-neutral-200 flex items-center justify-between">
          <span className="text-xs text-neutral-500">Match #{matchId}</span>
          <div className="flex items-center gap-1 text-sm text-brand-primary-600 font-medium">
            <span>View Details</span>
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                clipRule="evenodd"
              />
            </svg>
          </div>
        </div>
      </Card>
    </CardWrapper>
  );
}
