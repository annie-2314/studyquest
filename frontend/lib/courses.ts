// Thin typed helpers for the course/roadmap API.
import { apiFetch } from "./api";

export interface Step {
  id: string;
  ordinal: number;
  video_id: string;
  title: string;
  duration: string;
  estimated: string;
  completed: boolean;
  quiz_passed: boolean;
  youtube_url: string;
}

export interface Course {
  id: string;
  title: string;
  playlist_url: string;
  total_steps: number;
  completed_steps: number;
  percent: number;
  estimated_total: string;
  proficient: boolean;
  steps: Step[];
}

function token() {
  return localStorage.getItem("sq_access") ?? undefined;
}

export const coursesApi = {
  list: () => apiFetch<Course[]>("/courses", {}, token()),
  get: (id: string) => apiFetch<Course>(`/courses/${id}`, {}, token()),
  create: (playlist_url: string) =>
    apiFetch<Course>("/courses", { method: "POST", body: JSON.stringify({ playlist_url }) }, token()),
  complete: (cid: string, sid: string) =>
    apiFetch<Course>(`/courses/${cid}/steps/${sid}/complete`, { method: "POST" }, token()),
  summarize: (cid: string, sid: string) =>
    apiFetch<{ summary: string }>(`/courses/${cid}/steps/${sid}/summarize`, { method: "POST" }, token()),
  ask: (cid: string, sid: string, question: string) =>
    apiFetch<{ answer: string; citations: { ref: string; content: string }[] }>(
      `/courses/${cid}/steps/${sid}/ask`,
      { method: "POST", body: JSON.stringify({ question }) },
      token()
    ),
  quiz: (cid: string, sid: string) =>
    apiFetch<{ question: string; options: string[] }>(
      `/courses/${cid}/steps/${sid}/quiz`,
      { method: "POST" },
      token()
    ),
  grade: (cid: string, sid: string, question: string, selected: string) =>
    apiFetch<{ correct: boolean; feedback: string }>(
      `/courses/${cid}/steps/${sid}/quiz/grade`,
      { method: "POST", body: JSON.stringify({ question, selected }) },
      token()
    ),
};
