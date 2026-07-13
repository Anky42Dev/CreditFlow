import { http, HttpResponse } from "msw";

// DOC 6 §9/§11: minimal but representative mocks for the endpoints exercised
// by the unit/component test suite (auth, applications, loans,
// notifications, admin). Kept deterministic on purpose — no random data,
// no timers — so tests are stable and fast.
const BASE = "http://localhost:8000/api/v1";

export const applicationFixture = {
  id: 1,
  status: "SUBMITTED",
  amount: "100000.00",
  term_months: 12,
  product: 1,
};

export const loanFixture = {
  id: 7,
  status: "ACTIVE",
  principal: "100000.00",
  schedule_items: [
    { id: 1, status: "PAID", amount: "9000.00", due_date: "2026-01-15" },
    { id: 2, status: "OVERDUE", amount: "9000.00", due_date: "2026-02-15" },
    { id: 3, status: "PENDING", amount: "9000.00", due_date: "2026-03-15" },
  ],
};

export const notificationFixture = {
  id: 42,
  type: "application.status_changed",
  body: "Статус заявки №1 изменён",
  is_read: false,
  created_at: "2026-07-01T10:00:00Z",
};

export const handlers = [
  // --- auth ---
  http.post(`${BASE}/auth/login`, async () => {
    return HttpResponse.json({ access: "test-access-token" });
  }),
  http.get(`${BASE}/auth/me`, () => {
    return HttpResponse.json({
      id: 1,
      email: "client@test.com",
      role: "CLIENT",
      permissions: [],
    });
  }),
  http.post(`${BASE}/auth/refresh`, () => {
    return HttpResponse.json({ access: "test-access-token-refreshed" });
  }),

  // --- applications ---
  http.get(`${BASE}/credit-applications`, () => {
    return HttpResponse.json({ count: 1, next: null, previous: null, results: [applicationFixture] });
  }),
  http.get(`${BASE}/credit-applications/:id`, ({ params }) => {
    return HttpResponse.json({ ...applicationFixture, id: Number(params.id) });
  }),
  http.post(`${BASE}/credit-applications`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({ ...applicationFixture, ...body, id: 2, status: "DRAFT" }, { status: 201 });
  }),
  http.post(`${BASE}/credit-applications/:id/submit`, ({ params }) => {
    return HttpResponse.json({ ...applicationFixture, id: Number(params.id), status: "SUBMITTED" });
  }),

  // --- loans ---
  http.get(`${BASE}/loans`, () => {
    return HttpResponse.json({ count: 1, next: null, previous: null, results: [loanFixture] });
  }),
  http.get(`${BASE}/loans/:id`, ({ params }) => {
    return HttpResponse.json({ ...loanFixture, id: Number(params.id) });
  }),
  http.post(`${BASE}/loans/:id/repay`, async ({ request, params }) => {
    const body = await request.json();
    return HttpResponse.json({
      id: Number(params.id),
      loan: Number(params.id),
      amount: body.amount,
      idempotency_key: body.idempotency_key,
      status: "COMPLETED",
    });
  }),

  // --- notifications ---
  http.get(`${BASE}/notifications`, () => {
    return HttpResponse.json({ count: 1, next: null, previous: null, results: [notificationFixture] });
  }),
  http.get(`${BASE}/notifications/unread-count`, () => {
    return HttpResponse.json({ unread_count: 1 });
  }),
  http.post(`${BASE}/notifications/:id/read`, ({ params }) => {
    return HttpResponse.json({ ...notificationFixture, id: Number(params.id), is_read: true });
  }),
  http.post(`${BASE}/notifications/read-all`, () => {
    return HttpResponse.json({ updated: 1 });
  }),

  // --- credit products ---
  http.get(`${BASE}/credit-products`, () => {
    return HttpResponse.json({
      count: 1,
      next: null,
      previous: null,
      results: [{ id: 1, name: "Тестовый продукт", interest_rate: "12.00" }],
    });
  }),
  http.get(`${BASE}/credit-products/:id`, ({ params }) => {
    return HttpResponse.json({ id: Number(params.id), name: "Тестовый продукт", interest_rate: "12.00" });
  }),

  // --- admin ---
  http.get(`${BASE}/admin/applications`, () => {
    return HttpResponse.json({ count: 1, next: null, previous: null, results: [applicationFixture] });
  }),
  http.get(`${BASE}/admin/applications/:id`, ({ params }) => {
    return HttpResponse.json({ ...applicationFixture, id: Number(params.id) });
  }),
];
