import { renderToString } from "react-dom/server";
import { Landing } from "./Landing";
export function render() { return renderToString(<Landing />); }
