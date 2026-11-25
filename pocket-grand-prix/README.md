# FIWS Pocket Grand Prix

A hidden FIWS-only, top-down open-wheel arcade time-trial game.

## Preview locally

Serve the repository root with a static server:

```bash
python3 -m http.server 8000
```

Open `http://localhost:8000/pocket-grand-prix/`.

## Current playtest build

- A redesigned standalone arcade shell with a screen-filling race view and compact HUD.
- Vantage Park circuit with layered asphalt, painted kerbs, start/finish stripe, trackside scenery and circuit markings.
- Detailed top-down open-wheel car silhouette with exposed tyres, wings, cockpit and shadow.
- Camera follows the car on narrow/portrait screens and frames the full circuit on wider screens.
- More responsive acceleration, steering, grip and off-track slowdown, plus tyre-mark feedback when pushing the car.
- Keyboard and multi-touch controls, pause/resume, restart, lap timing and locally stored personal best.
- Landscape and portrait layouts, safe-area spacing and controls overlaid on the track to preserve usable screen space.

## Controls

- Desktop: WASD or arrow keys.
- Touch: left/right steering, brake and throttle. The race camera follows the car in portrait orientation.

## Known scope limits

This remains a visual/handling playtest, not the finished game. Grand Prix AI, nine randomly selected circuits, team selection/current-season liveries, sound and the server-validated three-letter online leaderboard are not implemented yet. It does not read or write official championship data. Real-device testing is still required; the automated checks do not replace phone/browser playtesting.
