// A shell command a revision's session runs names no file the scope hook could ask about
// (§PW378), so its writes outside the item are found after it ran, by the revision's
// own hook, and kept as `touched` with why. This follows the session's lines: when a
// Bash call's result comes back, it asks `revision.outside` and turns each write not
// shown yet into the window's own line, so the person sees it in the conversation.

/** One write outside the item, as `revision.outside` lists it. */
export interface Stray {
  file: string
  outside: string
  at: string
}

export class Strays {
  private readonly bash = new Set<string>()
  private readonly shown = new Set<string>()
  private readonly ask: () => Promise<Stray[]>

  constructor(ask: () => Promise<Stray[]>) {
    this.ask = ask
  }

  /** The window's lines for one line of the session: none, or each new write outside. */
  async after(line: string): Promise<string[]> {
    let message: Record<string, any>
    try {
      message = JSON.parse(line)
    } catch {
      return []
    }
    const parts = (message['message']?.['content'] ?? []) as Record<string, any>[]
    if (!Array.isArray(parts)) return []
    if (message['type'] === 'assistant') {
      for (const part of parts) {
        if (part['type'] === 'tool_use' && part['name'] === 'Bash') this.bash.add(String(part['id']))
      }
      return []
    }
    if (message['type'] !== 'user') return []
    const ran = parts.some((part) => part['type'] === 'tool_result' && this.bash.delete(String(part['tool_use_id'])))
    if (!ran) return []
    const found = await this.ask().catch(() => [] as Stray[])
    const lines: string[] = []
    for (const one of found) {
      const key = `${one.file}@${one.at}`
      if (this.shown.has(key)) continue
      this.shown.add(key)
      lines.push(JSON.stringify({ type: 'polyweave_outside', file: one.file, why: one.outside }))
    }
    return lines
  }
}
