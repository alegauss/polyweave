import { describe, expect, it } from 'vitest'

import { Answers } from './answers'

/** A project whose revision r1 ended in a sitting, answered as the test says. */
function project(answer: { choice: string; why?: string; at: string } | null) {
  const called: [string, Record<string, unknown>][] = []
  const call = async (operation: string, args: Record<string, unknown>) => {
    called.push([operation, args])
    if (operation === 'revision.open') {
      return { revisions: [{ revision: 'r1', sitting: 'review/s1/sitting.json', answer }] }
    }
    return {}
  }
  return { call, called }
}

describe("the person's answer on a revision's sitting", () => {
  it('goes back to the session as its next turn, once, on a look', async () => {
    const { call } = project({ choice: 'look', why: 'too bright', at: 't1' })
    const said: string[] = []
    const answers = new Answers()
    answers.watch('r1', { project: '/g', call, run: null, say: (t) => said.push(t), closed: () => {} })
    await answers.look()
    await answers.look()
    expect(said).toHaveLength(1)
    expect(said[0]).toContain('too bright')
  })

  it('closes the revision with its run and sitting on an accept', async () => {
    const { call, called } = project({ choice: 'accept', at: 't1' })
    const closed: string[] = []
    const answers = new Answers()
    answers.watch('r1', {
      project: '/g',
      call,
      run: { id: 'run1' },
      say: () => {},
      closed: (sitting) => closed.push(sitting),
    })
    await answers.look()
    expect(called.map(([op]) => op)).toEqual([
      'revision.open',
      'verdict.answers',
      'loop.finish',
      'revision.close',
    ])
    expect(called[3]![1]).toMatchObject({ revision: 'r1', run: 'run1', sitting: 'review/s1/sitting.json' })
    expect(closed).toEqual(['review/s1/sitting.json'])
  })

  it('does nothing while no one has answered', async () => {
    const { call, called } = project(null)
    const answers = new Answers()
    answers.watch('r1', { project: '/g', call, run: null, say: () => {}, closed: () => {} })
    await answers.look()
    expect(called.map(([op]) => op)).toEqual(['revision.open'])
  })
})
