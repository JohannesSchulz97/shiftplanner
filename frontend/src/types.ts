export interface Person {
  id: string
  name: string
  skills: string[]
  available: boolean
}

export interface ShiftDef {
  id: string
  name: string
  start: string          // "HH:MM"
  end: string            // "HH:MM"
  required_skill: string
  required_count: number
}

export interface Assignment {
  shift_id: string
  person_ids: string[]
  fulfilled: boolean
}
