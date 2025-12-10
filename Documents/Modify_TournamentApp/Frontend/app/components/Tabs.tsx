/**
 * Tabs Component
 * Phase 9, Epic 9.4 - Frontend Boilerplate Scaffolding
 * 
 * Tab navigation with keyboard support.
 */

'use client';

import React, { useState } from 'react';

interface Tab {
  id: string;
  label: string;
  content: React.ReactNode;
  disabled?: boolean;
}

interface TabsProps {
  tabs: Tab[];
  defaultTab?: string;
  onChange?: (tabId: string) => void;
}

export default function Tabs({ tabs, defaultTab, onChange }: TabsProps) {
  const [activeTab, setActiveTab] = useState(defaultTab || tabs[0]?.id);

  const handleTabChange = (tabId: string) => {
    setActiveTab(tabId);
    onChange?.(tabId);
  };

  const handleKeyDown = (event: React.KeyboardEvent, tabId: string, index: number) => {
    if (event.key === 'ArrowLeft' && index > 0) {
      const prevTab = tabs[index - 1];
      if (!prevTab.disabled) {
        handleTabChange(prevTab.id);
        document.getElementById(`tab-${prevTab.id}`)?.focus();
      }
    } else if (event.key === 'ArrowRight' && index < tabs.length - 1) {
      const nextTab = tabs[index + 1];
      if (!nextTab.disabled) {
        handleTabChange(nextTab.id);
        document.getElementById(`tab-${nextTab.id}`)?.focus();
      }
    }
  };

  const activeTabContent = tabs.find((tab) => tab.id === activeTab)?.content;

  return (
    <div className="w-full">
      {/* Tab List */}
      <div
        className="border-b border-neutral-200 overflow-x-auto"
        role="tablist"
        aria-label="Content tabs"
      >
        <div className="flex gap-1 min-w-max">
          {tabs.map((tab, index) => {
            const isActive = tab.id === activeTab;
            return (
              <button
                key={tab.id}
                id={`tab-${tab.id}`}
                role="tab"
                aria-selected={isActive}
                aria-controls={`panel-${tab.id}`}
                tabIndex={isActive ? 0 : -1}
                disabled={tab.disabled}
                onClick={() => handleTabChange(tab.id)}
                onKeyDown={(e) => handleKeyDown(e, tab.id, index)}
                className={`
                  px-4 py-2.5 text-sm font-medium transition-colors relative
                  focus:outline-none focus:ring-2 focus:ring-brand-primary-500 focus:ring-offset-2 rounded-t-lg
                  ${
                    isActive
                      ? 'text-brand-primary-600 border-b-2 border-brand-primary-600'
                      : 'text-neutral-600 hover:text-brand-primary-600 hover:bg-neutral-50'
                  }
                  ${tab.disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                `}
              >
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Tab Panels */}
      <div className="mt-4">
        {tabs.map((tab) => (
          <div
            key={tab.id}
            id={`panel-${tab.id}`}
            role="tabpanel"
            aria-labelledby={`tab-${tab.id}`}
            hidden={tab.id !== activeTab}
            className="focus:outline-none"
            tabIndex={0}
          >
            {tab.content}
          </div>
        ))}
      </div>
    </div>
  );
}
