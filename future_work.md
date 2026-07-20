# Future Work

## 1. Multi-Agent Architecture

Split JudoCoach AI into specialized agents.

### Research Agent

Searches the knowledge base for relevant information.

### Coaching Agent

Explains techniques in beginner-friendly language.

### Strategy Agent

Answers tactical questions such as:

- Fighting taller opponents
- Fighting shorter opponents
- Competition strategy

### Supervisor Agent

Coordinates communication between agents and ensures safe execution.

---

## 2. Video Analysis

Allow users to upload Judo videos.

Potential features:

- Technique recognition
- Posture analysis
- Common mistake detection
- Improvement suggestions

---

## 3. Competition Database

Connect to:

- IJF competition results
- Athlete profiles
- Rankings

Allow users to ask:

- "Show Teddy Riner's recent matches."
- "What techniques are most successful internationally?"

---

## 4. Expanded Knowledge Base

Separate the current Markdown files into individual documents.

Example:

techniques/

- osoto_gari.md
- seoi_nage.md
- uchi_mata.md

instead of a single techniques.md.

---

## 5. Local Models

Replace OpenAI with local models using Ollama.

Benefits:

- Lower cost
- Offline usage
- Better privacy

---

## 6. Hybrid Retrieval

Combine:

- Vector Search
- Keyword Search

to improve retrieval quality.

---

## 7. Image Support

Allow users to upload images of:

- Grips
- Stances
- Competition situations

The assistant would explain the position.

---

## 8. Mobile Application

Develop an Android and iOS app using the same FastAPI backend.

---

## 9. Training Plans

Generate personalized weekly training plans based on:

- Experience level
- Goals
- Competition schedule

---

## 10. Progress Tracking

Store previous reports and training sessions.

Allow users to monitor their long-term improvement.

---