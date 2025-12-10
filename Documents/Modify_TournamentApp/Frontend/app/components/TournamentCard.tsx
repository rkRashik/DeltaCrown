/**
 * TournamentCard Component
 * Phase 9, Epic 9.4 - Frontend Boilerplate Scaffolding
 * 
 * Tournament display card with game icon, name, format, status, dates, and CTA.
 * TODO: Integrate with Epic 9.2 SDK (DeltaCrownClient.tournaments.list)
 */

import React from 'react';
import Link from 'next/link';
import Card from './Card';
import Badge from './Badge';
import Button from './Button';

interface TournamentCardProps {
  tournamentId: string;
  name: string;
  gameTitle: string;
  gameIcon?: string;
  format: string;
  status: 'draft' | 'registration-open' | 'in-progress' | 'completed' | 'cancelled';
  registrationStart?: string;
  registrationEnd?: string;
  tournamentStart?: string;
  participantCount?: number;
  maxParticipants?: number;
  prizePool?: string;
  onClick?: () => void;
  className?: string;
}

export default function TournamentCard({
  tournamentId,
  name,
  gameTitle,
  gameIcon,
  format,
  status,
  registrationStart,
  registrationEnd,
  tournamentStart,
  participantCount,
  maxParticipants,
  prizePool,
  onClick,
  className = '',
}: TournamentCardProps) {
  const getStatusBadge = (tournamentStatus: string) => {
    switch (tournamentStatus) {
      case 'draft':
        return <Badge variant="default" size="sm">Draft</Badge>;
      case 'registration-open':
        return <Badge variant="success" size="sm">Registration Open</Badge>;
      case 'in-progress':
        return <Badge variant="warning" size="sm">In Progress</Badge>;
      case 'completed':
        return <Badge variant="info" size="sm">Completed</Badge>;
      case 'cancelled':
        return <Badge variant="error" size="sm">Cancelled</Badge>;
      default:
        return <Badge variant="default" size="sm">{tournamentStatus}</Badge>;
    }
  };

  const CardWrapper = onClick ? 'div' : Link;
  const wrapperProps = onClick
    ? { onClick, className: 'cursor-pointer' }
    : { href: `/tournaments/${tournamentId}` };

  return (
    <CardWrapper {...wrapperProps}>
      <Card variant="hoverable" padding="none" className={className}>
        {/* Header with Game Icon */}
        <div className="relative h-32 bg-gradient-to-br from-brand-primary-500 to-brand-secondary-600 rounded-t-lg overflow-hidden">
          {gameIcon ? (
            <img
              src={gameIcon}
              alt={gameTitle}
              className="w-full h-full object-cover opacity-20"
            />
          ) : (
            <div className="absolute inset-0 flex items-center justify-center">
              <svg className="w-16 h-16 text-white opacity-30" fill="currentColor" viewBox="0 0 20 20">
                <path d="M11 17a1 1 0 001.447.894l4-2A1 1 0 0017 15V9.236a1 1 0 00-1.447-.894l-4 2a1 1 0 00-.553.894V17zM15.211 6.276a1 1 0 000-1.788l-4.764-2.382a1 1 0 00-.894 0L4.789 4.488a1 1 0 000 1.788l4.764 2.382a1 1 0 00.894 0l4.764-2.382zM4.447 8.342A1 1 0 003 9.236V15a1 1 0 00.553.894l4 2A1 1 0 009 17v-5.764a1 1 0 00-.553-.894l-4-2z" />
              </svg>
            </div>
          )}
          <div className="absolute top-4 left-4 right-4 flex items-start justify-between">
            <div className="flex flex-col gap-1">
              <Badge variant="primary" size="sm" className="bg-white/90 text-brand-primary-700">
                {gameTitle}
              </Badge>
              {getStatusBadge(status)}
            </div>
            {prizePool && (
              <div className="bg-white/90 backdrop-blur-sm px-3 py-1 rounded-full">
                <span className="text-sm font-bold text-brand-primary-700">{prizePool}</span>
              </div>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          <h3 className="text-lg font-bold text-neutral-900 mb-2 line-clamp-2">
            {name}
          </h3>

          <div className="space-y-2 mb-4">
            <div className="flex items-center gap-2 text-sm text-neutral-600">
              <svg className="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
                <path
                  fillRule="evenodd"
                  d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z"
                  clipRule="evenodd"
                />
              </svg>
              <span className="font-medium">{format}</span>
            </div>

            {participantCount !== undefined && maxParticipants !== undefined && (
              <div className="flex items-center gap-2 text-sm text-neutral-600">
                <svg className="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9 6a3 3 0 11-6 0 3 3 0 016 0zM17 6a3 3 0 11-6 0 3 3 0 016 0zM12.93 17c.046-.327.07-.66.07-1a6.97 6.97 0 00-1.5-4.33A5 5 0 0119 16v1h-6.07zM6 11a5 5 0 015 5v1H1v-1a5 5 0 015-5z" />
                </svg>
                <span>
                  <span className="font-medium">{participantCount}</span> / {maxParticipants} participants
                </span>
              </div>
            )}

            {tournamentStart && (
              <div className="flex items-center gap-2 text-sm text-neutral-600">
                <svg className="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z"
                    clipRule="evenodd"
                  />
                </svg>
                <span>Starts: {tournamentStart}</span>
              </div>
            )}

            {registrationEnd && status === 'registration-open' && (
              <div className="flex items-center gap-2 text-sm text-warning">
                <svg className="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"
                    clipRule="evenodd"
                  />
                </svg>
                <span className="font-medium">Registration ends: {registrationEnd}</span>
              </div>
            )}
          </div>

          {/* CTA */}
          <Button variant="primary" size="sm" fullWidth>
            View Tournament
          </Button>
        </div>
      </Card>
    </CardWrapper>
  );
}
