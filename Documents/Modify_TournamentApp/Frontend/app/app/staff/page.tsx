/**
 * Staff Management Page
 * Phase 9, Epic 9.4 - Frontend Boilerplate Scaffolding
 * 
 * Staff listing for tournament organizers.
 * TODO: Integrate with Epic 9.2 SDK (DeltaCrownClient.staff.list)
 */

'use client';

import React from 'react';
import Table from '../../components/Table';
import Badge from '../../components/Badge';
import Button from '../../components/Button';

interface StaffMember {
  id: string;
  name: string;
  email: string;
  role: string;
  status: 'active' | 'inactive';
  assignedTournaments: number;
}

export default function StaffPage() {
  const mockStaff: StaffMember[] = [
    { id: 'S1', name: 'John Doe', email: 'john@example.com', role: 'Administrator', status: 'active', assignedTournaments: 5 },
    { id: 'S2', name: 'Jane Smith', email: 'jane@example.com', role: 'Moderator', status: 'active', assignedTournaments: 3 },
    { id: 'S3', name: 'Bob Johnson', email: 'bob@example.com', role: 'Referee', status: 'inactive', assignedTournaments: 0 },
  ];

  const columns = [
    {
      key: 'name' as keyof StaffMember,
      label: 'Name',
      sortable: true,
    },
    {
      key: 'email' as keyof StaffMember,
      label: 'Email',
      sortable: true,
    },
    {
      key: 'role' as keyof StaffMember,
      label: 'Role',
      sortable: true,
    },
    {
      key: 'status' as keyof StaffMember,
      label: 'Status',
      sortable: true,
      render: (value: StaffMember[keyof StaffMember]) => (
        <Badge variant={value === 'active' ? 'success' : 'default'} size="sm">
          {String(value).charAt(0).toUpperCase() + String(value).slice(1)}
        </Badge>
      ),
    },
    {
      key: 'assignedTournaments' as keyof StaffMember,
      label: 'Assigned',
      sortable: true,
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-neutral-900">Staff Management</h1>
          <p className="text-neutral-600 mt-2">Manage tournament staff and permissions.</p>
        </div>
        <Button variant="primary">Add Staff Member</Button>
      </div>

      <Table columns={columns} data={mockStaff} keyField="id" onRowClick={(row) => console.log(row)} />
    </div>
  );
}
