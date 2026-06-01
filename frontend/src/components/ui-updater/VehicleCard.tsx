import { Link } from 'react-router-dom'
import type { VehicleCard as VehicleCardType } from '../../types'
import { placeholderUrl } from '../../api/client'
import { useSessionStore } from '../../store/sessionStore'

interface Props {
  vehicle: VehicleCardType
  onSelect?: (id: string) => void
}

export function VehicleCard({ vehicle, onSelect }: Props) {
  const { compareIds, toggleCompare } = useSessionStore()
  const inCompare = compareIds.includes(vehicle.vehicle_id)
  const img =
    vehicle.image_url.startsWith('/api')
      ? vehicle.image_url
      : placeholderUrl(vehicle.make)

  return (
    <article
      className="vehicle-card"
      onClick={() => onSelect?.(vehicle.vehicle_id)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onSelect?.(vehicle.vehicle_id)}
    >
      <img
        src={img}
        alt=""
        className="vehicle-img"
        onError={(e) => {
          ;(e.target as HTMLImageElement).src = '/api/placeholders/default.png'
        }}
      />
      <div className="vehicle-body">
        <h4>
          {[vehicle.make, vehicle.model].filter(Boolean).join(' ') || 'Unknown vehicle'}
        </h4>
        {vehicle.variant ? <p className="variant">{vehicle.variant}</p> : null}
        <ul className="specs">
          {vehicle.year_from != null && (
            <li>{Math.round(vehicle.year_from)}+</li>
          )}
          {vehicle.fuel_type && <li>{vehicle.fuel_type}</li>}
          {vehicle.gearbox && <li>{vehicle.gearbox}</li>}
          {vehicle.drivetrain && <li>{vehicle.drivetrain}</li>}
          {vehicle.power_bhp != null && <li>{Math.round(vehicle.power_bhp)} bhp</li>}
          {vehicle.boot_litres != null && <li>{Math.round(vehicle.boot_litres)} L boot</li>}
          {vehicle.fuel_economy_l100 != null && (
            <li>{vehicle.fuel_economy_l100.toFixed(1)} L/100</li>
          )}
          {vehicle.avg_rating != null && (
            <li>★ {vehicle.avg_rating.toFixed(1)}</li>
          )}
        </ul>
        {vehicle.pros.length > 0 && (
          <div className="pros-cons">
            <strong>Pros</strong>
            <ul>
              {vehicle.pros.slice(0, 2).map((p, i) => (
                <li key={i}>{p}</li>
              ))}
            </ul>
          </div>
        )}
        {vehicle.cons.length > 0 && (
          <div className="pros-cons cons">
            <strong>Cons</strong>
            <ul>
              {vehicle.cons.slice(0, 2).map((c, i) => (
                <li key={i}>{c}</li>
              ))}
            </ul>
          </div>
        )}
        {vehicle.reason && <p className="reason">{vehicle.reason}</p>}
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
