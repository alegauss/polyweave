import { describe, expect, it } from 'vitest'

import { Holding } from './holding'

describe('one session holding an item', () => {
  it('starts the second revision on an item only once the first has ended', async () => {
    const holding = new Holding()
    const order: string[] = []
    let endFirst = () => {}
    const first = new Promise<void>((resolve) => (endFirst = resolve))

    expect(
      holding.take('art/icon.png', 'r1', () => {
        order.push('r1 starts')
        return first
      }),
    ).toBeNull()
    expect(
      holding.take('art/icon.png', 'r2', async () => {
        order.push('r2 starts')
      }),
    ).toBe('r1')
    // Another item is not held by either.
    expect(holding.take('audio/hit.wav', 'r3', async () => order.push('r3 starts'))).toBeNull()

    await new Promise((resolve) => setTimeout(resolve, 10))
    expect(order).toEqual(['r1 starts', 'r3 starts'])
    endFirst()
    await new Promise((resolve) => setTimeout(resolve, 10))
    expect(order).toEqual(['r1 starts', 'r3 starts', 'r2 starts'])
  })
})
