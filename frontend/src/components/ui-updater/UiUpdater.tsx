import { useState } from 'react'
import { getVehicle } from '../../api/client'
import { useSessionStore } from '../../store/sessionStore'
import { vehicleSpecChips, vehicleTitle } from '../../utils/vehicle'
import { FilterSection } from './FilterSection'
import { VehicleCard, CompareBar } from './VehicleCard'
import './UiUpdater.css'

export function UiUpdater() {
  const { uiState } = useSessionStore()
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null)

  async function openDetail(id: string) {
    try {
      const v = await getVehicle(id)
      const specs = (v.specs ?? {}) as Record<string, unknown>
      setDetail({
        ...v,
        fuel_type: specs.engineFuelType ?? specs.fuel_type,
        gearbox: specs.gearboxType ?? specs.gearbox,
        power_bhp: specs.enginePowerBhp ?? specs.power_bhp,
        boot_litres: specs.bootLitres ?? specs.boot_litres,
        fuel_economy_l100:
          specs.fuelEconomyCombinedL100 ?? specs.fuel_economy_l100,
        year_from: specs.yearFrom ?? specs.year_from,
        drivetrain: specs.drivetrain,
        pros: (v as { review_snippets?: string[] }).review_snippets ?? [],
      })
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
              {vehicleTitle({
                vehicle_id: String(detail.vehicle_id ?? ''),
                make: String(detail.make ?? ''),
                model: String(detail.model ?? ''),
                variant: String(detail.variant ?? ''),
                image_url: '',
                pros: [],
                cons: [],
              })}
            </h3>
            {detail.variant ? <p className="drawer-variant">{String(detail.variant)}</p> : null}
            <ul className="drawer-specs">
              {vehicleSpecChips({
                vehicle_id: String(detail.vehicle_id ?? ''),
                make: String(detail.make ?? ''),
                model: String(detail.model ?? ''),
                variant: String(detail.variant ?? ''),
                image_url: '',
                pros: [],
                cons: [],
                fuel_type: detail.fuel_type as string | undefined,
                gearbox: detail.gearbox as string | undefined,
                power_bhp: detail.power_bhp as number | undefined,
                boot_litres: detail.boot_litres as number | undefined,
                fuel_economy_l100: detail.fuel_economy_l100 as number | undefined,
                year_from: detail.year_from as number | undefined,
                drivetrain: detail.drivetrain as string | undefined,
                avg_rating: detail.avg_rating as number | undefined,
              }).map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
            {Array.isArray(detail.pros) && (detail.pros as string[]).length > 0 ? (
              <div className="drawer-block">
                <strong>Owner feedback</strong>
                <ul>
                  {(detail.pros as string[]).slice(0, 4).map((p, i) => (
                    <li key={i}>{p}</li>
                  ))}
                </ul>
              </div>
            ) : null}
            {detail.specs && typeof detail.specs === 'object' ? (
              <details className="drawer-raw">
                <summary>All specifications</summary>
                <dl>
                  {Object.entries(detail.specs as Record<string, unknown>)
                    .filter(([, v]) => v != null && v !== '')
                    .slice(0, 24)
                    .map(([k, v]) => (
                      <div key={k}>
                        <dt>{k}</dt>
                        <dd>{String(v)}</dd>
                      </div>
                    ))}
                </dl>
              </details>
            ) : null}
          </div>
        </div>
      )}
    </div>
  )
}
