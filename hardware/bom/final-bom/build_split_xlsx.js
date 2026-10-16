// Build the 학교·사비 엑셀 exactly as the page button does (same functions, taken from template.html), from data.json + state_main.json.
// usage: node build_split_xlsx.js <path to xlsx.full.min.js 0.18.5 (cdnjs)> <out dir>   then recalc with the xlsx skill (LibreOffice, sandbox off)
const fs = require("fs"), path = require("path");
const FB = __dirname;   // hardware/bom/final-bom
const XLSX = require(process.argv[2]);
const D = JSON.parse(fs.readFileSync(FB + "/data.json", "utf8"));
const Sx = JSON.parse(fs.readFileSync(FB + "/state_main.json", "utf8"));
const tpl = fs.readFileSync(FB + "/template.html", "utf8");
const grab = (name) => { const i = tpl.indexOf("function " + name + "("); let d = 0; const j = tpl.indexOf("{", i); for (let k = j; k < tpl.length; k++){ if (tpl[k] == "{") d++; else if (tpl[k] == "}"){ d--; if (!d) return tpl.slice(i, k + 1); } } };
const ITEMS = D.items, SHIPS = D.ships;
const won = n => Math.round(n).toLocaleString("ko-KR");
let S = {on: Sx.on, qty: Sx.qty};
const onOf = it => (it.id in S.on) ? S.on[it.id] : it.on;
const qtyOf = it => (it.id in S.qty) ? S.qty[it.id] : it.qty;
const window = {XLSX};
eval(grab("unitAt")); eval(grab("compute")); eval(grab("siteName")); eval(grab("splitData")); eval(grab("buildSplitWorkbook"));
const x = splitData();
console.log("school paid", x.schPaid, "school ship", x.schShip, "own", x.r.own, "total", x.r.total, "sch stores", x.sch.length, "own stores", x.own.length);
const {wb, ds} = buildSplitWorkbook();
const out = path.join(process.argv[3], `Toccata_학교_사비_구매목록_${ds}.xlsx`);
fs.writeFileSync(out, Buffer.from(XLSX.write(wb, {bookType:"xlsx", type:"array"})));
for (const n of wb.SheetNames){
  const rows = XLSX.utils.sheet_to_json(wb.Sheets[n], {header: 1});
  console.log("== sheet", n, rows.length, "rows"); console.log("  ", JSON.stringify(rows[0])); console.log("  ", JSON.stringify(rows[1])); console.log("  last:", JSON.stringify(rows[rows.length - 1]));
}
console.log(out);
