export const loanKeys = {
  all: ["loans"],
  lists: () => [...loanKeys.all, "list"],
  list: (filters) => [...loanKeys.lists(), filters],
  details: () => [...loanKeys.all, "detail"],
  detail: (id) => [...loanKeys.details(), id],
};
