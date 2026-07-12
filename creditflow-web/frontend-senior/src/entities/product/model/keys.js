export const productKeys = {
  all: ["products"],
  lists: () => [...productKeys.all, "list"],
  list: (filters) => [...productKeys.lists(), filters],
  details: () => [...productKeys.all, "detail"],
  detail: (id) => [...productKeys.details(), id],
};

export const adminProductKeys = {
  all: ["admin-products"],
  lists: () => [...adminProductKeys.all, "list"],
  list: (filters) => [...adminProductKeys.lists(), filters],
};
