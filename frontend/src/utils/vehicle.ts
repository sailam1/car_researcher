import { placeholderUrl } from '../api/client'
import { API_BASE_URL, API_PREFIX } from '../api/config'
import type { UIState, VehicleCard } from '../types'

function num(v: unknown): number | undefined {
  if (v == null || v === '') return undefined
  const n = Number(v)
  return Number.isFinite(n) ? n : undefined
}

function str(v: unknown): string {
  if (v == null) return ''
  const s = String(v).trim()
  if (s === 'nan' || s === 'None') return ''
  return s
}

/** Normalize API / session payloads (snake_case or legacy DuckDB keys). */
export function normalizeVehicleCard(raw: unknown): VehicleCard {
  const r = (raw && typeof raw === 'object' ? raw : {}) as Record<string, unknown>
  const make = str(r.make)
  const model = str(r.model)
  const variant = str(r.variant)
  const vehicle_id = str(r.vehicle_id ?? r.vehicleId) || `unknown-${make}-${model}`
  const imageRaw = str(r.image_url ?? r.imageUrl)

  return {
    vehicle_id,
    make,
    model,
    variant,
    image_url: imageRaw || placeholderUrl(make || 'default'),
    fuel_type: str(r.fuel_type ?? r.engineFuelType ?? r.fuelType) || undefined,
    gearbox: str(r.gearbox ?? r.gearboxType) || undefined,
    power_bhp: num(r.power_bhp ?? r.enginePowerBhp),
    boot_litres: num(r.boot_litres ?? r.bootLitres),
    fuel_economy_l100: num(r.fuel_economy_l100 ?? r.fuelEconomyCombinedL100),
    year_from: num(r.year_from ?? r.yearFrom),
    drivetrain: str(r.drivetrain) || undefined,
    pros: Array.isArray(r.pros) ? r.pros.map((p) => str(p)).filter(Boolean) : [],
    cons: Array.isArray(r.cons) ? r.cons.map((p) => str(p)).filter(Boolean) : [],
    reason: str(r.reason) || undefined,
    avg_rating: num(r.avg_rating ?? r.avgRating),
  }
}

export function normalizeUiState(ui: UIState): UIState {
  return {
    ...ui,
    vehicles: (ui.vehicles ?? []).map((v) => normalizeVehicleCard(v)),
  }
}

/** Turn `/api/...` paths into absolute backend URLs in production. */
export function resolveApiPath(path: string): string {
  const p = (path || '').trim()
  if (!p) return `${API_PREFIX}/placeholders/default.png`
  if (p.startsWith('http://') || p.startsWith('https://')) return p
  if (API_BASE_URL && p.startsWith('/')) return `${API_BASE_URL}${p}`
  return p
}

export function vehicleTitle(v: VehicleCard): string {
  const title = [v.make, v.model].filter(Boolean).join(' ')
  return title || 'Unknown vehicle'
}

export function vehicleSpecChips(v: VehicleCard): string[] {
  const chips: string[] = []
  if (v.year_from != null) chips.push(`${Math.round(v.year_from)}+`)
  if (v.fuel_type) chips.push(v.fuel_type)
  if (v.gearbox) chips.push(v.gearbox)
  if (v.drivetrain) chips.push(v.drivetrain)
  if (v.power_bhp != null) chips.push(`${Math.round(v.power_bhp)} bhp`)
  if (v.boot_litres != null) chips.push(`${Math.round(v.boot_litres)} L boot`)
  if (v.fuel_economy_l100 != null) chips.push(`${v.fuel_economy_l100.toFixed(1)} L/100km`)
  if (v.avg_rating != null) chips.push(`★ ${v.avg_rating.toFixed(1)}`)
  return chips
}
