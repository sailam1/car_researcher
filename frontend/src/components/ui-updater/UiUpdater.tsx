import { useState } from 'react'
import { getVehicle } from '../../api/client'
import { useSessionStore } from '../../store/sessionStore'
import { FilterSection } from './FilterSection'
import { VehicleCard, CompareBar } from './VehicleCard'
import './UiUpdater.css'

export function UiUpdater() {
  const { uiState } = useSessionStore()
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null)

  async function openDetail(id: string) {
    try {
      const v = await getVehicle(id)
      setDetail(v)
    } catch {
      setDetail(null)
    }
  }

  return (
    <div className="ui-updater">
      <header className="ui-header">
        <h1>Cardeko</h1>
        <p>Shortlist vehicles that match your research</p>
      </header>
      <FilterSection
        filters={uiState.filters}
        options={uiState.filter_options}
      />
      <CompareBar />
      {(uiState.shortlist_label ||
        (uiState.candidate_count ?? 0) > 0 ||
        uiState.vehicles.length > 0) && (
        <p className="catalog-banner" role="status" aria-live="polite">
          {uiState.shortlist_label ? (
            <span>{uiState.shortlist_label}</span>
          ) : (
            <>
              Shortlisted{' '}
              <strong>
                {(uiState.candidate_count ?? uiState.catalog_showing ?? uiState.vehicles.length).toLocaleString()}
              </strong>
              {uiState.catalog_total
                ? ` out of ${uiState.catalog_total.toLocaleString()} vehicles`
                : ' vehicles'}
            </>
          )}
          {uiState.vehicles.length > 0 &&
            (uiState.catalog_showing ?? uiState.vehicles.length) <
              (uiState.candidate_count ?? 0) && (
              <span className="catalog-banner-detail">
                {' '}
                — {uiState.vehicles.length.toLocaleString()} cards on screen
              </span>
            )}
        </p>
      )}
      <div className="vehicle-grid">
        {uiState.vehicles.length === 0 ? (
          <p className="empty-hint">
            No matches yet — use chat or filters to build your shortlist.
          </p>
        ) : (
          uiState.vehicles.slice(0, 30).map((v) => (
            <VehicleCard key={v.vehicle_id} vehicle={v} onSelect={openDetail} />
          ))
        )}
      </div>
      {detail && (
        <div className="drawer-overlay" onClick={() => setDetail(null)}>
          <div className="drawer" onClick={(e) => e.stopPropagation()}>
            <button type="button" className="close" onClick={() => setDetail(null)}>
              ×
            </button>
            <h3>
              {String(detail.make)} {String(detail.model)}
            </h3>
            <p>{String(detail.variant)}</p>
            <pre>{JSON.stringify(detail.specs, null, 2)}</pre>
          </div>
        </div>
      )}
    </div>
  )
}
