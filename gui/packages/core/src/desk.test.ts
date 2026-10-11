// The decision screen's facts read as the review page reads them (§PW400).

import { describe, expect, it } from 'vitest'

import { choices, last, ordered, progress, say, status, title, unready, visual, type Sitting, type State, type Words } from './desk'

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

  it('asks for a choice, and for words on anything but an accept', () => {
    expect(unready(null, '')).toBe('need_choice')
    expect(unready('look', '  ')).toBe('need_note')
    expect(unready('accept', '')).toBeNull()
  })
})
