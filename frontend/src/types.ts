export type DiscoveryPhase =
  | 'welcome'
  | 'broad'
  | 'narrow'
  | 'refining'
  | 'shortlisted'
  | 'done'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp?: string
}

export interface ActiveFilters {
  makes: string[]
  models: string[]
  engine_fuel_types: string[]
  gearbox_types: string[]
  drivetrains: string[]
  year_from_min?: number | null
  year_from_max?: number | null
  power_bhp_min?: number | null
  power_bhp_max?: number | null
  boot_litres_min?: number | null
  fuel_economy_l100_max?: number | null
}

export interface FilterOptions {
  makes: string[]
  models: string[]
  engine_fuel_types: string[]
  gearbox_types: string[]
  drivetrains: string[]
  year_from_min: number
  year_from_max: number
  power_bhp_min: number
  power_bhp_max: number
  boot_litres_max: number
  fuel_economy_l100_max: number
}

export interface VehicleCard {
  vehicle_id: string
  make: string
  model: string
  variant: string
  image_url: string
  fuel_type?: string
  gearbox?: string
  power_bhp?: number
  boot_litres?: number
  fuel_economy_l100?: number
  year_from?: number
  drivetrain?: string
  pros: string[]
  cons: string[]
  reason?: string
  avg_rating?: number
}

export interface UIState {
  filters: ActiveFilters
  vehicles: VehicleCard[]
  filter_options?: FilterOptions | null
  catalog_total?: number
  catalog_showing?: number
  candidate_count?: number
  shortlist_label?: string
}

export interface SessionCreateResponse {
  session_id: string
  messages: ChatMessage[]
  ui_state: UIState
  discovery_phase: DiscoveryPhase
  narrative_summary?: string
}

export interface SessionResponse {
  session_id: string
  messages: ChatMessage[]
  ui_state: UIState
  discovery_phase: DiscoveryPhase
  narrative_summary: string
  candidate_count?: number
}

export interface ChatResponse {
  reply: string
  messages: ChatMessage[]
  ui_state: UIState
  discovery_phase: DiscoveryPhase
}

export interface CompareVehicle {
  vehicle_id: string
  make: string
  model: string
  variant: string
  specs: Record<string, unknown>
  avg_rating?: number
  pros?: string[]
  cons?: string[]
}
