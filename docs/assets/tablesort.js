/* sortable tables (click a header); the benchmark leaderboards use it */
document$.subscribe(function () {
  var tables = document.querySelectorAll("article table:not([class])");
  tables.forEach(function (table) { new Tablesort(table); });
});
