/* sortable tables (click a header): plain Markdown tables and the benchmark leaderboards */
document$.subscribe(function () {
  var tables = document.querySelectorAll("article table:not([class]), article table.lb");
  tables.forEach(function (table) { new Tablesort(table); });
});
