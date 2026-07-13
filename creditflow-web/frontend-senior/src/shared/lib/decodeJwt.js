export function decodeJwtExp(token) {
  try {
    const payload = token.split(".")[1];
    const json = JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
    return json.exp ?? null;
  } catch {
    return null;
  }
}
