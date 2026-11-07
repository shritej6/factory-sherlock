import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { StatTile } from './StatTile';

describe('StatTile', () => {
  it('shows the figure and its detail once the value is known', () => {
    render(<StatTile label="Defect rate" value="4.2%" detail="failed / inspected" />);
    expect(screen.getByText('Defect rate')).toBeInTheDocument();
    expect(screen.getByText('4.2%')).toBeInTheDocument();
    expect(screen.getByText('failed / inspected')).toBeInTheDocument();
    expect(screen.queryByText('Loading')).not.toBeInTheDocument();
  });

  it('announces that it is loading while the value is undefined', () => {
    const { container } = render(<StatTile label="Inspections" />);
    expect(screen.getByText('Loading')).toHaveClass('sr-only');
    expect(container.firstElementChild).toHaveAttribute('aria-busy', 'true');
  });
});
