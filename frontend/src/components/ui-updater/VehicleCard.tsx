import { Link } from 'react-router-dom'
import type { VehicleCard as VehicleCardType } from '../../types'
import { placeholderUrl } from '../../api/client'
import { useSessionStore } from '../../store/sessionStore'
import {
  resolveApiPath,
  vehicleSpecChips,
  vehicleTitle,
} from '../../utils/vehicle'

interface Props {
  vehicle: VehicleCardType
  onSelect?: (id: string) => void
}

export function VehicleCard({ vehicle, onSelect }: Props) {
  const { compareIds, toggleCompare } = useSessionStore()
  const inCompare = compareIds.includes(vehicle.vehicle_id)
  const title = vehicleTitle(vehicle)
  const chips = vehicleSpecChips(vehicle)
  const imgSrc = resolveApiPath(
    vehicle.image_url || placeholderUrl(vehicle.make || 'default')
  )
  const pros = vehicle.pros ?? []
  const cons = vehicle.cons ?? []

  return (
    <article
      className="vehicle-card"
      onClick={() => onSelect?.(vehicle.vehicle_id)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onSelect?.(vehicle.vehicle_id)}
    >
      <div className="vehicle-card-inner">
        <img
          src={imgSrc}
          alt=""
          className="vehicle-img"
          loading="lazy"
          onError={(e) => {
            ;(e.target as HTMLImageElement).src = resolveApiPath(
              '/api/placeholders/default.png'
            )
          }}
        />
        <div className="vehicle-body">
          <h4>{title}</h4>
          {vehicle.variant ? <p className="variant">{vehicle.variant}</p> : null}
          {chips.length > 0 ? (
            <ul className="specs">
              {chips.map((label) => (
                <li key={label}>{label}</li>
              ))}
            </ul>
          ) : (
            <p className="specs-empty">Specs loading…</p>
          )}
          {pros.length > 0 && (
            <div className="pros-cons">
              <strong>Highlights</strong>
              <ul>
                {pros.slice(0, 2).map((p, i) => (
                  <li key={i}>{p}</li>
                ))}
              </ul>
            </div>
          )}
          {cons.length > 0 && (
            <div className="pros-cons cons">
              <strong>Watch outs</strong>
              <ul>
                {cons.slice(0, 2).map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
            </div>
          )}
          {vehicle.reason ? <p className="reason">{vehicle.reason}</p> : null}
          <label
            className="compare-check"
            onClick={(e) => e.stopPropagation()}
          >
            <input
              type="checkbox"
              checked={inCompare}
              onChange={() => toggleCompare(vehicle.vehicle_id)}
            />
            Add to compare
          </label>
        </div>
      </div>
    </article>
  )
}

export function CompareBar() {
  const { compareIds } = useSessionStore()
  if (compareIds.length === 0) return null
  return (
    <div className="compare-bar">
      <span>{compareIds.length} selected</span>
      <Link to={`/compare?ids=${compareIds.join(',')}`}>Compare →</Link>
    </div>
  )
}
