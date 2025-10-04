export function formatCount(n: number): string {
  if (n >= 1_00_00_000) { // 1 Crore or above
    // Cap at 99L+
    return "99L+";
  }

  if (n >= 1_00_000) { // Lakhs
    const lakhs = n / 1_00_000;
    // If >= 99 Lakhs, cap at 99L+
    if (lakhs >= 99) {
      return "99L+";
    }
    return lakhs >= 100 || lakhs % 1 === 0
      ? Math.round(lakhs) + "L"
      : lakhs.toFixed(1) + "L";
  }

  if (n >= 1_000) { // Thousands
    const thousands = n / 1_000;
    return thousands >= 100 || thousands % 1 === 0
      ? Math.round(thousands) + "K"
      : thousands.toFixed(1) + "K";
  }

  return n.toString();
}
