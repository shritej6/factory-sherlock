import { createBrowserRouter, Navigate } from 'react-router';

import { AnalyticsPage } from '@/features/analytics/AnalyticsPage';
import { BatchesPage } from '@/features/batches/BatchesPage';
import { InvestigationDetailPage } from '@/features/investigations/InvestigationDetailPage';
import { InvestigationsPage } from '@/features/investigations/InvestigationsPage';
import { LoginPage } from '@/features/login/LoginPage';
import { MachinesPage } from '@/features/machines/MachinesPage';
import { OrdersPage } from '@/features/orders/OrdersPage';
import { OverviewPage } from '@/features/overview/OverviewPage';
import { InspectionsPage } from '@/features/quality/InspectionsPage';
import { SimulationPage } from '@/features/simulation/SimulationPage';
import { TraceabilityPage } from '@/features/traceability/TraceabilityPage';

import { AppLayout } from './AppLayout';
import { RequireAuth } from './RequireAuth';

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { path: '/', element: <OverviewPage /> },
          { path: '/machines', element: <MachinesPage /> },
          { path: '/orders', element: <OrdersPage /> },
          { path: '/batches', element: <BatchesPage /> },
          { path: '/quality', element: <InspectionsPage /> },
          { path: '/investigations', element: <InvestigationsPage /> },
          { path: '/investigations/:id', element: <InvestigationDetailPage /> },
          { path: '/traceability', element: <TraceabilityPage /> },
          { path: '/analytics', element: <AnalyticsPage /> },
          { path: '/simulation', element: <SimulationPage /> },
          { path: '*', element: <Navigate to="/" replace /> },
        ],
      },
    ],
  },
]);
