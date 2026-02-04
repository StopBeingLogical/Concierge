# TUI Splash Screen Design (v1.1 Feature)

Design specification for adding a professional splash screen to Concierge, similar to Claude Code's interface.

## Vision

Professional, animated TUI welcome screen that makes Concierge feel polished and real.

---

## Display Specification

### Where It Appears

1. **On First Run**: `bit init <workspace>`
2. **On Demand**: `bit splash` command
3. **Optional**: On `bit --version` or `bit --help`

### Screen Layout

```
╔════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║                      🎯 CONCIERGE v1.0.0                          ║
║                  Personal AI Orchestration System                  ║
║                                                                    ║
╠════════════════════════════════════════════════════════════════════╣
║                                                                    ║
║  🚀 Features:                                                      ║
║     • Intent Synthesis - Convert natural language to tasks        ║
║     • Package Registry - 8+ ready-to-use task packages            ║
║     • Smart Matching - Confidence-scored package selection        ║
║     • Approval Gates - Review before execution                    ║
║     • Event Logging - Complete audit trails                       ║
║     • Real-time Monitoring - Watch execution live                 ║
║                                                                    ║
║  📦 Quick Start:                                                   ║
║     1. bit intent synth --text "Your task"                        ║
║     2. bit job from-intent --intent-id <hash>                    ║
║     3. bit plan generate --job-id <job_id>                       ║
║     4. bit approve --job-id <job_id>                             ║
║     5. bit run --job-id <job_id>                                 ║
║                                                                    ║
║  📚 Documentation:                                                 ║
║     • bit --help           - Command reference                    ║
║     • INDEX.md             - Navigation guide                     ║
║     • QUICKREF.md          - One-page cheat sheet                ║
║     • docs/examples/       - Real workflow examples               ║
║                                                                    ║
║  ⌨️  Try Now:                                                     ║
║     $ bit intent synth --text "Normalize podcast audio"          ║
║                                                                    ║
╠════════════════════════════════════════════════════════════════════╣
║  [Space] Continue  |  [q] Quit  |  [d] Documentation              ║
╚════════════════════════════════════════════════════════════════════╝
```

---

## Animation Ideas

### Option 1: Simple Fade-In
- Text appears line by line
- Icons animate in sequence
- Duration: 2-3 seconds total

### Option 2: Fancy Spinner
- Logo spins while loading
- Features appear one by one
- Smooth transitions
- Duration: 3-5 seconds

### Option 3: Minimal (Recommended for v1.1)
- No animation
- Clean, instant display
- Professional feel
- Add animations in v1.2+

---

## Implementation Details

### Technology
- **Framework**: Textual (already in dependencies: `textual>=0.40`)
- **Location**: `bit/tui.py` (new file)
- **Command**: Add to `bit/cli.py`

### Key Components

1. **SplashScreen Widget** (100-150 lines)
   ```python
   from textual.app import ComposeResult
   from textual.widgets import Static
   from textual.containers import Container

   class SplashScreen(Static):
       """Professional splash screen for Concierge"""

       def render(self):
           # Return formatted splash text
           pass

       def on_key(self, event):
           # Handle Space, Q, D keys
           pass
   ```

2. **Interactive Elements**
   - [Space] to continue
   - [q] to quit
   - [d] to open docs
   - [h] for help

3. **Color Scheme** (Suggested)
   - Primary: Cyan/Blue (#00D9FF or similar)
   - Accent: Green (#00FF00)
   - Background: Dark (#1E1E1E)
   - Text: White (#FFFFFF)

---

## CLI Integration

### New Command
```bash
bit splash
```

**Location**: `bit/cli.py`

```python
@app.command()
def splash():
    """Show Concierge splash screen"""
    from bit.tui import SplashScreen
    screen = SplashScreen()
    screen.run()
```

### On First Run
```python
@app.command()
def init(path: str):
    """Initialize workspace"""
    # ... existing code ...

    # Show splash on first init
    if is_first_run:
        show_splash_screen()
```

---

## Design Variants

### Minimal (Fast, Safe for v1.1)
- Static text display
- 80x25 character layout
- No animation
- Simple color highlighting
- ~80 lines of code

### Professional (Medium, for v1.2)
- Animated text reveal
- Spinner/progress indication
- Interactive menu
- Full TUI app experience
- ~200 lines of code

### Premium (Full, for v2.0)
- Rich graphics with Textual Canvas
- Multiple screens
- Navigation between help sections
- Settings customization
- ~500+ lines of code

---

## File Structure

After implementation:
```
bit/
├── tui.py              # NEW - TUI splash screen
├── cli.py              # UPDATED - Add splash command
└── ...

docs/
├── TUI_SPLASH_DESIGN.md  # This file
└── ...
```

---

## Testing

### Manual Testing
```bash
# Show splash
bit splash

# Should display clean, readable screen
# Should respond to key presses
# Should not crash or hang
```

### Test Cases
- [ ] Splash displays correctly on first init
- [ ] Splash command works: `bit splash`
- [ ] Navigation keys work (Space, q, d, h)
- [ ] Renders properly at different terminal sizes
- [ ] Colors display correctly
- [ ] No performance impact

---

## Dependencies

Already available:
- ✅ `textual>=0.40` - Already in pyproject.toml
- ✅ `rich>=13.0` - For styling (already included)

No new dependencies needed!

---

## Future Enhancements

**v1.2+:**
- [ ] Animated text reveal
- [ ] Spinner while checking workspace
- [ ] "Latest news" feed from GitHub releases
- [ ] Keyboard shortcuts guide
- [ ] Theme selection

**v2.0+:**
- [ ] Full TUI dashboard
- [ ] Multi-screen navigation
- [ ] Settings management UI
- [ ] Visual workflow builder
- [ ] Real-time job monitoring dashboard

---

## Notes for Implementation

1. **Keep it Simple**: Start with static text, add animations later
2. **Accessibility**: Ensure keyboard navigation works for all key presses
3. **Terminal Size**: Handle small terminals gracefully (80x24 minimum)
4. **Colors**: Test with different terminal themes (light/dark)
5. **Performance**: Should appear instantly, no lag
6. **Exit Gracefully**: Clean up on quit, return to shell cleanly

---

## Example Reference

Similar to Claude Code's splash, but simpler:
- Professional header with version
- Feature highlights
- Quick start guide
- Documentation links
- Interactive key hints at bottom

---

## Success Criteria (v1.1)

✅ Clean, readable splash screen displays
✅ Can be triggered with `bit splash`
✅ Shows on first workspace init
✅ Keyboard navigation works (Space, q)
✅ No terminal size issues
✅ Professional appearance
✅ No new dependencies required
✅ ~100-150 lines of clean code

---

**Status**: Design ready for implementation in v1.1
**Effort**: 1-2 hours of development
**Priority**: Nice-to-have polish feature
**Blocker**: None - can proceed without for v1.0

---

## Implementation Checklist (For Next Session)

- [ ] Create `bit/tui.py` with SplashScreen class
- [ ] Add `bit splash` command to CLI
- [ ] Add splash on first init
- [ ] Test keyboard navigation
- [ ] Test terminal compatibility
- [ ] Update CLI help text
- [ ] Add unit tests
- [ ] Document in CHANGELOG
