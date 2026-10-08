// One session holds an item at a time (§PW306). Two revisions on one item are two
// sessions, and the second waits until the first has ended, so each change is made,
// seen and judged on its own and never on top of another still running.

export class Holding {
  /** The revision holding each item, and when its session ends. */
  private readonly held = new Map<string, { revision: string; ends: Promise<unknown> }>()

  /**
   * Start a revision's session now, or once the one holding its item has ended. The
   * answer names the revision it waits on, or null where it started at once.
   */
  take(item: string, revision: string, begin: () => Promise<unknown>): string | null {
    const before = this.held.get(item)
    const waits = before && before.revision !== revision ? before : null
    const ends = (waits ? waits.ends.catch(() => undefined) : Promise.resolve()).then(begin)
    this.held.set(item, { revision, ends })
    void ends.finally(() => {
      if (this.held.get(item)?.revision === revision) this.held.delete(item)
    })
    return waits ? waits.revision : null
  }
}
