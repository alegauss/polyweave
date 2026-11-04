// Where a picture is wrong, drawn over it (§PW174, §PW687). One component for both places
// a person marks a picture: a sitting's card on the Decide screen and the item view. It
// knows nothing of either: the words, the picture and what the boxes become are handed in.

import { Button } from '@viglet/viglet-design-system'
import { useEffect, useRef, useState } from 'react'

import { inPixels, spanned, type Box } from '@pw/core'

/** Where a file will show once it has come across the desk. */
export const Loading = () => <div data-loading className="h-24 w-48 animate-pulse rounded bg-muted" />

/**
 * A drag draws a box in the picture's own pixels, whatever size it is shown at. The caller
 * turns the boxes into a mask: `review.answer` for a card, `revision.ask` for an item.
 */
export function Marker({
  name,
  source,
  alt,
  help,
  clear,
  boxes,
  onBoxes,
}: {
  /** What the marker is on, for `data-marker`. */
  name: string
  source: string | null
  alt: string
  help: string
  clear: string
  boxes: Box[]
  onBoxes: (boxes: Box[]) => void
}) {
  const picture = useRef<HTMLImageElement>(null)
  const canvas = useRef<HTMLCanvasElement>(null)
  const [start, setStart] = useState<[number, number] | null>(null)
  const [moving, setMoving] = useState<Box | null>(null)
  const at = (event: React.PointerEvent): [number, number] => {
    const frame = canvas.current!.getBoundingClientRect()
    const shown = picture.current!
    return inPixels(event.clientX - frame.left, event.clientY - frame.top, shown.naturalWidth, shown.clientWidth)
  }
  const paint = () => {
    const shown = picture.current
    const pen = canvas.current?.getContext('2d')
    if (!shown || !pen || !canvas.current) return
    canvas.current.width = shown.clientWidth
    canvas.current.height = shown.clientHeight
    const k = shown.naturalWidth / (shown.clientWidth || 1)
    pen.strokeStyle = '#ff3b30'
    pen.lineWidth = 2
    for (const box of moving ? [...boxes, moving] : boxes) {
      pen.strokeRect(box[0] / k, box[1] / k, (box[2] - box[0]) / k, (box[3] - box[1]) / k)
    }
  }
  useEffect(paint)
  return (
    <div data-marker={name} className="flex flex-col gap-2">
      <p className="text-xs text-muted-foreground">{help}</p>
      <div className="relative inline-block self-start">
        {!source && <Loading />}
        {source && (
          <img
            ref={picture}
            src={source}
            alt={alt}
            onLoad={paint}
            className="block max-h-96 w-auto min-w-48 [image-rendering:pixelated]"
          />
        )}
        <canvas
          ref={canvas}
          aria-label={alt}
          className="absolute inset-0 h-full w-full cursor-crosshair touch-none"
          onPointerDown={(event) => setStart(at(event))}
          onPointerMove={(event) => start && setMoving([...start, ...at(event)] as Box)}
          onPointerUp={(event) => {
            if (!start) return
            const box = spanned(start, at(event))
            if (box) onBoxes([...boxes, box])
            setStart(null)
            setMoving(null)
          }}
        />
      </div>
      <Button type="button" size="sm" variant="outline" className="self-start" onClick={() => onBoxes([])}>
        {clear}
      </Button>
    </div>
  )
}
