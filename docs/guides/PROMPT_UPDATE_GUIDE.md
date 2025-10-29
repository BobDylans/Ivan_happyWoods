# 🔄 Prompt Update Guide - Frontend Markdown Rendering Rules

**Date**: 2025-10-29  
**Purpose**: Update system prompts to match frontend `react-markdown` rendering capabilities

---

## 📍 Location to Update

**File**: `src/agent/nodes.py`  
**Method**: `_build_optimized_system_prompt()`  
**Lines**: ~670-750 (Search Results Handling section)

---

## ✅ Key Changes Needed

### 1. Replace Result Item Headers

**❌ REMOVE (Breaks frontend rendering)**:
```markdown
#### 1. **[Title]**
- Item 1
- Item 2
```

**✅ REPLACE WITH (Frontend-compatible)**:
```markdown
**1. [Title]**

- Item 1;
- Item 2.
```

**Reason**: Frontend does not properly render lists under `####` headers. Use bold text instead.

---

### 2. Add Mandatory Blank Lines

**Critical Rules**:
```markdown
# After headers (MUST have blank line)
### Header
                    ← Blank line required
Content starts here

# Before/after lists
Intro text
                    ← Blank line required
- List item 1;
- List item 2.
                    ← Blank line required
Next paragraph

# Between numbered results
**1. First Result**

- Detail 1;
- Detail 2.
                    ← Blank line required
**2. Second Result**
```

---

### 3. List Item Format

**✅ CORRECT**:
```markdown
- Item with space after dash;
- Item ends with semicolon;
- Last item ends with period.
```

**❌ INCORRECT**:
```markdown
-Item without space
- Item without punctuation
- Item, with comma
```

---

## 📝 Updated Search Results Template

Replace the template in `_build_optimized_system_prompt()` with:

```python
### Step 2: Structure Your Response (REQUIRED FORMAT)
**Use this exact template following frontend rendering rules:**

```markdown
## 🔍 Search Results: [Topic]

### 📊 Executive Summary

[If ai_answer exists: present it here in 2-3 sentences]
[If no ai_answer: synthesize key findings from top results]

### 📰 Detailed Findings

**1. [Title from result[0]]**

- 📅 Published: [published_date or "Recent"];
- 📝 Key Points: [Extract 50-100 words from snippet];
- 🔗 Source: [Title](URL).

**2. [Title from result[1]]**

- 📅 Published: [published_date or "Recent"];
- 📝 Key Points: [Extract core information];
- 🔗 Source: [Title](URL).

[Continue for top 3-5 results sorted by score]

---

💡 **Key Insight**: [One-sentence conclusion or trend analysis]
```

**CRITICAL Formatting Rules (Frontend Requirements)**:
1. ✅ Blank line after ALL section headers
2. ✅ Blank line before each numbered result
3. ✅ Use `**Number. Title**` (bold), NOT `#### Number. Title`
4. ✅ Space after `-` in lists: `- Item;`
5. ✅ Semicolons for list items `;` except last `.`
6. ✅ Blank line after each result
7. ✅ Blank lines around `---` separator
8. ❌ NEVER use `####` for numbered items in lists
```

---

## 🔧 Step-by-Step Update Instructions

### Step 1: Locate the Section
```bash
# Open file
code src/agent/nodes.py

# Search for (Ctrl+F)
"### Step 2: Structure Your Response"
```

### Step 2: Replace Template Example
Find this section (~line 671-695) and update the markdown template to match above.

### Step 3: Update Formatting Rules
Find "### Step 3: What You MUST DO" section and add:

```python
### Step 3: What You MUST DO ✅ (Frontend Rendering)
- ✅ Extract ai_answer if present
- ✅ Parse ALL results - show actual content
- ✅ **Blank line after headers** (critical for frontend)
- ✅ **Use `**1. Title**` format**, NOT `#### 1. Title`
- ✅ **Space after list `-`**: `- Item;` not `-Item;`
- ✅ **Semicolons in lists**: `- Item;` except last `- Item.`
- ✅ **Blank line between results**
- ✅ Make links clickable: `[Text](URL)`
- ✅ Sort by relevance score (0.8+)
- ✅ Include published_date when available
```

### Step 4: Add Example
Replace the "GOOD" example with:

````python
**✅ GOOD (Proper frontend-compatible Markdown):**
```markdown
## 🔍 Search Results: Trump's Japan Visit 2025

### 📊 Executive Summary

Former President Trump confirmed plans to visit Japan in spring 2025, focusing on trade and security cooperation.

### 📰 Detailed Findings

**1. Trump Confirms 2025 Japan Visit**

- 📅 Published: 2025-01-15;
- 📝 Key Points: Trump announced via social media his visit to Japan in April 2025 for bilateral talks;
- 🔗 Source: [The Japan Times](https://example.com/article1).

**2. US-Japan Trade Talks Scheduled**

- 📅 Published: 2025-01-12;
- 📝 Key Points: Japanese officials preparing for negotiations during Trump's visit;
- 🔗 Source: [Reuters Asia](https://example.com/article2).

---

💡 **Key Insight**: First post-presidency visit signals continued alliance priorities.
```
````

---

## ⚠️ Common Mistakes to Avoid

### Mistake 1: Using #### for List Items
```markdown
❌ WRONG:
#### 1. Item
- Detail

✅ CORRECT:
**1. Item**

- Detail;
```

### Mistake 2: Missing Blank Lines
```markdown
❌ WRONG:
### Header
Content immediately

✅ CORRECT:
### Header

Content with blank line
```

### Mistake 3: List Format
```markdown
❌ WRONG:
-Item
- Item

✅ CORRECT:
- Item;
- Item.
```

---

## ✅ Verification Checklist

After updating, verify:

- [ ] Template uses `**1. Title**` not `#### 1. Title`
- [ ] All headers have blank line after them
- [ ] Lists use `- ` with space
- [ ] List items end with `;` or `.`
- [ ] Blank lines between numbered results
- [ ] Example shows proper formatting
- [ ] Rules mention "frontend rendering" explicitly

---

## 🧪 Test After Update

```bash
# Restart server
python start_server.py

# Test with search query
"搜索特朗普访问日本2025的新闻"

# Check frontend displays:
✅ Proper list bullets
✅ Clickable links
✅ Clear visual separation
✅ No rendering errors
```

---

**Need help?** Check `demo/chat_demo.html` for frontend rendering component.
