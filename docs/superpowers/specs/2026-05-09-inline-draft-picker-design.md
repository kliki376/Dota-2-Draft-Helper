# Inline Draft Picker — Design Spec

**Date:** 2026-05-09  
**Status:** Approved  
**Scope:** Replace text-based /pick flow with inline keyboard hero picker, split into 2 draft phases

---

## Problem

Current `/pick` flow requires typing hero names as comma-separated text. This is slow and error-prone during a live Dota 2 draft. Users need a tap-based interface that matches the pace of the game.

---

## Solution

Inline keyboard hero picker with alphabetical grouping and a 2-phase draft flow.

---

## Draft Flow

### Phase 1 — Enemy picks 2 heroes

1. User sends `/pick`
2. Bot sends a message with phase indicator and 8 letter-group buttons:
   ```
   Фаза 1 — Враг пикает 2 героев (0/2)
   [A-C] [D-F] [G-I] [J-L]
   [M-O] [P-R] [S-T] [U-Z]
   ```
3. User taps a group → message **edits** to show heroes in that group + [← Назад]
4. User taps a hero → message edits back to group picker, pick counter increments
5. After 2 picks → bot edits message to show recommendations + [Перейти к фазе 2 →] button

### Phase 2 — Enemy picks 2 more heroes

6. User taps [Перейти к фазе 2 →]
7. Same picker flow, counter resets to (0/2), but context includes phase 1 picks
8. After 2 more picks → bot edits message to show final "ласт пик" recommendation (scored against all 4 enemies)

---

## UI Details

- **Message editing:** Every interaction edits the same bot message (`edit_message_text` + `edit_message_reply_markup`). No new messages except the initial one and the final recommendations.
- **Letter groups:** A-C, D-F, G-I, J-L, M-O, P-R, S-T, U-Z (8 groups, 2 rows of 4)
- **Hero buttons per group:** Up to ~20 heroes, arranged in 3 columns. Last button is always [← Назад]
- **Duplicate guard:** If user taps a hero already picked, silently ignore (or show brief alert)
- **Cancel:** [✖ Отмена] button always visible in group view

---

## Callback Data Format

All inline button callbacks use prefixed strings:

| Callback data | Meaning |
|---|---|
| `group:A-C` | User tapped letter group A-C |
| `hero:antimage` | User tapped Anti-Mage |
| `back` | Return to group picker |
| `phase2` | Start phase 2 |
| `cancel` | Cancel the draft session |

---

## Scoring

- **Phase 1 result:** `score_picks(enemies=phase1_picks, ...)` — top 5 heroes
- **Phase 2 result:** `score_picks(enemies=phase1_picks + phase2_picks, ...)` — top 3 heroes with "ласт пик" framing
- Player profile (if linked) applied in both phases

---

## State (context.user_data)

```python
{
    "phase1_enemies": [HeroInfo, HeroInfo],       # set after phase 1 complete
    "phase2_enemies": [HeroInfo, HeroInfo],       # set after phase 2 complete
    "current_picks": [HeroInfo, ...],             # accumulator for current phase
    "picker_message_id": int,                     # message to edit
    "current_group": str | None,                  # "A-C" etc, None = group view
}
```

---

## Files Changed

| File | Change |
|---|---|
| `dota_bot/bot.py` | Replace ConversationHandler /pick with CallbackQueryHandler-based picker |
| `dota_bot/keyboards.py` | New — builds InlineKeyboardMarkup for groups and hero lists |

---

## Out of Scope (v1.1+)

- Ally hero picker (same pattern, future phase)
- Position filter before picking
- Search by typing within picker
