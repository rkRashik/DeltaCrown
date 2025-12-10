/**
 * Help & Documentation Page
 * Phase 9, Epic 9.4 - Frontend Boilerplate Scaffolding
 * 
 * Help documentation and FAQ for organizers.
 */

'use client';

import React from 'react';
import Card, { CardHeader, CardTitle, CardContent } from '../../components/Card';
import Input from '../../components/Input';

export default function HelpPage() {
  const faqs = [
    {
      question: 'How do I create a new tournament?',
      answer: 'Navigate to the Tournaments page and click the "Create Tournament" button. Fill in the required details including game, format, dates, and participant limits.',
    },
    {
      question: 'How do I approve match results?',
      answer: 'Go to the Results Inbox where you can review all pending match results. Click "Approve" to confirm or "Reject" if there are discrepancies.',
    },
    {
      question: 'How do I manage tournament staff?',
      answer: 'Visit the Staff page to add new staff members, assign roles, and manage permissions for your tournaments.',
    },
    {
      question: 'What tournament formats are supported?',
      answer: 'DeltaCrown supports Single Elimination, Double Elimination, Swiss System, Round Robin, and custom bracket formats.',
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-neutral-900">Help & Documentation</h1>
        <p className="text-neutral-600 mt-2">Find answers to common questions and learn how to use the platform.</p>
      </div>

      <Input
        placeholder="Search documentation..."
        leftIcon={
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" />
          </svg>
        }
      />

      <Card>
        <CardHeader>
          <CardTitle>Frequently Asked Questions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {faqs.map((faq, idx) => (
              <div key={idx} className="pb-6 border-b border-neutral-200 last:border-0 last:pb-0">
                <h3 className="text-lg font-semibold text-neutral-900 mb-2">{faq.question}</h3>
                <p className="text-neutral-700">{faq.answer}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card variant="hoverable" padding="md">
          <div className="text-center">
            <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-brand-primary-100 flex items-center justify-center">
              <svg className="w-6 h-6 text-brand-primary-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
              </svg>
            </div>
            <h3 className="font-semibold text-neutral-900 mb-1">API Documentation</h3>
            <p className="text-sm text-neutral-600">Learn how to integrate with our API</p>
          </div>
        </Card>

        <Card variant="hoverable" padding="md">
          <div className="text-center">
            <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-brand-primary-100 flex items-center justify-center">
              <svg className="w-6 h-6 text-brand-primary-600" fill="currentColor" viewBox="0 0 20 20">
                <path d="M2 5a2 2 0 012-2h7a2 2 0 012 2v4a2 2 0 01-2 2H9l-3 3v-3H4a2 2 0 01-2-2V5z" />
                <path d="M15 7v2a4 4 0 01-4 4H9.828l-1.766 1.767c.28.149.599.233.938.233h2l3 3v-3h2a2 2 0 002-2V9a2 2 0 00-2-2h-1z" />
              </svg>
            </div>
            <h3 className="font-semibold text-neutral-900 mb-1">Community Forum</h3>
            <p className="text-sm text-neutral-600">Connect with other organizers</p>
          </div>
        </Card>

        <Card variant="hoverable" padding="md">
          <div className="text-center">
            <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-brand-primary-100 flex items-center justify-center">
              <svg className="w-6 h-6 text-brand-primary-600" fill="currentColor" viewBox="0 0 20 20">
                <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z" />
                <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z" />
              </svg>
            </div>
            <h3 className="font-semibold text-neutral-900 mb-1">Contact Support</h3>
            <p className="text-sm text-neutral-600">Get help from our support team</p>
          </div>
        </Card>
      </div>
    </div>
  );
}
