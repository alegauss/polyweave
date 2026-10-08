import { describe, expect, it } from 'vitest'

import { reviewArgs } from './reviews'

describe('the review server a project is shown through', () => {
  it('runs the engine that serves the project, as review on any free port', () => {
    const engine = { command: '/g/.venv/bin/python', args: ['-m', 'polyweave', 'serve'], from: 'project' as const }
    expect(reviewArgs(engine, '/g')).toEqual(['-m', 'polyweave', 'review', '--root', '/g', '--port', '0'])
  })
})
