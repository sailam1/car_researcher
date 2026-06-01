import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { compareVehicles } from '../api/client'
import type { CompareVehicle } from '../types'
import './ComparePage.css'

export function ComparePage() {
  const [params] = useSearchParams()
  const ids = params.get('ids')?.split(',').filter(Boolean) ?? []
  const [vehicles, setVehicles] = useState<CompareVehicle[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (ids.length < 2) {
      setError('Select at least two vehicles to compare.')
      return
    }
    compareVehicles(ids)
      .then((r) => {
        setVehicles(r.vehicles)
        setError(null)
      })
      .catch(() => setError('Failed to load comparison.'))
  }, [ids.join(',')])

  const specKeys = [
    'yearFrom',
    'engineFuelType',
    'gearboxType',
    'enginePowerBhp',
    'bootLitres',
    'fuelEconomyCombinedL100',
    'drivetrain',
    'weightKg',
  ]

  return (
    <div className="compare-page">
      <header>
        <Link to="/">← Back to research</Link>
        <h1>Compare vehicles</h1>
      </header>
      {error && <p className="error">{error}</p>}
      {vehicles.length >= 2 && (
        <div className="compare-scroll">
          <table>
            <thead>
              <tr>
                <th>Spec</th>
                {vehicles.map((v) => (
                  <th key={v.vehicle_id}>
                    {v.make} {v.model}
                    <div className="sub">{v.variant}</div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {specKeys.map((key) => (
                <tr key={key}>
                  <td>{key}</td>
                  {vehicles.map((v) => (
                    <td key={v.vehicle_id}>
                      {String(v.specs[key] ?? '—')}
                    </td>
                  ))}
                </tr>
              ))}
              <tr>
                <td>Avg rating</td>
                {vehicles.map((v) => (
                  <td key={v.vehicle_id}>
                    {v.avg_rating != null ? v.avg_rating.toFixed(1) : '—'}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
