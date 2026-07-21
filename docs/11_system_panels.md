# System Panels

The System is not part of the handcrafted world — it is something *overlaid*
on it. So its panels are the one deliberate break from the parchment
aesthetic: dark, backlit, machine-precise, with ornate corner filigree, a
crowned icon, rules bracketing a letterspaced title, and bracketed body copy.

Modelled directly on the provided System UI kit
(`assets/backgrounds/ChatGPT Image Jul 21…png`).

### Syntax

```text
system skill_learned:
"SKILL LEARNED"
"You have learned 'VOICE OF THE SYSTEM'."
"The world can now hear you speak."
```

- The word after `system` is the **variant**.
- The **first** quoted line is the panel title.
- Every line after it is body copy, each rendered inside `[brackets]`.
- Panels support `{{player}}` templating like all other authored content.

A system panel is always its own beat — it interrupts, by design. It is
dismissed with Continue, Enter, or Space.

### Variants

| Variant | Icon | Accent | Use for |
|---|---|---|---|
| `alarm` | `!` | blue | System boot, urgent address to the player |
| `system` | `⚙` | green | Mission briefings, neutral system output |
| `notification` | `🔔` | amber | New quests |
| `skill_learned` | `📖` | purple | Skills, modules, abilities unlocked |
| `status` | `♥` | teal | Stat readouts, scans |
| `warning` | `⚠` | red | Trials, penalties, stat resets |
| `item_obtained` | `🧰` | gold | Items and equipment |
| `level_up` | `↑` | bright blue | Level and chapter completion |
| `arrival` | `⛩` | violet | Isekai arrival, world transitions |

Adding a variant is one row in `VARIANTS` in `SystemPanel.jsx` plus one CSS
line setting `--sys-hue` / `--sys-glow`.

### Current usage

| Scene | Panels |
|---|---|
| `awakening` | `arrival`, `alarm` |
| `chapter_1_dragon` | `status` (scans the player's real stats) |
| `chapter_1_dragon_trial` | `warning` |
| `chapter_1_trial_failed` | `warning` |
| `chapter_1b_wisdom_of_system` | `skill_learned` ×3, `item_obtained`, `level_up` |
| `chapter_2_trial_of_choice` | `notification`, `system` |

These replaced the plain `"===================="` text banners that were
previously rendered as ordinary narration.
