# FIWS Pocket Grand Prix

An isolated FIWS-only top-down open-wheel arcade racing prototype.

## Local preview

Open `index.html` directly in a modern browser, or serve this folder with a static server:

```bash
python3 -m http.server 8000
```

Then visit `http://localhost:8000/pocket-grand-prix/` from the repository root.

## Current prototype scope

- Standalone page intended for `/pocket-grand-prix/`.
- One fictional Grand Prix circuit: Vantage Park.
- Canvas-rendered top-down circuit and open-wheel car.
- Time Trial driving prototype with acceleration, braking, steering, lateral grip, off-track slowdown and lap timing.
- Keyboard controls and touch controls.
- Responsive layout, pause/resume, visibility pause and local personal-best storage.
- Grand Prix mode, AI, nine-track random selection, current-season team colours and online leaderboard are planned follow-up work.

## Controls

- Desktop: WASD or arrow keys.
- Mobile: left/right steering and brake/go touch buttons. Landscape is recommended.

## Important

This is an early handling prototype, not a release candidate. Tune the handling and verify on real phones before adding AI, all nine circuits, live FIWS team data or a server-validated three-character leaderboard. It does not read or write official championship data.
