# ADR-0011: Black industrial control panel interface

## Status

Accepted. Recorded 2026-11-08. Implemented in `frontend/src/styles/index.css`, `frontend/src/app/AppLayout.tsx`, `frontend/src/app/StatusBand.tsx`, `frontend/src/app/SoftKeyBar.tsx`, `frontend/src/utils/chartTheme.ts`, and the font imports in `frontend/src/main.tsx` (commit 3a6ccad). It replaces the light dashboard with a navy sidebar and dark-mode overrides; no earlier ADR covered the interface style, so no record is superseded.

## Context

The first frontend followed a common web dashboard layout: a light canvas, a navy sidebar holding the navigation, rounded cards with drop shadows, and a dark variant selected by `prefers-color-scheme`. It was complete and passed its accessibility review, but the owner judged that it looked like a generic template rather than a tool for a production floor.

Factory Sherlock is meant for engineers who already work with machine controls. CNC controls (Siemens Sinumerik Operate, Heidenhain TNC 7 in its dark mode, Fanuc iHMI) share a vocabulary: a dark field, a status line across the top that is always visible, function keys along the bottom edge, and colour reserved for machine state. The ISA-101 guidance on high-performance HMI gives the same advice for process displays: a neutral background, with colour kept for abnormal conditions so that they stand out.

Constraints on the change:

- No behaviour, route, API call, or permission changes. The nine sections and their screens stay as they are.
- Contrast stays at WCAG 2.1 AA (NFR-6) on every text and surface pair in use.
- The application must work from a clone without network access to third parties, so fonts cannot come from a CDN.
- The screenshots and walkthrough clips are part of the deliverable and are recaptured after the change, so the look has to be settled first.

## Decision

The interface is a single black theme modelled on a CNC control pendant.

- Palette (`frontend/src/styles/index.css`): field `#000000`, panels `#121212`, panel header band `#1a1a1a`, keys `#262626`, hairlines `#333333`. There is no border radius anywhere. Raised elements are drawn with a one-pixel bevel (an inset `box-shadow`) instead of a drop shadow.
- One chrome colour: amber `#ffb000` marks the active soft key, the primary key, links, the focus ring, and text selection. Red `#ff4a3d`, green `#43c56d`, and the other state colours appear only on live status: badges, lamps, pass and fail marks, and alerts. The chart palette in `frontend/src/utils/chartTheme.ts` steps through amber, white, and grey, and keeps green and red for pass and fail.
- Type: Barlow Condensed for page titles, panel titles, readout figures, buttons, and soft keys; Barlow for body text; JetBrains Mono for identifiers, timestamps, and SQL. The three families are self-hosted through the `@fontsource` packages imported in `frontend/src/main.tsx`; nothing loads from a CDN.
- Layout: `AppLayout.tsx` renders `StatusBand.tsx` above `main` and `SoftKeyBar.tsx` below it. The status band is a `header` (banner landmark) with the product name, one lamp per machine from `useMachines` showing its code and state, a live clock, the signed-in user and role, and Sign out. The soft-key bar is a sticky `footer` holding a `nav` labelled "Primary" with one `NavLink` key per section of `nav.ts`. `Sidebar.tsx` and `hooks/useMediaQuery.ts` are deleted.
- Components: `StatTile` is an instrument readout with the figure large and the label beneath; `StatusBadge` is a square lamp followed by the state word; panel headers sit on the `#1a1a1a` band; tables use tighter rows with sentence-case condensed headers; `EmptyState` is a dashed outline; notices carry a 4 px rule on the left.
- Narrow screens: there is no drawer and no Menu button. The soft-key row scrolls horizontally.
- Accessibility is kept: the skip link, focus management on route change, and the landmarks banner, main, navigation "Primary", and contentinfo. Contrast ratios computed from the token values: muted text `#a3a3a3` on a key `#262626` is 6.0:1 (the lowest pair in use); faint text `#8a8a8a` is 5.5:1 on a panel `#121212` and 5.0:1 on `#1a1a1a`; amber on black and black on amber are both 11.5:1; status text on its soft background is at least 5.8:1 (fault `#ff4a3d` on `#2b0f0d`); idle `#9a9a9a` on `#1e1e1e` is 5.9:1.

## Consequences

Positive:

- Colour carries one meaning. On screens of neutral panels, a red or amber state lamp is the only element that draws the eye, which is what the status band and the machine cards are for.
- The status band shows every machine's state on every screen, so an engineer on the Orders screen still sees that a machine is in fault.
- Navigation is one row at the bottom, so the same markup serves wide and narrow screens. The drawer, the Menu button, the media-query hook, and the focus handling the drawer needed are gone.
- One theme halves the number of colour pairs to check and removes the dark-mode overrides from the stylesheet.

Negative or accepted costs:

- There is no light theme and no user setting. Someone who needs a light background has to use a browser or operating system override.
- The status band reads the machine list through `useMachines` on every screen, and the clock re-renders once a second inside the band only.
- A condensed display face is less readable than a regular face at small sizes. It is limited to short strings (titles, figures, keys); body text and tables use Barlow.
- Three font families add eight CSS imports and their font files to the build. Nothing is fetched from a third party.
- The fourteen screenshots and five walkthrough clips made before this change show the old look and have to be recaptured (tracked in `docs/media/`).
- Contrast is computed from the token values and is not asserted by a test, as in the 2026-11-07 accessibility pass. No screen-reader session has been recorded for the new layout.

## Alternatives considered

- Keep the light theme and refine the dark-mode overrides. Rejected: the complaint was about the look, not the contrast, and a refined light dashboard would still read as a generic template. Two themes also double the colour pairs to verify.
- A control-room SCADA grey palette (mid-grey field, pale panels, saturated process colours). Rejected: it is a recognised HMI style, but a mid-grey field leaves less contrast headroom for muted text, and the screens would stay closer to the light dashboard than to a machine control.
- A terminal look with monospace type everywhere. Rejected: tables of numbers and long investigation narratives are harder to scan in one monospace face, and identifiers and SQL would lose the distinction JetBrains Mono gives them now.
- A brutalist signage look (heavy outlines, large flat colour blocks, oversized type). Rejected: it spends colour on decoration, which conflicts with the rule that colour means machine state, and large blocks reduce the number of rows a table can show.
