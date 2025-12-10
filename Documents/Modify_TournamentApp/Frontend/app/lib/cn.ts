/**
 * Classnames Utility (cn)
 * Phase 9, Epic 9.4 - Frontend Boilerplate Scaffolding
 * 
 * Simple utility for conditionally joining classNames together.
 */

export function cn(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ');
}
