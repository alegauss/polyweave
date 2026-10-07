import './index.css'

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { BRIDGE_KEY, type Bridge } from '@pw/core'

import { App } from './App'
import { start } from './i18n'

const bridge = (window as unknown as Record<string, Bridge>)[BRIDGE_KEY]!

void bridge.smoke().then((smoke) => {
  start(smoke?.language ?? navigator.language)
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App bridge={bridge} smoke={smoke} />
    </StrictMode>,
  )
})
