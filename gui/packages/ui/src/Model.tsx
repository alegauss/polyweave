// A model member seen in 3D beside its still (§PW601): the .glb its record names, turned
// by drag, zoomed by wheel, turning slowly on its own until touched, and put back where it
// began. three.js is imported only when a card has a model, so a page of pictures never
// loads it, and it ships in the bundle, never from a CDN.

import { Button } from '@viglet/viglet-design-system'
import { useEffect, useRef, useState } from 'react'

import { say, type Words } from '@pw/core'

/** Where a person looked at a model from, as a verdict names a view of it. */
export interface View {
  member: string
  camera: [number, number, number]
  target: [number, number, number]
}

type Held = {
  reset: () => void
  view: () => Omit<View, 'member'>
}

const rounded = (v: { x: number; y: number; z: number }): [number, number, number] => [
  Math.round(v.x * 1000) / 1000,
  Math.round(v.y * 1000) / 1000,
  Math.round(v.z * 1000) / 1000,
]

export function Model({
  source,
  label,
  words,
  onView,
}: {
  source: string
  label: string
  words: Words
  onView?: (view: Omit<View, 'member'>) => void
}) {
  const box = useRef<HTMLDivElement>(null)
  const held = useRef<Held | null>(null)
  const [failed, setFailed] = useState('')

  useEffect(() => {
    let live = true
    let stop = () => {}
    void (async () => {
      const THREE = await import('three')
      const { GLTFLoader } = await import('three/examples/jsm/loaders/GLTFLoader.js')
      const { OrbitControls } = await import('three/examples/jsm/controls/OrbitControls.js')
      const where = box.current
      if (!live || !where) return
      const width = where.clientWidth || 320
      const height = Math.round((width * 9) / 16)
      const renderer = new THREE.WebGLRenderer({ antialias: true })
      renderer.setPixelRatio(window.devicePixelRatio)
      renderer.setSize(width, height)
      where.appendChild(renderer.domElement)
      const scene = new THREE.Scene()
      // The neutral grey a still is rendered on, so the two read alike.
      scene.background = new THREE.Color(0x808080)
      scene.add(new THREE.HemisphereLight(0xffffff, 0x404040, 1.6))
      const key = new THREE.DirectionalLight(0xffffff, 1.4)
      key.position.set(3, 5, 4)
      scene.add(key)
      const camera = new THREE.PerspectiveCamera(35, width / height, 0.01, 1000)
      const controls = new OrbitControls(camera, renderer.domElement)
      controls.enableDamping = true
      controls.autoRotate = true
      controls.autoRotateSpeed = 1.2
      // Turning on its own until a person takes it.
      controls.addEventListener('start', () => (controls.autoRotate = false))
      let frame = 0
      try {
        const gltf = await new GLTFLoader().loadAsync(source)
        if (!live) return
        scene.add(gltf.scene)
        const bounds = new THREE.Box3().setFromObject(gltf.scene)
        const centre = bounds.getCenter(new THREE.Vector3())
        const size = bounds.getSize(new THREE.Vector3()).length() || 1
        const start = centre.clone().add(new THREE.Vector3(0.6, 0.45, 1).normalize().multiplyScalar(size * 1.4))
        camera.near = size / 100
        camera.far = size * 100
        camera.updateProjectionMatrix()
        const home = () => {
          camera.position.copy(start)
          controls.target.copy(centre)
          controls.update()
        }
        home()
        held.current = {
          reset: () => {
            home()
            controls.autoRotate = true
          },
          view: () => ({ camera: rounded(camera.position), target: rounded(controls.target) }),
        }
      } catch (error) {
        setFailed(String((error as Error).message ?? error))
      }
      const tick = () => {
        controls.update()
        renderer.render(scene, camera)
        frame = requestAnimationFrame(tick)
      }
      tick()
      stop = () => {
        cancelAnimationFrame(frame)
        controls.dispose()
        renderer.dispose()
        renderer.domElement.remove()
      }
    })()
    return () => {
      live = false
      stop()
    }
  }, [source])

  return (
    <div className="flex flex-col gap-1">
      <div ref={box} aria-label={label} className="w-full max-w-xl overflow-hidden rounded border" />
      {failed && <p className="text-xs text-destructive">{failed}</p>}
      <div className="flex gap-2">
        <Button type="button" size="sm" variant="outline" onClick={() => held.current?.reset()}>
          {say(words, 'reset_view')}
        </Button>
        {onView && (
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => held.current && onView(held.current.view())}
          >
            {say(words, 'mark_view')}
          </Button>
        )}
      </div>
    </div>
  )
}
