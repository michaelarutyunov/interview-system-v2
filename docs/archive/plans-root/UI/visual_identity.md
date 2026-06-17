For a **minimal, technical Streamlit app**, the goal is:

* high readability for conversation
* subtle "engineering" aesthetic
* almost no decorative color
* one sharp accent color

Think **Notion × Linear × developer console**.

Below is a scheme that works very well for AI tooling.

---

# 1. Font Strategy (Very Important)

Use **two fonts**:

| Use               | Font               | Why                |
| ----------------- | ------------------ | ------------------ |
| UI + conversation | **Inter**          | extremely readable |
| technical labels  | **JetBrains Mono** | dev aesthetic      |

### Inter

Inter

Best UI font right now.

Why:

* neutral
* clean numerals
* great readability
* used by many modern tools

### JetBrains Mono

JetBrains Mono

Use only for:

* system labels
* strategy names
* node IDs
* the title `// interview_engine_demo`

Example:

```
AI question
(normal font)

strategy: explore_situation
(monospace)
```

---

### Streamlit font injection

```python
st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

code, pre, .mono {
    font-family: 'JetBrains Mono', monospace;
}

</style>
""", unsafe_allow_html=True)
```

---

# 2. Color Philosophy

Avoid rainbow UI.

Use **one accent color only**.

Structure:

| Element    | Color      |
| ---------- | ---------- |
| background | near white |
| text       | dark gray  |
| metadata   | muted gray |
| accent     | one color  |

---

# 3. Recommended Palette

### Background

```
#FAFAFA
```

Not pure white → easier on eyes.

---

### Primary Text

```
#111111
```

Very readable.

---

### Secondary Text

```
#6B7280
```

Used for:

* strategy labels
* timestamps
* graph stats

---

### UI Borders

```
#E5E7EB
```

For dividers and subtle containers.

---

# 4. Accent Color (Pick ONE)

For a **tech-edge AI feel**, these work best.

---

## Option 1 — Teal (Best for AI tools)

```
#14B8A6
```

Feels:

* modern
* technical
* calm

Used for:

* active state
* buttons
* highlights

---

## Option 2 — Electric Blue (More "AI")

```
#2563EB
```

Feels:

* energetic
* technical
* product-like

---

## Option 3 — Neon Mint (Experimental)

```
#10B981
```

Feels:

* futuristic
* slightly hacker-ish

---

# 5. Chat Message Styling

Assistant:

```
background: #F3F4F6
```

User:

```
background: #FFFFFF
border: 1px solid #E5E7EB
```

This keeps the UI **very clean**.

---

# 6. Strategy Metadata Style

Make these **subtle but technical**.

Example:

```
explore_situation • 40.5s
```

Color:

```
#9CA3AF
```

Font:

```
JetBrains Mono
```

---

# 7. Header Style

```
 // interview_engine_demo
```

Color:

```
#111111
```

Font:

```
JetBrains Mono
```

Add small accent line:

```
border-bottom: 1px solid #E5E7EB
```

---

# 8. Sidebar

Background:

```
#FFFFFF
```

Section labels:

```
#9CA3AF
```

Active item:

accent color.

---

# 9. Example CSS

You can inject something like this:

```python
st.markdown("""
<style>

body {
    background-color: #FAFAFA;
}

h1, h2, h3 {
    color: #111111;
}

.stChatMessage {
    border-radius: 12px;
}

div[data-testid="stChatMessageContent"] {
    font-size: 16px;
}

.caption {
    color: #9CA3AF;
    font-family: 'JetBrains Mono', monospace;
}

</style>
""", unsafe_allow_html=True)
```

---

# 10. Visual Identity Summary

Final aesthetic:

| Component      | Style          |
| -------------- | -------------- |
| UI font        | Inter          |
| technical font | JetBrains Mono |
| background     | #FAFAFA        |
| text           | #111111        |
| metadata       | #9CA3AF        |
| border         | #E5E7EB        |
| accent         | teal (#14B8A6) |

Result:

* minimal
* technical
* calm
* credible for research tooling

---

**One more tip**

If you want a **slightly more "AI lab" vibe**, you can add a subtle dark mode later:

```
background: #0F172A
accent: #22D3EE
```

This looks extremely good for demos.

---

If you want, I can also show you **three Streamlit UI tricks used by YC startups to make apps look like polished SaaS products** rather than Python dashboards. They're surprisingly simple but very effective.
