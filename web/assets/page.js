// Plain pages: the shared header and footer around static text.
import { h, shell } from "./common.js";

const main = document.querySelector("main");
if (main) document.body.replaceChildren(shell(h("div", { class: "wrap" }, main)));
