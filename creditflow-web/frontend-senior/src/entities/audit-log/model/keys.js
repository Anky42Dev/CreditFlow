export const auditLogKeys = {
  all: ["admin-audit"],
  lists: () => [...auditLogKeys.all, "list"],
  list: (filters) => [...auditLogKeys.lists(), filters],
};
