// Zero Track Blog — standalone nav (no data dependency).
(function () {
  const nav = document.getElementById("nav");
  const base = nav.dataset.base || "";
  const items = [
    ["index.html", "Posts", true],
  ];
  nav.innerHTML =
    `<span class="logo">ZeroTrack<b>_</b><span class="sub-mark">BLOG</span></span>` +
    items.map(([href, lbl, rel]) =>
      `<a class="item" href="${rel ? base + href : href}">${lbl}</a>`
    ).join("");
})();
