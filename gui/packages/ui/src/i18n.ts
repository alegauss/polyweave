// Every word on screen comes from a catalog (§PW303), as the review page's do (§PW287):
// `en` and `pt-BR`, the same pair, so a person reads the window in the language they
// judge in.

import i18next from 'i18next'
import { initReactI18next } from 'react-i18next'

import en from './locales/en.json'
import ptBR from './locales/pt-BR.json'

export const CATALOGS = { en, 'pt-BR': ptBR } as const
export type Language = keyof typeof CATALOGS

/** The catalog a language tag reads in: Portuguese in pt-BR, anything else in English. */
export function language(tag: string | undefined): Language {
  return tag?.toLowerCase().startsWith('pt') ? 'pt-BR' : 'en'
}

export function start(tag: string | undefined): typeof i18next {
  void i18next.use(initReactI18next).init({
    resources: { en: { translation: en }, 'pt-BR': { translation: ptBR } },
    lng: language(tag),
    fallbackLng: 'en',
    interpolation: { escapeValue: false },
  })
  return i18next
}
