# Characters — Cast, Domains, and Introduction Cadence

Design principle: **every recurring character owns a teaching domain and a
personality that embodies it.** The Sage is patient and unfolds ideas slowly —
because that's how fundamentals should be taught. A functions-mentor should be
*lazy in the good way* ("write it once, never again"). The character *is* the
pedagogy. That's what makes a mentor memorable instead of a talking tooltip.

## The rule of introduction

Don't dump the cast. Introduce a mentor **one chapter before** their B-chapter,
as a face in an A-chapter the player can't yet help — so when the B-chapter
opens, the learner already cares who's teaching them. The Old Man → Gate is
already almost this shape; make it the standard.

Cadence: **tease in A, teach in B, reprise in later A.** A mentor the player
learned from should show up again later, older or in trouble, so the world feels
continuous and the earlier lesson gets a callback.

## Established cast (canon)

| Character | Domain | Personality | Status |
|---|---|---|---|
| **The Player** (Unknown Traveler) | — | Amnesiac; the learner's avatar. Silent early, gains "voice" literally when they learn `print()` | ✅ |
| **The System** | Framing / stats / quests | Cold, precise, machine-exact. Grief disguised as neutrality (see arc) | ✅ |
| **The Ancient Dragon** | Judgment / DSA bosses | God-like, severe, secretly a teacher. "Failure is the beginning of your education" | ✅ |
| **The Sage of the System** | Fundamentals (vars, types, I/O) | Patient, warm, unfolds ideas one chest at a time. The template mentor | ✅ |
| **The Old Man at the Gate** | Control flow | Frail, humble, decades of honest failure. Rewards help with knowledge | ✅ |

## Proposed cast (new mentors, by domain)

Each is a candidate to introduce in the A-chapter before their B-chapter.

| Character | Domain (chapter) | Personality hook | Teaching-as-character |
|---|---|---|---|
| **The Alchemist** | Operators (2b) | Obsessive, measures everything twice | Every value has a *weight*; `==` weighs, `=` pours. Precedence = which reagent goes in first |
| **The Warden of the Halls** | Loops (3b) | Trapped in his own corridor for an age | He is *living proof of an infinite loop* — freeing him teaches `break` and the exit condition |
| **The Quartermaster** | Lists (4b) | Gruff, hates off-by-one, counts on his fingers from zero | Packs a caravan; every slot numbered from 0. Rants when you index out of range |
| **The Cataloguer** | Dicts/tuples/sets (5b) | Blind archivist who finds anything by *name*, never by position | "Don't tell me *where* it is, tell me its *key*." Sets = the roster where no name repeats |
| **The Riddle Weaver** | Strings (6b) | Speaks only in wordplay | Slices ribbons of runes; `f`-strings are how she "weaves a name into a sentence" |
| **The Enchanter** | Functions (7b) | Gloriously lazy genius | "I refuse to cast the same spell twice." `def` = binding once; `return` = the spell's gift |
| **The Warder** | Exceptions (8b) | A soldier who has *survived* the Blight | Teaches you to raise a ward before touching corruption. Calm because he's been afraid correctly |
| **The Scribe** | File I/O (9b) | Ancient, ink-stained, keeper of the true record | Reads the world's source scrolls; lets you *write your name in* — the first permanent thing you do |
| **The Duelist** | Comprehensions (10b) | Flashy, speed-obsessed | Mocks your five-line loops, shows you the one-breath version. Scored on DEX |
| **The Architect / First Traveler** | OOP (11b) | The player's predecessor; who you might be | Teaches you to *define beings*. The reveal-heavy mentor — the arc's turn |

## Antagonist-side

| Entity | Role | Concept it embodies |
|---|---|---|
| **The Unhandled / the Blight** | The spreading decay | Uncaught exceptions made physical |
| **The Null** *(optional lieutenant)* | A being of absence, whispers "you are nothing" | `None`, uninitialized values, `NameError` |
| **The Fork** *(optional)* | A corrupted twin of the player | Duplicated/aliased state, mutation bugs — a mirror boss late in Act III |

## Buildup arcs (mini)

- **The System's thaw.** Starts giving *only* stats and warnings. By Act III it
  editorializes, hesitates, and finally asks the player for something instead of
  commanding. Its last line should feel earned.
- **The Dragon's return.** It judged you in Ch 1. Bring it back at the Act IV
  boss *on your side* — the being that once tested your ambition now needs it.
- **The Old Man's secret.** Decades at one gate is suspicious. Reprise him later
  as more than he seemed — maybe a failed former traveler who couldn't learn OOP
  and settled at a door he could *almost* open.
- **The First Traveler.** Seed unexplained references early (a second character
  sheet in the Sage's library, a name that isn't yours on the Archive scroll),
  pay off at chapter 11b when you learn you can define beings — because someone
  once defined *you*.

## A small, high-value writing rule

The player is **silent until they learn `print()`**, then gains a voice
(`npc You:` blocks already start appearing in Ch 2). Lean into this hard: the
player's *ability to speak in the story is literally gated by the curriculum.*
Early chapters, others speak for them; after the mirror, they speak; after
functions, they can *promise* things (a function is a promise); after OOP, they
can *name new things into the world*. The grammar of what the player can say
should grow with what they can code. This is the single most elegant hook in the
whole design — protect it.
