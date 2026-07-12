const ACCESS = "cf_access";
const REFRESH = "cf_refresh";

export const getTokens = () => ({
  access: typeof window !== "undefined" ? localStorage.getItem(ACCESS) : null,
  refresh: typeof window !== "undefined" ? localStorage.getItem(REFRESH) : null,
});

export const setTokens = ({ access, refresh }) => {
  localStorage.setItem(ACCESS, access);
  if (refresh) localStorage.setItem(REFRESH, refresh);
};

export const clearTokens = () => {
  localStorage.removeItem(ACCESS);
  localStorage.removeItem(REFRESH);
};
