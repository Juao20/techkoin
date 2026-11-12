import type { ReactNode } from 'react'
import { Button } from '@/components/Button/Button'
import { Checkbox, Radio } from '@/components/Choice/Choice'
import { Field } from '@/components/Field/Field'
import fieldStyles from '@/components/Field/Field.module.css'
import { useBrands, useCities } from '@/lib/catalog'
import { CATEGORY_LABELS, CONDITION_LABELS } from '@/lib/listings'
import { MOBILE_USAGES, PC_USAGES, USAGE_LABELS } from '@/lib/usage'
import {
  clearFilters,
  countActive,
  withFlag,
  withList,
  withSingle,
  type FlagKey,
  type Filters,
  type SingleKey,
} from './filters'
import styles from './FilterPanel.module.css'

type Props = { filters: Filters; onChange: (next: Filters) => void }

function Group({ title, children }: { title: string; children: ReactNode }) {
  return (
    <fieldset className={styles.group}>
      <legend className={styles.legend}>{title}</legend>
      {children}
    </fieldset>
  )
}

function Pick({
  label,
  filters,
  name,
  options,
  onChange,
}: {
  label: string
  filters: Filters
  name: SingleKey
  options: { value: string; label: string }[]
  onChange: (f: Filters) => void
}) {
  return (
    <Field label={label}>
      {({ id }) => (
        <select
          id={id}
          className={fieldStyles.control}
          value={filters.single[name] ?? ''}
          onChange={(e) => onChange(withSingle(filters, name, e.target.value))}
        >
          <option value="">Tous</option>
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      )}
    </Field>
  )
}

const RAM = [4, 8, 16, 32].map((v) => ({ value: String(v), label: `${v} Go et plus` }))
const STORAGE = [64, 128, 256, 512, 1024].map((v) => ({
  value: String(v),
  label: v >= 1024 ? '1 To et plus' : `${v} Go et plus`,
}))

