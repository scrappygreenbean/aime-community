# The Realtor's AIME — Community OS (Proof of Concept)

A custom front-end for the AIME community — built to replace the endless, ugly
GoHighLevel feed with a **real website** where every *channel* opens to its own
designed page. This is the first vertical, **The Realtor's AIME**, with the first
working channel: **AI Employees**.

GoHighLevel stays the backend (members, the $88 payment, login). This repo is the
beautiful custom experience that will later be wired to it. Right now it's a
fully static site — no build step, no server required.

---

## What's in this proof of concept

| Page | What it is |
|------|------------|
| `index.html` | The **home hub** for The Realtor's AIME. Shows every channel as a big, designed tile — *AI Employees* (live) plus placeholders (Start Here, Resources, Wins, Office Hours, Ask AIME) so the "each channel = its own page, no endless scroll" idea is obvious on sight. |
| `ai-employees.html` | The **AI Employees channel** — a gallery of 8 AI specialist cards. Click any card and it opens that employee's **own detail view** (what they do, what you'll get, and a real, ready-to-paste prompt with a one-click Copy button). |

### The 8 AI Employees (each with a real, paste-ready prompt)
1. **Mira** — Listing Describer
2. **Dale** — Follow-Up Writer
3. **Reese** — Social Post Maker
4. **Sloane** — Neighborhood Expert
5. **Quincy** — Objection Handler
6. **Harper** — CMA Storyteller
7. **Beau** — Open House Recap
8. **Nova** — Lead Qualifier

Every prompt is written in the AIME voice — direct, honest, fiduciary-first,
client-over-commission, a little Texas, anti-fluff. No guru talk, no hype.

---

## Brand

Classic **gold on black** (the Realtor's AIME sub-brand — *not* the parent
rose-gold AIME).

| Token | Hex | Use |
|-------|-----|-----|
| Midnight Black | `#050505` | Background |
| Luxury Gold | `#D4AF37` | Primary metallic |
| Champagne Gold | `#F1D18A` | Secondary |
| Accent Glow Gold | `#FFD76A` | Highlights |

- **Headers:** Playfair Display (elegant serif)
- **Body:** Montserrat (clean sans)
- Luxury-tech aesthetic — lots of black negative space, metallic gold accents,
  card hover lift + glow.

---

## How to view it locally

It's plain static HTML/CSS/JS. Two options:

### Option A — just open the file
Double-click `index.html` (or drag it into a browser). Everything works from
`file://`, including the Copy-prompt button.

### Option B — run a tiny local server (recommended)
A local server avoids any browser quirks and matches how it'll be hosted.

**Python (already on most machines):**
```bash
cd aime-community
python -m http.server 8080
```
Then open <http://localhost:8080>.

**Node (if you prefer):**
```bash
cd aime-community
npx serve .
```

Start at the home hub (`index.html`), then click the **AI Employees** tile.

---

## How it's built

```
aime-community/
├── index.html            # Home hub — channel tiles
├── ai-employees.html     # AI Employees channel (gallery + detail)
├── assets/
│   ├── css/styles.css    # All styling (brand tokens + components)
│   └── js/
│       ├── employees.js  # The roster + prompts (the only file to edit for content)
│       └── app.js        # Renders the gallery + hash-routed detail views
└── README.md
```

- **No framework, no build.** Everything is vanilla HTML/CSS/JS so it loads
  instantly and is trivial to host anywhere (GHL custom page, Netlify, S3, etc.).
- **Detail views are hash-routed** (`ai-employees.html#mira`) so each AI Employee
  has its own shareable link and a real Back button — without a server.
- **Adding or editing content** = edit `assets/js/employees.js` only. Each
  employee is one object (name, role, one-liner, prompt, etc.).

---

## What's intentionally NOT done yet
- **GoHighLevel wiring** (auth, members, the $88 payment) — backend hookup is the
  next phase. This is the front-end experience to react to first.
- The placeholder channels (Start Here, Resources, Wins, Office Hours, Ask AIME)
  are tiles only — they show the concept; their pages come next.

---

## Adding the next vertical later
The whole thing is a "Brand Pack" swap: change the four color tokens + fonts +
emblem in `styles.css`, point the channel tiles at that vertical's pages, and
swap the roster in `employees.js`. Insurance Agents AIME, HHS AIME, etc. each
become their own separately-branded section on the same engine.

---

*The Realtor's AIME · AI that finally works for YOU. · hello@gotaime.com · $88 lifetime, no upsells.*
