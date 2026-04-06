# sublim
PySide6 GUI python script for displaying subliminal messages from a text file

```
python -m pip install pyside6
```

Right click and create shortcuts to the script with your text files.

```
C:\sublim\sublim.py ./messages.txt
```

## Modes

**default** — sequential, no gaps
```
sublim.py ./messages.txt
```

**conscious reinforcement** — mostly subliminal, occasionally pauses to show a message at readable speed
```
sublim.py ./messages.txt c
```

**randomize, don't burst**
```
sublim.py ./messages.txt r
```

**burst, don't randomize**
```
sublim.py ./messages.txt b
```

**random burst**
```
sublim.py ./messages.txt rb
```

**surprising** — long random gaps with occasional surprise flashes. better for longer sessions
```
sublim.py ./messages.txt s
```

**bird** — like `s`, uses bird sounds as audio cues before surprise flashes
```
sublim.py ./messages.txt bird
```

**hypno** — full guided hypnosis session with phased arc (see below)
```
sublim.py ./messages.txt hypno 20
```

---

## Optional flags (all modes)

**Background audio** — loops an audio file for the duration of the session (theta/alpha binaural beats recommended)
```
sublim.py ./messages.txt s bg ./theta.wav
sublim.py ./messages.txt hypno 20 bg ./theta.wav
```

---

## hypno mode

A complete hypnosis session arc. Dark theme. Duration in minutes (default 20).

```
sublim.py ./messages.txt hypno 20
sublim.py ./messages.txt hypno 45 bg ./theta.wav induction ./induction.txt
```

**Session phases:**
1. **Progressive relaxation** — body-scan sequence before anything begins (relax forehead, jaw, shoulders, etc.)
2. **Induction** (15% of session) — messages shown at readable speed with fade in/out, breathing guides between each
3. **Deepening** (10%) — flash speed ramps gradually from 500ms → 44ms while spiral spins
4. **Delivery** (65%) — full subliminal burst mode; gaps use breathing guides, deepener phrases, or breath-synced suggestion flashes at exhale peak
5. **Emergence** (10%) — speed ramps back up, breathing, emergence messages, spiral returns, ends on `"awaken."`

**Rotating spiral** — displayed during induction, deepening, and emergence for eye fixation and trance induction. Hidden during subliminal delivery.

**Breath-synced suggestions** — during delivery gaps, suggestions are occasionally flashed at the relaxation peak of the exhale (highest receptivity).

**Deepener phrases** — `"deeper now..."`, `"let it in"`, `"surrender..."` etc. periodically faded in during delivery gaps to maintain trance depth.

**Separate induction script** — optionally load a different phrase file for induction (softer language, body-awareness cues, deepeners) separate from your affirmation messages:
```
sublim.py ./messages.txt hypno 20 induction ./induction.txt
```

**Emergence messages** — tag lines in your messages file with `[emerge]` to use as the awakening sequence:
```
[emerge] returning now...
[emerge] feeling refreshed and clear...
```
If none are tagged, built-in defaults are used.

---

## Message weighting

Prefix any line with `[N]` to make it appear N times more often in the rotation:
```
[3] I am confident
[2] I am focused
I am calm
```

---

## Notes

Keep messages brief — the font is large.

Superior to videos because you get high precision control of timing and randomization within a running program.

Best with a high refresh-rate, low pixel response-time monitor.

For `hypno` mode: theta binaural beats (5–7Hz) or alpha (8–10Hz) as background audio deepen receptivity significantly.

---

## Session time tracking

Records the amount of time the app is open in `rectime.txt`.

Day-by-day breakdown:
```
python ./procRecTime.py
```
