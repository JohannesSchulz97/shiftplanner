import type { Person } from '@/types'

interface RowProps {
  person: Person
  allSkills: string[]
  onChange: (p: Person) => void
  onRemove: () => void
}

function PersonRow({ person, allSkills, onChange, onRemove }: RowProps) {
  function toggleSkill(skill: string) {
    const skills = person.skills.includes(skill)
      ? person.skills.filter(s => s !== skill)
      : [...person.skills, skill]
    onChange({ ...person, skills })
  }

  return (
    <div className="flex items-start gap-3 py-3">
      {/* Available dot */}
      <button
        onClick={() => onChange({ ...person, available: !person.available })}
        title={person.available ? 'Mark unavailable' : 'Mark available'}
        className={`mt-1 h-3 w-3 flex-shrink-0 rounded-full border-2 transition-colors ${
          person.available ? 'border-emerald-500 bg-emerald-500' : 'border-slate-300 bg-white'
        }`}
      />
      <div className="flex-1 min-w-0">
        <input
          value={person.name}
          onChange={e => onChange({ ...person, name: e.target.value })}
          className="w-full text-sm font-medium text-slate-800 bg-transparent border-b border-transparent hover:border-slate-200 focus:border-slate-400 focus:outline-none pb-0.5"
        />
        <div className="flex flex-wrap gap-1 mt-1.5">
          {allSkills.map(skill => {
            const active = person.skills.includes(skill)
            return (
              <button
                key={skill}
                onClick={() => toggleSkill(skill)}
                className={`rounded px-2 py-0.5 text-xs font-medium border transition-colors ${
                  active
                    ? 'bg-slate-800 text-white border-slate-800'
                    : 'bg-white text-slate-400 border-slate-200 hover:border-slate-400 hover:text-slate-600'
                }`}
              >
                {skill}
              </button>
            )
          })}
        </div>
      </div>
      <button
        onClick={onRemove}
        className="text-slate-300 hover:text-red-400 text-lg leading-none mt-0.5 transition-colors"
      >
        ×
      </button>
    </div>
  )
}

interface Props {
  people: Person[]
  setPeople: React.Dispatch<React.SetStateAction<Person[]>>
  allSkills: string[]
}

export function PeoplePanel({ people, setPeople, allSkills }: Props) {
  function add() {
    setPeople(prev => [
      ...prev,
      { id: `p${Date.now()}`, name: 'New Person', skills: [], available: true },
    ])
  }

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">People</h2>
        <button onClick={add} className="text-xs font-medium text-slate-400 hover:text-slate-700 transition-colors">
          + Add person
        </button>
      </div>
      <p className="mb-1 text-xs text-slate-400">
        <span className="inline-block h-2 w-2 rounded-full bg-emerald-500 mr-1" />
        green = available today · click skills to toggle
      </p>
      <div className="divide-y divide-slate-100">
        {people.length === 0 && (
          <p className="py-4 text-center text-xs text-slate-400">No people yet.</p>
        )}
        {people.map(p => (
          <PersonRow
            key={p.id}
            person={p}
            allSkills={allSkills}
            onChange={updated => setPeople(prev => prev.map(x => x.id === p.id ? updated : x))}
            onRemove={() => setPeople(prev => prev.filter(x => x.id !== p.id))}
          />
        ))}
      </div>
    </section>
  )
}
