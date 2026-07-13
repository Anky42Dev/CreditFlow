// DOC 6 §3.2: access token lives only in module memory, never in localStorage.
let accessToken = null;
let accessExp = null;

export const setAccess = (token, exp) => {
  accessToken = token;
  accessExp = exp ?? null;
};

export const getAccess = () => accessToken;
export const getAccessExp = () => accessExp;

export const clearAccess = () => {
  accessToken = null;
  accessExp = null;
};
