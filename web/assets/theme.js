// Runs before the page draws, so a chosen theme never flashes the other one.
// No choice saved: the page follows the system setting.
try {
  const theme = localStorage.getItem("plumb:theme");
  if (theme === "light" || theme === "dark") document.documentElement.dataset.theme = theme;
} catch {
  /* storage blocked: follow the system */
}
