/**
 * Builds a URLSearchParams instance so array values are sent as repeated
 * keys (`status=A&status=B`), matching django-filter's MultipleChoiceFilter
 * — axios's default array serialization uses `key[]=` brackets instead,
 * which DRF/QueryDict.getlist() does not recognize.
 */
export function toSearchParams(params = {}) {
  const usp = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    if (Array.isArray(value)) {
      value.forEach((item) => usp.append(key, item));
    } else {
      usp.append(key, value);
    }
  });
  return usp;
}
