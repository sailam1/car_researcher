import { useCallback } from 'react'
import type { ActiveFilters, DiscoveryPhase, FilterOptions } from '../../types'
import { updateFilters } from '../../api/client'
import { useSessionStore } from '../../store/sessionStore'

interface Props {
  filters: ActiveFilters
  options: FilterOptions | null | undefined
}

export function FilterSection({ filters, options }: Props) {
  const { sessionId, setUiState, setPhase } = useSessionStore()

  const patch = useCallback(
    async (next: ActiveFilters) => {
      if (!sessionId) return
      const res = await updateFilters(sessionId, next)
      setUiState(res.ui_state)
      setPhase(res.discovery_phase as DiscoveryPhase)
    },
    [sessionId, setUiState, setPhase]
  )

  if (!options) return null

  function toggleList(
    key: keyof Pick<
      ActiveFilters,
      'makes' | 'models' | 'engine_fuel_types' | 'gearbox_types' | 'drivetrains'
    >,
    value: string
  ) {
    const cur = [...(filters[key] as string[])]
    const idx = cur.indexOf(value)
    if (idx >= 0) cur.splice(idx, 1)
    else cur.push(value)
    void patch({ ...filters, [key]: cur })
  }

  return (
    <div className="filter-section">
      <h3>Filters</h3>
      <div className="filter-group">
        <label>Make</label>
        <div className="chip-row">
          {options.makes.slice(0, 12).map((m) => (
            <button
              key={m}
              type="button"
              className={filters.makes.includes(m) ? 'chip active' : 'chip'}
              onClick={() => toggleList('makes', m)}
            >
              {m}
            </button>
          ))}
        </div>
      </div>
      <div className="filter-group">
        <label>Fuel</label>
        <div className="chip-row">
          {options.engine_fuel_types.map((f) => (
            <button
              key={f}
              type="button"
              className={
                filters.engine_fuel_types.includes(f) ? 'chip active' : 'chip'
              }
              onClick={() => toggleList('engine_fuel_types', f)}
            >
              {f}
            </button>
          ))}
        </div>
      </div>
      <div className="filter-row">
        <label>
          Min boot (L)
          <input
            type="number"
            min={0}
            max={options.boot_litres_max}
            value={filters.boot_litres_min ?? ''}
            onChange={(e) =>
              void patch({
                ...filters,
                boot_litres_min: e.target.value
                  ? Number(e.target.value)
                  : null,
              })
            }
          />
        </label>
        <label>
          Max economy (L/100)
          <input
            type="number"
            min={0}
            step={0.1}
            value={filters.fuel_economy_l100_max ?? ''}
            onChange={(e) =>
              void patch({
                ...filters,
                fuel_economy_l100_max: e.target.value
                  ? Number(e.target.value)
                  : null,
              })
            }
          />
        </label>
      </div>
    </div>
  )
}
