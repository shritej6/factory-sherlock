import { NavLink } from 'react-router';

import { NAV_ITEMS } from './nav';

/** Primary navigation as a row of soft keys pinned to the bottom edge, one key per section. */
export function SoftKeyBar() {
  return (
    <footer className="sticky bottom-0 z-20 border-t-2 border-border-strong bg-canvas">
      <nav id="primary-navigation" aria-label="Primary">
        <ul className="flex overflow-x-auto">
          {NAV_ITEMS.map((item) => (
            <li key={item.to} className="min-w-32 flex-1">
              <NavLink
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  `flex h-12 items-center justify-center border-r border-border px-3 text-center font-display text-[13px] leading-tight font-semibold tracking-wider uppercase ${isActive ? 'key-down' : 'key text-ink-muted hover:text-ink'}`
                }
              >
                {item.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </footer>
  );
}
