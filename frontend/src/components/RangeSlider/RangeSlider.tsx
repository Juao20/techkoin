import * as Slider from '@radix-ui/react-slider'
import styles from './RangeSlider.module.css'

type Props = {
  label: string
  min: number
  max: number
  step?: number
  value: [number, number]
  onValueChange: (value: [number, number]) => void
  format?: (value: number) => string
}

export function RangeSlider({ label, min, max, step = 1, value, onValueChange, format }: Props) {
  const fmt = format ?? String
  return (
    <div className={styles.wrap}>
      <div className={styles.head}>
        <span className={styles.label}>{label}</span>
        <span className={styles.values}>
          {fmt(value[0])} – {fmt(value[1])}
        </span>
      </div>
      <Slider.Root
        className={styles.root}
        min={min}
        max={max}
        step={step}
        value={value}
        onValueChange={(v) => onValueChange([v[0], v[1]])}
      >
        <Slider.Track className={styles.track}>
          <Slider.Range className={styles.range} />
        </Slider.Track>
        <Slider.Thumb className={styles.thumb} aria-label={`${label} minimum`} />
        <Slider.Thumb className={styles.thumb} aria-label={`${label} maximum`} />
      </Slider.Root>
    </div>
  )
}
