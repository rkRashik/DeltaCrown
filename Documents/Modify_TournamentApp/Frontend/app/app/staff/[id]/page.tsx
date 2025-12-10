/**
 * Staff Detail Page
 * Phase 9, Epic 9.4 - Frontend Boilerplate Scaffolding
 * 
 * Individual staff member details and permissions.
 * TODO: Integrate with Epic 9.2 SDK (DeltaCrownClient.staff.get)
 */

'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import Card, { CardHeader, CardTitle, CardContent } from '../../../components/Card';
import Badge from '../../../components/Badge';
import Button from '../../../components/Button';

export default function StaffDetailPage() {
  const params = useParams();
  const staffId = params?.id as string;

  const mockStaff = {
    id: staffId,
    name: 'John Doe',
    email: 'john@example.com',
    role: 'Administrator',
    status: 'active' as const,
    joinedDate: 'Jan 15, 2025',
    assignedTournaments: ['Summer Championship 2025', 'Weekly Open #47', 'Valorant Qualifier'],
  };

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-3 mb-2">
          <h1 className="text-3xl font-bold text-neutral-900">{mockStaff.name}</h1>
          <Badge variant="success">Active</Badge>
        </div>
        <p className="text-neutral-600">{mockStaff.role}</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Staff Information</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <dt className="text-sm font-medium text-neutral-500">Email</dt>
              <dd className="mt-1 text-base text-neutral-900">{mockStaff.email}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-neutral-500">Role</dt>
              <dd className="mt-1 text-base text-neutral-900">{mockStaff.role}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-neutral-500">Joined</dt>
              <dd className="mt-1 text-base text-neutral-900">{mockStaff.joinedDate}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-neutral-500">Status</dt>
              <dd className="mt-1"><Badge variant="success">Active</Badge></dd>
            </div>
          </dl>

          <div className="mt-6 pt-6 border-t border-neutral-200">
            <h4 className="text-sm font-medium text-neutral-500 mb-3">Assigned Tournaments</h4>
            <ul className="space-y-2">
              {mockStaff.assignedTournaments.map((tournament, idx) => (
                <li key={idx} className="text-neutral-700">• {tournament}</li>
              ))}
            </ul>
          </div>

          <div className="flex gap-3 mt-6 pt-6 border-t border-neutral-200">
            <Button variant="primary">Edit Permissions</Button>
            <Button variant="secondary">View Activity Log</Button>
            <Button variant="danger">Deactivate</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
