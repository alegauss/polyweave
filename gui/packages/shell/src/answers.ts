// Watching for the person's answer on the sitting a revision ended in (§PW307). An accept
// closes the revision with its run and its sitting; a look or a number goes back to the
// same session as its next turn. The revision closes on the person's word, never the
// session's.

import { followUp, type Answer } from '@pw/core'

type Call = (operation: string, args: Record<string, unknown>) => Promise<unknown>

interface Watched {
  project: string
  call: Call
  run: Record<string, unknown> | null
  /** The answer already acted on, so one answer is acted on once. */
  seen: string | null
  say(text: string): void
  closed(sitting: string): void
}

interface Opened {
  revision: string
  sitting: string | null
  answer: Answer | null
}

export class Answers {
  private readonly watched = new Map<string, Watched>()

  watch(revision: string, one: Omit<Watched, 'seen'>): void {
    this.watched.set(revision, { ...one, seen: null })
  }

  forget(revision: string): void {
    this.watched.delete(revision)
  }

  /** Read every watched revision once and act on any answer not yet acted on. */
  async look(): Promise<void> {
    for (const [revision, one] of [...this.watched]) {
      const open = (await one.call('revision.open', { root: one.project }).catch(() => null)) as {
        revisions: Opened[]
      } | null
      const mine = open?.revisions.find((r) => r.revision === revision)
      const answer = mine?.answer
      if (!mine?.sitting || !answer || (answer.at ?? '') === one.seen) continue
      one.seen = answer.at ?? ''
      const next = followUp(answer)
      if (!next.close) {
        one.say(next.say)
        continue
      }
      // The person accepted: the run takes their verdict, then the revision closes on it.
      if (one.run) {
        await one.call('verdict.answers', { run: one.run, root: one.project }).catch(() => null)
        await one.call('loop.finish', { run: one.run, root: one.project }).catch(() => null)
      }
      await one.call('revision.close', {
        revision,
        run: String(one.run?.['id'] ?? 'no-run'),
        sitting: mine.sitting,
        root: one.project,
      })
      this.watched.delete(revision)
      one.closed(mine.sitting)
    }
  }
}
