import { Outlet } from 'react-router';

import { SoftKeyBar } from './SoftKeyBar';
import { StatusBand } from './StatusBand';

/**
 * The shell is laid out like a machine control pendant: a status band across the top, the
 * work area in the middle, and a row of soft keys along the bottom for navigation.
 */
export function AppLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-canvas">
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <StatusBand />
      <main
        id="main"
        tabIndex={-1}
        className="min-w-0 flex-1 px-4 py-5 outline-none sm:px-6 lg:px-8"
      >
        <Outlet />
      </main>
      <SoftKeyBar />
    </div>
  );
}
