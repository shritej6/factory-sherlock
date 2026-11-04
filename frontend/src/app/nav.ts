export interface NavItem {
  to: string;
  label: string;
}

export const NAV_ITEMS: readonly NavItem[] = [
  { to: '/', label: 'Factory Overview' },
  { to: '/machines', label: 'Machine Monitoring' },
  { to: '/orders', label: 'Production Orders' },
  { to: '/batches', label: 'Production Batches' },
  { to: '/quality', label: 'Quality Inspection' },
  { to: '/investigations', label: 'Investigations' },
  { to: '/traceability', label: 'Material Traceability' },
  { to: '/analytics', label: 'Analytics and Reports' },
  { to: '/simulation', label: 'Simulation' },
];
