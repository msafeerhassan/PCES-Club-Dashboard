(function () {
  const stored = localStorage.getItem("pces-theme");
  if (stored === "dark") {
    document.documentElement.setAttribute("data-theme", "dark");
  }

  window.toggleTheme = function () {
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    if (isDark) {
      document.documentElement.removeAttribute("data-theme");
      localStorage.setItem("pces-theme", "light");
    } else {
      document.documentElement.setAttribute("data-theme", "dark");
      localStorage.setItem("pces-theme", "dark");
    }
  };
})();