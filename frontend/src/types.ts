export type AvailabilityState = 'expected' | 'offered' | 'unavailable'

export interface Person {
  id: string
  name: string
  skills: string[]
  availability: Record<string, AvailabilityState>
  max_hours_per_day: number
  min_rest_minutes: number
  skill_levels?: Record<string, string>
}

export interface ShiftDef {
  id: string
  name: string
  start: string          // "HH:MM"
  end: string            // "HH:MM"
  required_skill: string
  required_count: number
  date: string           // "YYYY-MM-DD"
}

export interface Assignment {
  shift_id: string
  person_ids: string[]
  fulfilled: boolean
}
