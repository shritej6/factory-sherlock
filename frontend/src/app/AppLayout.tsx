import { useCallback, useRef, useState } from 'react';
import { Outlet } from 'react-router';

import { Sidebar } from './Sidebar';

export function AppLayout() {
  const [navOpen, setNavOpen] = useState(false);
  const menuButton = useRef<HTMLButtonElement>(null);

  const closeNav = useCallback(() => {
    setNavOpen((wasOpen) => {
      if (wasOpen) menuButton.current?.focus();
      return false;
    });
  }, []);

  return (
    <div className="flex min-h-screen">
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <Sidebar open={navOpen} onClose={closeNav} />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-3 border-b border-border bg-surface px-4 py-2 lg:hidden">
          <button
            ref={menuButton}
            type="button"
            aria-expanded={navOpen}
            aria-controls="primary-navigation"
            onClick={() => setNavOpen(true)}
            className="rounded-panel border border-border px-2.5 py-1 text-sm"
          >
            Menu
          </button>
          <span className="text-sm font-semibold">Factory Sherlock</span>
        </header>
        <main
          id="main"
          tabIndex={-1}
          className="min-w-0 flex-1 px-4 py-5 outline-none sm:px-6 lg:px-8"
        >
          <Outlet />
        </main>
      </div>
    </div>
  );
}