export function FilterPanel({ filters, onChange }: Props) {
  const cities = useCities()
  const category = filters.single.category ?? ''
  const brands = useBrands(category || undefined)
  const isComputer = category === 'laptop' || category === 'desktop'
  const isMobile = category === 'smartphone' || category === 'tablet'
  const flag = (key: FlagKey, label: string) => (
    <Checkbox
      key={key}
      label={label}
      checked={Boolean(filters.flags[key])}
      onChange={(e) => onChange(withFlag(filters, key, e.target.checked))}
    />
  )
  const active = countActive(filters)

  return (
    <div className={styles.panel}>
      <div className={styles.head}>
        <h2 className={styles.title}>Filtres</h2>
        {active > 0 && (
          <Button variant="ghost" onClick={() => onChange(clearFilters(filters))}>
            Tout effacer ({active})
          </Button>
        )}
      </div>

      <Group title="Catégorie">
        <Radio
          name="category"
          label="Toutes"
          checked={!category}
          onChange={() => onChange(withSingle(filters, 'category', ''))}
        />
        {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
          <Radio
            key={value}
            name="category"
            label={label}
            checked={category === value}
            onChange={() => onChange(withSingle(filters, 'category', value))}
          />
        ))}
      </Group>

      <Group title="Prix (FCFA)">
        <div className={styles.row}>
          <Field label="Minimum">
            {({ id }) => (
              <input
                id={id}
                className={fieldStyles.control}
                type="number"
                min={0}
                step={5000}
                inputMode="numeric"
                value={filters.single.price_min ?? ''}
                onChange={(e) => onChange(withSingle(filters, 'price_min', e.target.value))}
              />
            )}
          </Field>
          <Field label="Maximum">
            {({ id }) => (
              <input
                id={id}
                className={fieldStyles.control}
                type="number"
                min={0}
                step={5000}
                inputMode="numeric"
                value={filters.single.price_max ?? ''}
                onChange={(e) => onChange(withSingle(filters, 'price_max', e.target.value))}
              />
            )}
          </Field>
        </div>
      </Group>

      <Group title="État">
        {Object.entries(CONDITION_LABELS).map(([value, label]) => (
          <Checkbox
            key={value}
            label={label}
            checked={(filters.lists.condition ?? []).includes(value)}
            onChange={(e) => onChange(withList(filters, 'condition', value, e.target.checked))}
          />
        ))}
      </Group>

      <Group title="Note d'état">
        {[
          ['A', 'A, comme neuf'],
          ['B', 'B, bon état'],
          ['C', 'C, traces visibles'],
        ].map(([value, label]) => (
          <Checkbox
            key={value}
            label={label ?? value ?? ''}
            checked={(filters.lists.grade ?? []).includes(value ?? '')}
            onChange={(e) => onChange(withList(filters, 'grade', value ?? '', e.target.checked))}
          />
        ))}
      </Group>

      <Group title="Marque">
        {(brands.data ?? []).map((b) => (
          <Checkbox
            key={b.slug}
            label={b.name}
            checked={(filters.lists.brand ?? []).includes(b.slug)}
            onChange={(e) => onChange(withList(filters, 'brand', b.slug, e.target.checked))}
          />
        ))}
      </Group>

      <Group title="Lieu">
        <Pick
          label="Ville"
          filters={filters}
          name="city"
          options={(cities.data ?? []).map((c) => ({ value: c.slug, label: c.name }))}
          onChange={onChange}
        />
      </Group>

      {(isComputer || isMobile || !category) && (
        <Group title="Caractéristiques">
          <Pick
            label="Mémoire vive"
            filters={filters}
            name="ram_min"
            options={RAM}
            onChange={onChange}
          />
          <Pick
            label="Stockage"
            filters={filters}
            name="storage_min"
            options={STORAGE}
            onChange={onChange}
          />
          {isComputer && (
            <>
              <Pick
                label="Type de stockage"
                filters={filters}
                name="storage_type"
                options={[
                  { value: 'ssd', label: 'SSD' },
                  { value: 'hdd', label: 'HDD' },
                ]}
                onChange={onChange}
              />
              <Pick
                label="Clavier"
                filters={filters}
                name="keyboard"
                options={[
                  { value: 'azerty', label: 'AZERTY' },
                  { value: 'qwerty', label: 'QWERTY' },
                ]}
                onChange={onChange}
              />
              {flag('gpu_dedicated', 'Carte graphique dédiée')}
            </>
          )}
          {isMobile && (
            <>
              {flag('5g', '5G')}
              {flag('dual_sim', 'Double SIM')}
              {flag('unlocked', 'Débloqué tout opérateur')}
              {flag('no_replaced_parts', 'Aucune pièce remplacée')}
            </>
          )}
          {category === 'tablet' && (
            <>
              {flag('cellular', 'Avec carte SIM')}
              {flag('stylus', 'Stylet inclus')}
            </>
          )}
        </Group>
      )}

      {(isComputer || isMobile) && (
        <Group title="Usage conseillé">
          <Pick
            label="Je cherche pour"
            filters={filters}
            name="usage"
            options={(isComputer ? PC_USAGES : MOBILE_USAGES).map((u) => ({
              value: u,
              label: USAGE_LABELS[u] ?? u,
            }))}
            onChange={onChange}
          />
        </Group>
      )}

      <Group title="Vendeur">
        <Pick
          label="Type de vendeur"
          filters={filters}
          name="seller_type"
          options={[
            { value: 'shop', label: 'Boutiques' },
            { value: 'individual', label: 'Particuliers' },
          ]}
          onChange={onChange}
        />
        <Pick
          label="Garantie"
          filters={filters}
          name="warranty"
          options={[1, 3, 6, 12].map((m) => ({ value: String(m), label: `${m} mois et plus` }))}
          onChange={onChange}
        />
        {flag('verified', 'Vendeur vérifié')}
        {flag('invoice', 'Facture fournie')}
      </Group>
    </div>
  )
}
