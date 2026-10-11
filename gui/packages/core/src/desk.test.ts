// The decision screen's facts read as the review page reads them (§PW400).

import { describe, expect, it } from 'vitest'

import {
  choices,
  drawn,
  figures,
  inPixels,
  lanes,
  last,
  measuredOf,
  narrower,
  ordered,
  progress,
  say,
  spanned,
  status,
  title,
  turned,
  unready,
  visual,
  type Sitting,
  type State,
  type Words,
} from './desk'

const WORDS: Words = {
  language: 'pt-BR',
  page: { progress: '{done} de {total}', need_note: 'Diga o que está errado' },
  kinds: { look: { choices: { look: { label: 'Refazer', means: 'Não está certo.', then: '' } } } },
}

const sitting = (manifest: string, families: string[], more: Partial<Sitting> = {}): Sitting => ({
  manifest,
  at: '2026-10-11T10:00:00+00:00',
  choices: {
    accept: { label: 'Aceitar', means: 'Está certo.', then: '' },
    look: 'the look is wrong',
    number: { label: 'Número', means: 'Uma medida errou.', then: '' },
  },
  families: Object.fromEntries(families.map((name) => [name, { sheet: `${manifest}/${name}.png` }])),
  ...more,
})

describe('the decision screen', () => {
  it('fills a word of the catalog and falls back to its key', () => {
    expect(say(WORDS, 'progress', { done: 1, total: 3 })).toBe('1 de 3')
    expect(say(WORDS, 'missing')).toBe('missing')
  })

  it("reads an older sitting's English choice by its key, and offers number only on a failure", () => {
    const one = sitting('a', ['icon'])
    expect(choices(WORDS, one).map(([word, choice]) => [word, choice.label])).toEqual([
      ['accept', 'Aceitar'],
      ['look', 'Refazer'],
    ])
    one.families['icon']!.said = [{ name: 'icon', passed: false, failed: ['edge drifted'] }]
    expect(choices(WORDS, one, one.families['icon']).map(([word]) => word)).toContain('number')
  })

  it('opens the newest sittings with something to answer, folds the finished, and counts', () => {
    const state: State = {
      language: 'pt-BR',
      pending: { assets: [] },
      sittings: [sitting('old', ['a']), sitting('new', ['b', 'c'])],
      answers: [
        { sitting: 'old', family: 'a', choice: 'accept' },
        { sitting: 'new', family: 'b', choice: 'look', why: 'darker' },
      ],
    }
    const { open, done } = ordered(state)
    expect(open.map((one) => one.manifest)).toEqual(['new'])
    expect(done.map((one) => one.manifest)).toEqual(['old'])
    expect(progress(state)).toEqual({ done: 1, total: 2 })
    expect(status(last(state.sittings[1]!, 'b', state.answers))).toBe('look')
    expect(status(last(state.sittings[1]!, 'c', state.answers))).toBe('wait')
  })

  it('shows a line, then films, then the pictures, then the sheet', () => {
    expect(visual({ sheet: 's', members: [{ name: 'l', text: { en: 'Hi' }, who: 'Ada' }] }).kind).toBe('line')
    expect(title('l', { sheet: 's', members: [{ name: 'l', text: { en: 'Hi' }, who: 'Ada' }] })).toBe('Ada')
    expect(visual({ sheet: 's', members: [{ name: 'm', films: [{ label: 'f', path: 'f.png' }] }] }).kind).toBe('films')
    expect(visual({ sheet: 's', members: [{ name: 'p', new: 'p.png' }] }).kind).toBe('pictures')
    expect(visual({ sheet: 's', members: [{ name: 'w', new: 'w.wav', sound: true }] }).kind).toBe('sheet')
  })

  it("keeps a drawn box in the picture's own pixels, and drops one too thin to mean anything", () => {
    // Drawn on a 256-pixel picture shown 128 wide: every point counts twice.
    const start = inPixels(10, 5, 256, 128)
    const end = inPixels(2, 40, 256, 128)
    expect(spanned(start, end)).toEqual([4, 10, 20, 80])
    expect(spanned([3, 3], [4, 40])).toBeNull()
    expect(drawn([{ member: 'a', shapes: [] }, { member: 'b', shapes: [{ box: [0, 0, 4, 4] }] }])).toEqual([
      { member: 'b', shapes: [{ box: [0, 0, 4, 4] }] },
    ])
  })

  it("says a sound's numbers, never its words", () => {
    const member = { name: 'hit', measured: { new: { peak_db: -1.2, loudness: -14, said: 'clipped' } } }
    expect(measuredOf(member, 'new')).toBe('peak_db -1.2, loudness -14')
    expect(measuredOf(member, 'old')).toBe('')
  })

  it("lays a gate run in two lanes, each candidate's numbers in lines", () => {
    const run = {
      id: 'g',
      candidates: [
        { picture: 'a.png', passed: true, failed: [], silhouette_iou: 0.99 },
        {
          picture: 'b.png',
          passed: false,
          failed: ['centroid moved'],
          silhouette_iou: 0.6,
          drift: { line_weight: { value: 4, canon: 3, floor: 0.5, which_way: 'heavier' } },
        },
      ],
    }
    const { kept, refused } = lanes(run)
    expect([kept.map((one) => one.picture), refused.map((one) => one.picture)]).toEqual([['a.png'], ['b.png']])
    expect(figures(WORDS, refused[0]!)).toEqual([
      'b.png: silhouette IoU 0.6',
      'centroid moved',
      'line_weight 4 / 3 ± 0.5, heavier',
    ])
  })

  it('turns each mesh against the one before, and names the floors a canon picture holds open', () => {
    const frames = [{ azimuth: 0, picture: 'f.png' }]
    expect(turned([{ asset: 'm', frames }, { asset: 'n', frames }, { asset: 'm', frames }]).map(([asset, all]) => [asset, all.length])).toEqual([
      ['m', 2],
      ['n', 1],
    ])
    const board = {
      family: 'default',
      palette: [],
      floors: { line_weight: 2, hue: null },
      pictures: [],
      without: { 'c2.png': { line_weight: 1.2, hue: 0.1 } },
    }
    expect(narrower(board, 'c2.png')).toEqual(['line_weight 2 → 1.2'])
    expect(narrower(board, 'c0.png')).toEqual([])
  })

  it('asks for a choice, and for words on anything but an accept', () => {
    expect(unready(null, '')).toBe('need_choice')
    expect(unready('look', '  ')).toBe('need_note')
    expect(unready('accept', '')).toBeNull()
  })
})
