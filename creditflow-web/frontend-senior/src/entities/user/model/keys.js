export const profileKeys = {
  detail: ["profile"],
};

export const adminUserKeys = {
  all: ["admin-users"],
  lists: () => [...adminUserKeys.all, "list"],
  list: (filters) => [...adminUserKeys.lists(), filters],
};
