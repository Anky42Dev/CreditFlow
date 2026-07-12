export const applicationKeys = {
  all: ["applications"],
  lists: () => [...applicationKeys.all, "list"],
  list: (filters) => [...applicationKeys.lists(), filters],
  details: () => [...applicationKeys.all, "detail"],
  detail: (id) => [...applicationKeys.details(), id],
};

export const adminApplicationKeys = {
  all: ["admin-applications"],
  lists: () => [...adminApplicationKeys.all, "list"],
  list: (filters) => [...adminApplicationKeys.lists(), filters],
  infiniteLists: () => [...adminApplicationKeys.all, "infinite"],
  infiniteList: (filters) => [...adminApplicationKeys.infiniteLists(), filters],
  details: () => [...adminApplicationKeys.all, "detail"],
  detail: (id) => [...adminApplicationKeys.details(), id],
};
