/**
 * Match Detail Page
 * Phase 9, Epic 9.4 - Frontend Boilerplate Scaffolding
 * 
 * Match detail with participants, scores, and result submission.
 * TODO: Integrate with Epic 9.2 SDK (DeltaCrownClient.matches.get)
 */

'use client';

import React, { useState } from 'react';
import { useParams } from 'next/navigation';
import Card, { CardHeader, CardTitle, CardContent } from '../../../components/Card';
import Badge from '../../../components/Badge';
import Button from '../../../components/Button';
import Modal, { ModalFooter } from '../../../components/Modal';
import Input from '../../../components/Input';

export default function MatchDetailPage() {
  const params = useParams();
  const matchId = params?.id as string;
  const [isModalOpen, setIsModalOpen] = useState(false);

  const mockMatch = {
    id: matchId,
    tournament: 'Summer Championship 2025',
    participant1: { id: 'P1', name: 'Team Alpha', score: 2 },
    participant2: { id: 'P2', name: 'Team Beta', score: 1 },
    status: 'completed' as const,
    round: 'Semifinals',
    bracketPosition: 'Upper Bracket',
    scheduledTime: 'Jun 15, 2025 3:00 PM',
    completedTime: 'Jun 15, 2025 4:32 PM',
  };

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-3 mb-2">
          <h1 className="text-3xl font-bold text-neutral-900">Match #{mockMatch.id}</h1>
          <Badge variant="success">Completed</Badge>
        </div>
        <p className="text-neutral-600">{mockMatch.tournament} • {mockMatch.round}</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Match Details</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="p-6 rounded-lg bg-brand-primary-50 border-2 border-brand-primary-500">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-16 h-16 rounded-full bg-gradient-to-br from-brand-primary-500 to-brand-secondary-500 flex items-center justify-center flex-shrink-0">
                    <span className="text-white font-bold text-2xl">
                      {mockMatch.participant1.name.charAt(0)}
                    </span>
                  </div>
                  <div className="flex-1">
                    <h3 className="text-xl font-bold text-neutral-900">{mockMatch.participant1.name}</h3>
                    <Badge variant="success" size="sm" className="mt-1">Winner</Badge>
                  </div>
                  <div className="text-5xl font-bold text-brand-primary-600">{mockMatch.participant1.score}</div>
                </div>
              </div>

              <div className="p-6 rounded-lg bg-neutral-50">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-16 h-16 rounded-full bg-gradient-to-br from-neutral-400 to-neutral-500 flex items-center justify-center flex-shrink-0">
                    <span className="text-white font-bold text-2xl">
                      {mockMatch.participant2.name.charAt(0)}
                    </span>
                  </div>
                  <div className="flex-1">
                    <h3 className="text-xl font-bold text-neutral-900">{mockMatch.participant2.name}</h3>
                    <Badge variant="default" size="sm" className="mt-1">Runner-up</Badge>
                  </div>
                  <div className="text-5xl font-bold text-neutral-600">{mockMatch.participant2.score}</div>
                </div>
              </div>
            </div>

            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-6 border-t border-neutral-200">
              <div>
                <dt className="text-sm font-medium text-neutral-500">Bracket Position</dt>
                <dd className="mt-1 text-base font-semibold text-neutral-900">{mockMatch.bracketPosition}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-neutral-500">Round</dt>
                <dd className="mt-1 text-base font-semibold text-neutral-900">{mockMatch.round}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-neutral-500">Scheduled Time</dt>
                <dd className="mt-1 text-base text-neutral-700">{mockMatch.scheduledTime}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-neutral-500">Completed Time</dt>
                <dd className="mt-1 text-base text-neutral-700">{mockMatch.completedTime}</dd>
              </div>
            </dl>

            <div className="flex gap-3 pt-6 border-t border-neutral-200">
              <Button variant="primary" onClick={() => setIsModalOpen(true)}>Update Score</Button>
              <Button variant="secondary">Reschedule</Button>
              <Button variant="danger">Report Dispute</Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title="Update Match Score" size="md">
        <div className="space-y-4">
          <Input label={mockMatch.participant1.name} type="number" defaultValue={mockMatch.participant1.score} />
          <Input label={mockMatch.participant2.name} type="number" defaultValue={mockMatch.participant2.score} />
        </div>
        <ModalFooter>
          <Button variant="secondary" onClick={() => setIsModalOpen(false)}>Cancel</Button>
          <Button variant="primary">Save Score</Button>
        </ModalFooter>
      </Modal>
    </div>
  );
}
