// Plain pages: the shared header and footer around static text.
import { footer, header } from "./common.js";

document.getElementById("header")?.replaceWith(header());
document.getElementById("footer")?.replaceWith(footer());
