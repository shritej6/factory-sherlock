import { useEffect, useRef } from 'react';
import { NavLink } from 'react-router';

import { useAuth } from '@/hooks/useAuth';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { titleCase } from '@/utils/format';

import { NAV_ITEMS } from './nav';

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

export function Sidebar({ open, onClose }: SidebarProps) {
  const { user, logout } = useAuth();
  const isDesktop = useMediaQuery('(min-width: 1024px)');
  const drawerHidden = !open && !isDesktop;
  const nav = useRef<HTMLElement>(null);

  // The drawer precedes the Menu button in the DOM, so focus must move into it when it opens.
  useEffect(() => {
    if (!open) return;
    nav.current?.querySelector<HTMLAnchorElement>('a')?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open, onClose]);

  return (
    <>
      {open && (
        <button
          type="button"
          tabIndex={-1}
          aria-label="Close navigation"
          className="fixed inset-0 z-20 bg-black/40 lg:hidden"
          onClick={onClose}
        />
      )}
      <aside
        id="primary-navigation"
        inert={drawerHidden}
        className={`fixed inset-y-0 left-0 z-30 flex w-64 flex-col bg-sidebar text-sidebar-ink transition-transform motion-reduce:transition-none lg:static lg:translate-x-0 ${open ? 'translate-x-0' : '-translate-x-full'}`}
        aria-label="Sidebar"
      >
        <div className="border-b border-white/10 px-5 py-4">
          <p className="text-base font-semibold tracking-tight text-white">Factory Sherlock</p>
          <p className="mt-0.5 text-[11px] tracking-wide text-sidebar-ink/70 uppercase">
            Production intelligence
          </p>
        </div>
        <nav ref={nav} aria-label="Primary" className="flex-1 overflow-y-auto px-2 py-3">
          <ul className="flex flex-col gap-0.5">
            {NAV_ITEMS.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.to === '/'}
                  onClick={onClose}
                  className={({ isActive }) =>
                    `block rounded-panel px-3 py-2 text-sm ${isActive ? 'bg-sidebar-active font-medium text-white' : 'text-sidebar-ink hover:bg-white/5 hover:text-white'}`
                  }
                >
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
        <div className="border-t border-white/10 px-5 py-4 text-xs">
          {user && (
            <>
              <p className="font-medium text-white">{user.username}</p>
              <p className="text-sidebar-ink/70">{titleCase(user.role)}</p>
            </>
          )}
          <button
            type="button"
            onClick={logout}
            className="mt-3 rounded-panel border border-white/20 px-2.5 py-1 text-xs text-sidebar-ink hover:bg-white/5 hover:text-white"
          >
            Sign out
          </button>
        </div>
      </aside>
    </>
  );
}
