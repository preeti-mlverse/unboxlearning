# Testing the UnboxEd app

Double-click `start.bat` (or run the API with `python -m uvicorn engine.api:app --port 8030` and the web app with
`npm --prefix web run dev`), then open http://localhost:5190.

Steps marked 💲 call OpenAI and spend credit. Everything else is free.

## 1. Accounts and dashboard
1. **Sign up** → choose *Educator* (or School / NGO / Organization) → fill in your details → you land on the dashboard.
2. Open **"Courses made before accounts existed"** and click **Add to my courses** for the three demo courses.
3. **Log out**, then **Log in** again using your email *or* your 10-digit mobile number.
4. In a private window, sign up as a **Learner**. You should see *Explore courses* (published courses only), and
   **Create** should say you need an educator account.

## 2. Any content → course 💲
Go to **Create**, then add a file (PDF, Word, PowerPoint, Excel/CSV, EPUB, image, audio/video ≤ 25 MB), a web page,
a documentation site, a YouTube link with captions, or pasted text.
A 10–20 minute course costs about $0.30–0.45, so with about $3 left, test with **one short source**
(a single Wikipedia page is ideal).

## 3. Understanding → outline → micro-modules 💲
On `/create/:cid` you will see:
- *What we found*;
- how we'll teach it;
- suggested goals;
- which sections to include.

Then pick a goal and language and click **Plan outline**. Edit, rename, reorder or delete modules, then click
**Generate**. Each module is a set of cards. There are 12 card kinds: hook, concept, example, check, true/false,
sort, reorder, match, odd-one-out, fill-the-blank, apply, recap. Learners also get two practice games: memory deck and
time attack.

## 4. Illustrations, narration, fact-check
- **Course preview (`/course/:cid`):** every card shows its picture or diagram and its source citations.
- **Fact-check:** cards that failed the check are flagged for you to review.
- **↻ Regenerate / 🎨 Redraw** (💲) rebuild a single card.
- **Narration** is read aloud by the browser's voice (free) in the learner player.
- **Publish** makes the course visible to learners.

## 5. Tutor (never gives the answer away)
In a module, open the tutor and ask for the answer to a question. It should give hints step by step, not the answer.
Each message costs 💲 a fraction of a cent.

## 6. Languages
The course language is chosen at setup (English, Hindi, Tamil, Telugu, Bengali, Marathi and more). The cards are
written directly in that language, and the tutor replies in it.

## Automated checks
```
python -m pytest tests -q
npm --prefix web run typecheck
```
