import type { Person, ShiftDef, Assignment } from '@/types'

// Colour per skill (falls back to slate)
const SKILL_PALETTE: Record<string, { block: string; label: string; badge: string }> = {
  physio:       { block: 'border-violet-200 bg-violet-50',  label: 'text-violet-800', badge: 'bg-violet-100 text-violet-700' },
  shift_leader: { block: 'border-blue-200 bg-blue-50',      label: 'text-blue-800',   badge: 'bg-blue-100 text-blue-700'   },
  medic:        { block: 'border-emerald-200 bg-emerald-50', label: 'text-emerald-800', badge: 'bg-emerald-100 text-emerald-700' },
}

const FALLBACK = { block: 'border-slate-200 bg-slate-50', label: 'text-slate-700', badge: 'bg-slate-100 text-slate-600' }

function palette(skill: string) {
  return SKILL_PALETTE[skill] ?? FALLBACK
}

function timeToMin(t: string): number {
  const [h, m] = t.split(':').map(Number)
  return h * 60 + m
}

const HOUR_PX = 72

interface Props {
  shifts: ShiftDef[]
  assignments: Assignment[] | null
  people: Person[]
}

export function ScheduleTimeline({ shifts, assignments, people }: Props) {
  if (shifts.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center rounded-xl border border-dashed border-slate-200 bg-white text-sm text-slate-400">
        Add shifts on the left to get started.
      </div>
    )
  }

  const personById = Object.fromEntries(people.map(p => [p.id, p]))
  const assignmentByShift = Object.fromEntries(
    (assignments ?? []).map(a => [a.shift_id, a])
  )

  // Time range — snap to whole hours, pad by 30 min
  const allMins = shifts.flatMap(s => [timeToMin(s.start), timeToMin(s.end)])
  const minMin = Math.floor((Math.min(...allMins) - 30) / 60) * 60
  const maxMin = Math.ceil((Math.max(...allMins) + 30) / 60) * 60
  const totalMins = maxMin - minMin
  const totalHeight = (totalMins / 60) * HOUR_PX

  const hours: number[] = []
  for (let t = minMin; t <= maxMin; t += 60) hours.push(t)

  function top(min: number) {
    return ((min - minMin) / 60) * HOUR_PX
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {assignments ? 'Generated Schedule' : 'Schedule'}
        </h2>
        {!assignments && (
          <span className="text-xs text-slate-400">Generate to assign people</span>
        )}
      </div>

      <div className="flex gap-3">
        {/* Hour labels */}
        <div className="relative w-12 flex-shrink-0 select-none" style={{ height: totalHeight }}>
          {hours.map(t => (
            <div
              key={t}
              className="absolute right-0 -translate-y-2 text-right text-xs text-slate-400"
              style={{ top: top(t) }}
            >
              {String(Math.floor(t / 60)).padStart(2, '0')}:00
            </div>
          ))}
        </div>

        {/* Timeline */}
        <div className="relative flex-1" style={{ height: totalHeight }}>
          {/* Gridlines */}
          {hours.map(t => (
            <div
              key={t}
              className="absolute w-full border-t border-slate-100"
              style={{ top: top(t) }}
            />
          ))}

          {/* Shift blocks */}
          {shifts.map(shift => {
            const sMin = timeToMin(shift.start)
            const eMin = timeToMin(shift.end)
            const blockTop = top(sMin)
            const blockH = top(eMin) - blockTop
            const pal = palette(shift.required_skill)
            const a = assignmentByShift[shift.id]
            const assigned = a?.person_ids.map(id => personById[id]).filter(Boolean) ?? []
            const unfulfilled = a && !a.fulfilled

            return (
              <div
                key={shift.id}
                className={`absolute inset-x-0 rounded-lg border px-3 py-2 ${pal.block} ${
                  !a ? 'border-dashed opacity-60' : ''
                }`}
                style={{ top: blockTop + 2, height: blockH - 4 }}
              >
                <div className={`text-sm font-semibold ${pal.label}`}>{shift.name}</div>
                <div className={`text-xs opacity-70 ${pal.label}`}>
                  {shift.start}–{shift.end} · needs {shift.required_count} × {shift.required_skill}
                </div>

                {/* Assignment result */}
                {a && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {unfulfilled && (
                      <span className="rounded bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                        ⚠ No qualified person available
                      </span>
                    )}
                    {assigned.map(p => (
                      <span key={p.id} className={`rounded px-2 py-0.5 text-xs font-medium ${pal.badge}`}>
                        {p.name}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
