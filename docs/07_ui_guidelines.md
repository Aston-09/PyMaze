# UI Guidelines

The user interface of PyBe must balance the aesthetic of a modern web application with the immersion of an RPG.

## Overall Theme
- **Aesthetic:** Premium Dark Theme.
- **Visual Style:** Glassmorphism (translucent backgrounds with blur filters) for floating panels, dynamic micro-animations, and smooth transitions.
- **Color Palette:** Deep blues, purples, and slate grays for backgrounds, with vibrant neon accents for highlights, success (green), and error (red) states.

## Layout & Components
- **The Split-Pane View:** 
  - The left pane serves as the **Narrative Panel** (or Dialogue Box / HUD), displaying story text, NPC dialogues, and quest instructions.
  - The right pane serves as the **Code Editor**, utilizing Monaco Editor (VS Code core) for an authentic coding experience with syntax highlighting and auto-indentation.
- **Dialogue Box:** Should visually distinguish between different NPCs and the "System". Use subtle text animations (like typewriter effects) when rendering new story beats.
- **Execution Console:** Situated below or alongside the code editor, it must clearly display:
  - Standard output and error traces.
  - A breakdown of Validation Tests (Pass/Fail indicators with expected vs. actual results).
- **HUD (Heads Up Display):** A persistent header or overlay showing the player's current Chapter, HP, Mana, XP, and Gold.
