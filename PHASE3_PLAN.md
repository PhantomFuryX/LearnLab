# Phase 3: Intelligent Agents & Automation

This plan addresses the remaining gaps in the LearnLab agent ecosystem, focusing on the specific missing features identified in the status check.

## Phase 3a: Content Intelligence (Research & Summary)
**Goal:** Expand data sources and ensure robust, automated ingestion.

- [ ] **Research Agent: RSS/Feed Ingestion**
  - Add `feedparser` to ingest standard RSS/Atom feeds (e.g., AI blogs, tech news).
  - Add `ingest_feed(url)` method to Research Agent.

- [ ] **Research Agent: Reddit/Twitter Integration**
  - *Option A:* Direct API (complex due to costs/limits).
  - *Option B (Preferred):* Use N8N webhook to receive scraped data from external scrapers/Apify.
  - Implement `ingest_social_signal(platform, data)` method.

- [ ] **Background Scheduler (Celery/ARQ)**
  - Implement `scheduler_service.py` to run Research Agent jobs daily/weekly.
  - "This week's top AI research" auto-job.

## Phase 3b: Educational Core (Quiz & Tutor)
**Goal:** Turn passive content into active learning.

- [ ] **Create Quiz Agent (`quiz_agent.py`)**
  - **Input:** Summary text or Module ID.
  - **Task:** Generate 5-10 MCQs + Short Answer questions.
  - **Output:** JSON with questions, options, correct answer, and explanation.
  - **Grading:** Implement `grade_submission(quiz_id, user_answers)` logic.

- [ ] **Upgrade Tutor Agent**
  - **Step-by-Step Mode:** Add specific prompt flow for "Walk me through this code line-by-line".
  - **Memory:** Integrate `UserMemoryService` to recall past topics/struggles.

## Phase 3c: Social & Automation (Post Agent)
**Goal:** Turn learning into content.

- [ ] **Create Post Agent (`post_agent.py`)**
  - **Input:** Summary + Code Snippet.
  - **Task:** Generate platform-specific copy.
    - *LinkedIn:* Professional, structured, hashtags.
    - *Twitter:* Thread format, punchy.
  - **Output:** Draft text + Image prompt (for DALL-E/Flux).

- [ ] **N8N Workflow Integration**
  - Create a standard N8N webhook to receive "Ready to Publish" posts.
  - Trigger N8N from Post Agent.

## Phase 3d: Frontend Integration
**Goal:** Make the new agents accessible to the user.

- [ ] **Quiz Interface**
  - New page: `QuizView.tsx`.
  - Interactive form to take quiz & see results.

- [ ] **Post Draft Preview**
  - New component in Dashboard/Research view to "Generate Post" from a result.
  - Editable text area for the generated draft.

- [ ] **Planner Integration**
  - Connect the existing `PlanCreation.tsx` form to the backend `planner.py` router.
