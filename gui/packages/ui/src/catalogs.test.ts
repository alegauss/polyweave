import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'

import { describe, expect, it } from 'vitest'

import { KINDS } from '@pw/core'

import en from './locales/en.json'
import ptBR from './locales/pt-BR.json'
import { language } from './i18n'

function keys(tree: object, prefix = ''): string[] {
  return Object.entries(tree).flatMap(([key, value]) =>
    typeof value === 'object' ? keys(value, `${prefix}${key}.`) : [`${prefix}${key}`],
  )
}

describe('the catalogs', () => {
  it('say the same things in both languages', () => {
    expect(keys(ptBR).sort()).toEqual(keys(en).sort())
  })

  it('name every kind the inventory lists, and every record state', () => {
    for (const kind of KINDS) expect(keys(en)).toContain(`kind.${kind}`)
    for (const state of ['sound', 'changed', 'missing', 'outdated', 'unrecorded', 'unbuilt'])
      expect(keys(en)).toContain(`record.${state}`)
  })

  it('cover every key the screens ask for', () => {
    const here = import.meta.dirname
    const asked = readdirSync(here)
      .filter((name) => name.endsWith('.tsx'))
      .flatMap((name) => [...readFileSync(join(here, name), 'utf8').matchAll(/\bt\('([a-z_.]+)'/g)])
      .map((found) => found[1]!)
    expect(asked.length).toBeGreaterThan(5)
    for (const key of asked) expect(keys(en)).toContain(key)
  })

  it('read Portuguese for pt and English for anything else', () => {
    expect(language('pt-BR')).toBe('pt-BR')
    expect(language('pt')).toBe('pt-BR')
    expect(language('en-US')).toBe('en')
    expect(language(undefined)).toBe('en')
  })
})
